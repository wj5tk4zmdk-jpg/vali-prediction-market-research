import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

import pandas as pd

import vali
from vali.application.commands import build_parser
from vali.artifacts.reports import rebuild_report
from vali.config import ValiConfig
from vali.providers import google_trends, kalshi
from vali.providers.google_trends import (
    FixtureTrendsGateway,
    build_request_plan,
    load_query_manifest,
)


ROOT = Path(__file__).parents[2]
NEW_CONFIG = ROOT / "configs" / "experiments" / "fed_easing_v1.toml"
NEW_TRENDS_FIXTURE = (
    ROOT
    / "tests"
    / "fixtures"
    / "providers"
    / "google_trends"
    / "interest.json"
)
OLD_TRENDS_FIXTURE = (
    ROOT / "tests" / "fixtures" / "google_trends" / "interest.json"
)
KALSHI_FIXTURES = ROOT / "tests" / "fixtures" / "providers" / "kalshi"


class ArtifactLayoutCompatibilityTests(unittest.TestCase):
    def test_committed_provider_fixtures_and_compatibility_copy_load(self):
        self.assertEqual(
            NEW_TRENDS_FIXTURE.read_bytes(), OLD_TRENDS_FIXTURE.read_bytes()
        )
        specs = load_query_manifest(
            ROOT / "configs" / "features" / "google_trends_candidate_v1.csv"
        )
        request = build_request_plan(
            specs,
            pd.Timestamp("2026-06-17").date(),
            pd.Timestamp("2026-06-21").date(),
        )[0]
        response = FixtureTrendsGateway(NEW_TRENDS_FIXTURE).fetch(request)
        compatibility_response = FixtureTrendsGateway(
            OLD_TRENDS_FIXTURE
        ).fetch(request)
        self.assertEqual(response, compatibility_response)

        expected_kalshi = {
            "candlesticks.json",
            "events.json",
            "markets.json",
            "orderbook.json",
            "trades.json",
        }
        self.assertEqual(
            {path.name for path in KALSHI_FIXTURES.glob("*.json")},
            expected_kalshi,
        )
        for path in KALSHI_FIXTURES.glob("*.json"):
            self.assertIsNotNone(json.loads(path.read_text(encoding="utf-8")))

    def test_new_config_and_cli_paths_remain_resolvable(self):
        config = ValiConfig.from_toml(NEW_CONFIG)
        self.assertEqual(config.methodology_version, "1.0.1")
        parser = build_parser()
        config_args = parser.parse_args(
            ["validate", "--config", str(NEW_CONFIG)]
        )
        fixture_args = parser.parse_args(
            [
                "trends",
                "backfill",
                "--out",
                "run",
                "--fixture",
                str(NEW_TRENDS_FIXTURE),
            ]
        )
        self.assertEqual(config_args.config, NEW_CONFIG)
        self.assertEqual(fixture_args.fixture, NEW_TRENDS_FIXTURE)

    def test_report_reconstruction_preserves_name_and_sections(self):
        with TemporaryDirectory() as temporary:
            run_dir = Path(temporary)
            frames = {
                "metrics": pd.DataFrame(
                    [
                        {
                            "model": "market",
                            "metric": "brier_score",
                            "value": 0.2,
                        }
                    ]
                ),
                "forecasts": pd.DataFrame(),
                "trades": pd.DataFrame(),
                "sensitivity": pd.DataFrame(),
                "exclusions": pd.DataFrame(),
                "calibration": pd.DataFrame(),
                "regime_confusion": pd.DataFrame(),
            }
            for name, frame in frames.items():
                frame.to_csv(run_dir / f"{name}.csv", index=False)
            manifest = {
                "methodology_version": "1.0.1",
                "parameter_freeze_date": "2026-06-23",
            }
            (run_dir / "run_manifest.json").write_text(
                json.dumps(manifest), encoding="utf-8"
            )

            report = rebuild_report(run_dir)

            self.assertEqual(report.name, "report.html")
            content = report.read_text(encoding="utf-8")
            self.assertIn("VALI Fed-Rate Research Report", content)
            self.assertIn("Forecast metrics", content)
            self.assertIn("Reproducibility manifest", content)

    def test_imports_resolve_only_from_authoritative_source_tree(self):
        authoritative = (ROOT / "src" / "vali").resolve()
        modules = (vali, google_trends, kalshi)
        for module in modules:
            module_path = Path(module.__file__).resolve()
            self.assertTrue(module_path.is_relative_to(authoritative))
            self.assertNotIn("artifacts", module_path.parts)
            self.assertNotIn("quarantine", module_path.parts)

        self.assertFalse((ROOT / "build").exists())
        quarantined_build = str(
            (ROOT / "artifacts" / "quarantine" / "build").resolve()
        ).casefold()
        self.assertTrue(
            all(quarantined_build not in str(path).casefold() for path in sys.path)
        )

    def test_tests_do_not_depend_on_stale_build_source(self):
        stale_forward = "build" + "/lib"
        stale_windows = "build" + "\\lib"
        for path in (ROOT / "tests").rglob("*.py"):
            content = path.read_text(encoding="utf-8")
            self.assertNotIn(stale_forward, content)
            self.assertNotIn(stale_windows, content)

    def test_no_prohibited_application_surface_was_added(self):
        text = build_parser().format_help().casefold()
        for forbidden in (
            "api-key",
            "credentials",
            "live-trading",
            "order-submit",
            "p_flow",
            "private-input",
            "proprietary-flow",
            "submit-order",
        ):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
