from datetime import date
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

import pandas as pd

from vali.application.commands import build_parser
from vali.config import FeatureConfig, ValiConfig
from vali.features import build_attention_index
from vali.providers.google_trends import (
    FixtureTrendsGateway,
    build_request_plan,
    feature_manifest_frame,
    load_query_manifest,
    normalize_response,
    query_manifest_sha256,
)
from vali.providers.kalshi import (
    build_easing_mappings,
    normalize_candlesticks,
)


ROOT = Path(__file__).parents[2]
OLD_CONFIG = ROOT / "examples" / "config.toml"
NEW_CONFIG = ROOT / "configs" / "experiments" / "fed_easing_v1.toml"
OLD_TRENDS_MANIFEST = (
    ROOT / "src" / "vali" / "data" / "google_trends_query_manifest.v1.csv"
)
NEW_TRENDS_MANIFEST = (
    ROOT / "configs" / "features" / "google_trends_candidate_v1.csv"
)
KALSHI_FIXTURES = ROOT / "tests" / "fixtures" / "providers" / "kalshi"
TRENDS_FIXTURE = (
    ROOT
    / "tests"
    / "fixtures"
    / "providers"
    / "google_trends"
    / "interest.json"
)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def trends_feature_rows(specs, cutoffs):
    rows = []
    active = [spec for spec in specs if spec.active]
    for offset, spec in enumerate(active):
        for index, cutoff in enumerate(cutoffs):
            rows.append(
                {
                    "feature_id": spec.feature_id,
                    "observation_at": cutoff - pd.Timedelta(days=2),
                    "available_at": cutoff - pd.Timedelta(hours=1),
                    "vintage": "initial",
                    "source": "google_trends_api_alpha",
                    "value": float(10 + offset + index),
                }
            )
    return pd.DataFrame(rows)


class ProjectLayoutCompatibilityTests(unittest.TestCase):
    def test_new_and_compatibility_config_paths_load_identically(self):
        self.assertTrue(OLD_CONFIG.exists())
        self.assertTrue(NEW_CONFIG.exists())
        self.assertEqual(OLD_CONFIG.read_bytes(), NEW_CONFIG.read_bytes())

        old = ValiConfig.from_toml(OLD_CONFIG)
        new = ValiConfig.from_toml(NEW_CONFIG)
        self.assertEqual(old.methodology_version, new.methodology_version)
        self.assertEqual(old.parameter_freeze_date, new.parameter_freeze_date)
        self.assertEqual(old.market, new.market)
        self.assertEqual(old.features, new.features)
        self.assertEqual(old.signal, new.signal)
        self.assertEqual(old.regime, new.regime)
        self.assertEqual(old.backtest, new.backtest)
        self.assertEqual(old.data.events.name, new.data.events.name)
        self.assertEqual(old.data.quotes.name, new.data.quotes.name)
        self.assertEqual(old.data.features.name, new.data.features.name)
        self.assertEqual(
            old.data.feature_manifest.name, new.data.feature_manifest.name
        )

    def test_frozen_trends_manifest_bytes_order_status_and_hash_are_identical(self):
        self.assertEqual(
            OLD_TRENDS_MANIFEST.read_bytes(), NEW_TRENDS_MANIFEST.read_bytes()
        )
        old = load_query_manifest(OLD_TRENDS_MANIFEST)
        new = load_query_manifest(NEW_TRENDS_MANIFEST)
        self.assertEqual(old, new)
        self.assertEqual(
            [spec.query_id for spec in old],
            [spec.query_id for spec in new],
        )
        self.assertEqual(
            [spec.query_id for spec in old if spec.active],
            [spec.query_id for spec in new if spec.active],
        )
        self.assertEqual(
            [spec.query_id for spec in old if not spec.active],
            [spec.query_id for spec in new if not spec.active],
        )
        self.assertEqual(
            query_manifest_sha256(old), query_manifest_sha256(new)
        )
        self.assertEqual(
            query_manifest_sha256(new),
            "f720ef7ba487e9949720a348f8ba5354162f67f4df4acf0d625ccf83715bfb1a",
        )

    def test_relocated_manifest_preserves_attention_and_audit_behavior(self):
        old_specs = load_query_manifest(OLD_TRENDS_MANIFEST)
        new_specs = load_query_manifest(NEW_TRENDS_MANIFEST)
        old_manifest = feature_manifest_frame(old_specs)
        new_manifest = feature_manifest_frame(new_specs)
        pd.testing.assert_frame_equal(old_manifest, new_manifest)

        cutoffs = pd.date_range(
            "2026-01-01 21:00", periods=8, freq="D", tz="UTC"
        )
        features = trends_feature_rows(old_specs, cutoffs)
        config = FeatureConfig(standardization_window=3, min_periods=3)
        old_attention, old_audit = build_attention_index(
            features, old_manifest, cutoffs, config
        )
        new_attention, new_audit = build_attention_index(
            features, new_manifest, cutoffs, config
        )
        pd.testing.assert_frame_equal(old_attention, new_attention)
        pd.testing.assert_frame_equal(old_audit, new_audit)
        self.assertTrue(old_attention["attention"].notna().any())

        broadened = features.iloc[[0]].copy()
        broadened["feature_id"] = "google_trends.post_freeze"
        with self.assertRaisesRegex(ValueError, "outside the frozen manifest"):
            build_attention_index(
                pd.concat([features, broadened], ignore_index=True),
                new_manifest,
                cutoffs,
                config,
            )

        missing = features.loc[
            features["feature_id"] != new_manifest.iloc[0]["feature_id"]
        ]
        missing_attention, missing_audit = build_attention_index(
            missing, new_manifest, cutoffs, config
        )
        self.assertTrue(missing_attention["attention"].isna().all())
        self.assertTrue(
            (missing_attention["attention_rejection_reason"] == "missing_required_feature").all()
        )
        self.assertTrue(
            missing_audit.loc[
                missing_audit["feature_id"]
                == new_manifest.iloc[0]["feature_id"],
                "missing_for_signal",
            ].all()
        )

    def test_optional_missingness_and_dynamic_reweighting_are_unchanged(self):
        cutoffs = pd.date_range(
            "2026-02-01 21:00", periods=7, freq="D", tz="UTC"
        )
        rows = []
        for feature_id in ("required", "optional"):
            for index, cutoff in enumerate(cutoffs):
                if feature_id == "optional" and index == 5:
                    continue
                rows.append(
                    {
                        "feature_id": feature_id,
                        "observation_at": cutoff - pd.Timedelta(hours=1),
                        "available_at": cutoff - pd.Timedelta(minutes=30),
                        "vintage": "initial",
                        "source": "public_search",
                        "value": float(index + 1),
                    }
                )
        features = pd.DataFrame(rows)
        manifest = pd.DataFrame(
            [
                {
                    "feature_id": "required",
                    "rationale": "required",
                    "transformation": "level",
                    "polarity": 1,
                    "availability_lag_days": 0,
                    "missing_policy": "asof",
                    "max_age_days": 1,
                    "required": True,
                    "source": "public_search",
                },
                {
                    "feature_id": "optional",
                    "rationale": "optional",
                    "transformation": "level",
                    "polarity": -1,
                    "availability_lag_days": 0,
                    "missing_policy": "asof",
                    "max_age_days": 1,
                    "required": False,
                    "source": "public_search",
                },
            ]
        )
        reject, reject_audit = build_attention_index(
            features,
            manifest,
            cutoffs,
            FeatureConfig(standardization_window=3, min_periods=3),
        )
        dynamic, _ = build_attention_index(
            features,
            manifest,
            cutoffs,
            FeatureConfig(
                standardization_window=3,
                min_periods=3,
                optional_feature_policy="dynamic_reweight",
            ),
        )
        self.assertEqual(
            reject.iloc[5]["attention_rejection_reason"],
            "missing_optional_feature",
        )
        self.assertTrue(pd.isna(reject.iloc[5]["attention"]))
        self.assertTrue(pd.notna(dynamic.iloc[5]["attention"]))
        self.assertTrue(
            reject_audit.loc[
                (reject_audit["cutoff_at"] == cutoffs[5])
                & (reject_audit["feature_id"] == "optional"),
                "missing_for_signal",
            ].iloc[0]
        )

    def test_relocated_provider_fixture_hashes_and_outputs_are_unchanged(self):
        expected_hashes = {
            "candlesticks.json": "510e4d8052d47eb70f30e8e6094a4128e5aca0cd4bc9de36b546dab205bca0c8",
            "events.json": "123ca286a85bf50aacfa23b35d2ee4d1f317d7a358b4680c200ca6be91fa31d7",
            "markets.json": "d1976ccba922f3144167a02a4b489cd607997ce6fc7089f92425c02bb8a961ef",
            "orderbook.json": "af5ca9c2759614c2ca747ebfd90e27c5559512c486892d5de6407c4f4f89077b",
            "trades.json": "7c0d68fd5249eece86e75b020d69178e0bfa62d8193f5018777ade03f3d7f93c",
            "interest.json": "dc0b7e96e1ce57bb8e0226f22ce45c1c7d4867fe8a708ee553f5ad40b3b97018",
        }
        paths = list(KALSHI_FIXTURES.glob("*.json")) + [TRENDS_FIXTURE]
        self.assertEqual(
            {
                path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                for path in paths
            },
            expected_hashes,
        )

        events = load_json(KALSHI_FIXTURES / "events.json")["events"]
        markets = load_json(KALSHI_FIXTURES / "markets.json")
        mapping = build_easing_mappings(events, markets)[0][-1]
        quotes = normalize_candlesticks(
            mapping,
            load_json(KALSHI_FIXTURES / "candlesticks.json")["candlesticks"],
        )
        self.assertEqual(quotes.iloc[0]["bid"], 0.35)
        self.assertEqual(quotes.iloc[0]["ask"], 0.40)
        self.assertFalse(quotes.iloc[0]["depth_observed"])

        specs = load_query_manifest(NEW_TRENDS_MANIFEST)
        request = build_request_plan(
            specs, date(2026, 6, 17), date(2026, 6, 21)
        )[0]
        response = FixtureTrendsGateway(TRENDS_FIXTURE).fetch(request)
        features, observations, exclusions = normalize_response(response, specs)
        self.assertEqual(len(features), 18)
        self.assertEqual(len(observations), 24)
        self.assertEqual(set(exclusions["reason"]), {"low_volume", "suppressed"})

    def test_pytest_discovery_and_cli_paths_use_the_new_layout(self):
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "--collect-only",
                "-q",
                "tests/unit",
                "tests/contract",
                "tests/leakage",
                "tests/integration",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        for directory in ("tests/unit", "tests/contract", "tests/leakage", "tests/integration"):
            self.assertIn(directory, completed.stdout)

        parser = build_parser()
        config_args = parser.parse_args(
            ["validate", "--config", str(NEW_CONFIG)]
        )
        fixture_args = parser.parse_args(
            [
                "trends",
                "backfill",
                "--out",
                "output",
                "--fixture",
                str(TRENDS_FIXTURE),
            ]
        )
        self.assertEqual(config_args.config, NEW_CONFIG)
        self.assertEqual(fixture_args.fixture, TRENDS_FIXTURE)
        cli_text = parser.format_help().lower()
        for forbidden in (
            "api-key",
            "credentials",
            "order-submit",
            "p_flow",
            "private-input",
        ):
            self.assertNotIn(forbidden, cli_text)


if __name__ == "__main__":
    unittest.main()
