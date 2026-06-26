"""Contract tests for KG-Handoff Step 4 compiled-manifest backtest wiring."""

from __future__ import annotations

from contextlib import redirect_stdout
from copy import deepcopy
from io import StringIO
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import unittest

import pandas as pd

from vali.application.commands import main as application_main
from vali.knowledge_graph import compute_graph_hash
from vali.knowledge_graph.handoff import KnowledgeGraphError
from vali.knowledge_graph.runtime import load_compiled_manifest_runtime
from vali.sample import make_synthetic_dataset


ROOT = Path(__file__).parents[2]
HORMUZ_ROOT = (
    ROOT / "configs" / "knowledge_graph" / "examples" / "hormuz_normalization"
)


def _capture(arguments: list[str]) -> dict:
    output = StringIO()
    with redirect_stdout(output):
        application_main(arguments)
    return json.loads(output.getvalue())


def _copy_graph(root: Path) -> Path:
    target = root / "graph"
    shutil.copytree(HORMUZ_ROOT, target)
    return target / "graph_manifest.v1.json"


def _feature_manifest_rows(data_dir: Path) -> list[dict]:
    return pd.read_csv(data_dir / "feature_manifest.csv").to_dict("records")


def _compiled_manifest(root: Path, *, expected_lead_days: list[int] | None = None) -> Path:
    data_dir = root / "data"
    make_synthetic_dataset(data_dir, seed=20260623, event_count=5)
    graph = _copy_graph(root)
    _, _, graph_hash = compute_graph_hash(graph)
    expected_lead_days = expected_lead_days or [1, 14]
    features = []
    for row in _feature_manifest_rows(data_dir):
        features.append(
            {
                "feature_id": row["feature_id"],
                "concept_id": f"attention_concept:{row['feature_id']}",
                "query_id": f"attention_query:{row['feature_id']}",
                "source": row["source"],
                "query_text": row["feature_id"].replace("_", " "),
                "geo": "US",
                "frequency": "daily",
                "polarity": int(row["polarity"]),
                "transform": row["transformation"],
                "availability_lag": f"T-{int(row['availability_lag_days'])}",
                "missing_policy": row["missing_policy"],
                "max_age_days": int(row["max_age_days"]),
                "required": bool(row["required"]),
                "contamination_risks": [],
                "expected_lead_days": list(expected_lead_days),
                "evidence_status": "hypothesized",
            }
        )

    payload = {
        "schema_version": "compiled_vali_manifest.v1",
        "manifest_id": "compiled:test_graph:synthetic_vali:v1",
        "created_at": "2026-06-26T16:00:00Z",
        "source_graph": {
            "graph_id": "example_graph:hormuz_normalization:v1",
            "graph_version": "v1",
            "graph_hash": graph_hash,
            "graph_manifest_path": "graph/graph_manifest.v1.json",
            "freeze_status": "draft",
            "review_record": "REVIEW_RECORD.v1.json",
            "preflight_report_hash": "sha256:fixture",
            "preflight_schema_version": "kg_preflight.v1",
        },
        "event_family": {
            "event_family_id": "synthetic_fomc_easing",
            "terminal_measure_id": "synthetic_easing_outcome",
            "clear_horizon_id": "clear_horizon:synthetic_fomc_easing:v1",
        },
        "p_side": {
            "markets": [
                {
                    "venue": "synthetic_public_fixture",
                    "series_ticker": "SYNTH",
                    "event_ticker": "SYNTH-FOMC",
                    "market_ticker": "SYNTH-EASING",
                    "normalized_contract_id": "normalized_contract:synthetic_fomc_easing:v1",
                    "operator": "binary",
                    "threshold": "target_range_lower_after_meeting",
                    "terminal_measure_id": "synthetic_easing_outcome",
                    "settlement_source": "synthetic_fixture",
                    "cutoff_rules": "daily_16_00_et",
                    "clear_horizon_id": "clear_horizon:synthetic_fomc_easing:v1",
                    "price_source_policy": "public_executable_prices",
                    "liquidity_policy": "configured_spread_depth_staleness_fee_gates",
                    "depth_availability": "observed_fixture_depth",
                    "exclusion_status": "fixture_only",
                }
            ]
        },
        "a_side": {
            "composition_policy": "equal_weight",
            "weight_policy": "frozen_equal_weight",
            "features": features,
        },
        "relationships": [
            {
                "edge_id": "edge_fixture_attention_to_easing",
                "from": "AttentionConcept:labor_cooling",
                "to": "TerminalMeasure:synthetic_easing_outcome",
                "relationship": "candidate_public_attention_proxy",
                "expected_direction": "positive_toward_easing",
                "expected_lead_days": list(expected_lead_days),
            }
        ],
        "falsification_gates": [],
        "claim_boundaries": [
            "no_alpha_claim",
            "no_trading_readiness_claim",
            "public_data_only",
            "no_private_data",
            "no_proprietary_order_flow",
            "no_credentials",
            "no_live_trading",
            "no_order_submission",
            "no_P_flow",
        ],
        "runtime_constraints": {
            "no_graph_traversal_required": True,
            "no_learned_weights": True,
            "no_dynamic_query_selection": True,
            "lag_metadata_usage": "documentation_and_falsification_only",
            "lag_metadata_constraint": (
                "VALI engine MUST NOT use expected_lead_days to tune rolling windows "
                "or entry/exit timing"
            ),
        },
        "runtime_inputs": {
            "events": "data/events.csv",
            "quotes": "data/quotes.csv",
            "features": "data/features.csv",
        },
        "runtime_parameters": {
            "run": {
                "parameter_freeze_date": "2026-06-23",
                "methodology_version": "1.0.1",
            },
            "market": {
                "max_spread": 0.10,
                "min_depth": 100.0,
                "max_quote_age_minutes": 30,
                "fallback_trade_window_minutes": 120,
                "fee_bps": 5.0,
                "probability_epsilon": 0.0001,
            },
            "features": {
                "timezone": "America/New_York",
                "daily_cutoff": "16:00",
                "standardization_window": 90,
                "min_periods": 30,
            },
            "signal": {
                "velocity_window": 7,
                "normalization_window": 90,
                "min_periods": 30,
                "entry_threshold": 2.0,
                "exit_threshold": 0.5,
                "sensitivity_windows": [3, 14, 30],
            },
            "regime": {
                "window": 90,
                "min_periods": 30,
                "max_lag": 7,
                "min_abs_correlation": 0.20,
                "tie_margin": 0.05,
            },
            "backtest": {
                "min_train_events": 16,
                "notional": 100.0,
                "stop_loss_fraction": 0.25,
                "max_holding_days": 14,
                "days_before_settlement": 1,
                "calibration_l2": 1.0,
                "entry_regime_confirmation_periods": 1,
                "exit_regime_confirmation_periods": 1,
            },
        },
    }
    manifest = root / "compiled_manifest.json"
    manifest.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return manifest


class KnowledgeGraphManifestBacktestTests(unittest.TestCase):
    def test_backtest_runs_from_compiled_manifest_and_appends_evidence(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = _compiled_manifest(root)
            graph = root / "graph" / "graph_manifest.v1.json"
            _, before_hashes, before_graph_hash = compute_graph_hash(graph)
            output = root / "run"

            summary = _capture(
                ["backtest", "--manifest", str(manifest), "--out", str(output)]
            )
            run_manifest = json.loads((output / "run_manifest.json").read_text(encoding="utf-8"))
            evidence_path = Path(run_manifest["kg_validation_evidence"]["path"])
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            _, after_hashes, after_graph_hash = compute_graph_hash(graph)

        self.assertEqual(summary["output_dir"], str(output.resolve()))
        self.assertGreater(summary["signal_rows"], 0)
        self.assertIn("compiled_manifest", run_manifest)
        self.assertEqual(
            run_manifest["compiled_manifest"]["expected_lag_metadata_used_for_signal_construction"],
            False,
        )
        self.assertTrue(evidence_path.name.startswith("validation_evidence_"))
        self.assertEqual(evidence["graph_hash"], before_graph_hash)
        self.assertEqual(evidence["source"]["compiled_manifest_id"], "compiled:test_graph:synthetic_vali:v1")
        self.assertEqual(evidence["evidence_status"], "not_validated")
        self.assertIn("bounded_by_evidence", evidence["claim_status"])
        self.assertEqual(before_hashes, after_hashes)
        self.assertEqual(before_graph_hash, after_graph_hash)

    def test_manifest_backtest_matches_equivalent_toml_config_outputs(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = _compiled_manifest(root)
            config = root / "data" / "config.toml"
            config_output = root / "config_run"
            manifest_output = root / "manifest_run"

            _capture(["backtest", "--config", str(config), "--out", str(config_output)])
            _capture(["backtest", "--manifest", str(manifest), "--out", str(manifest_output)])

            config_signals = pd.read_csv(config_output / "signals.csv")
            manifest_signals = pd.read_csv(manifest_output / "signals.csv")
            config_trades = (config_output / "trades.csv").read_text(encoding="utf-8")
            manifest_trades = (manifest_output / "trades.csv").read_text(encoding="utf-8")

        pd.testing.assert_frame_equal(config_signals, manifest_signals)
        self.assertEqual(config_trades, manifest_trades)

    def test_expected_lead_days_metadata_is_ignored_for_signal_construction(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest_one = _compiled_manifest(root / "one", expected_lead_days=[1, 14])
            manifest_two = _compiled_manifest(root / "two", expected_lead_days=[30, 90])

            _capture(["backtest", "--manifest", str(manifest_one), "--out", str(root / "run_one")])
            _capture(["backtest", "--manifest", str(manifest_two), "--out", str(root / "run_two")])

            first = pd.read_csv(root / "run_one" / "signals.csv")
            second = pd.read_csv(root / "run_two" / "signals.csv")

        pd.testing.assert_frame_equal(first, second)

    def test_manifest_runtime_rejects_dynamic_lag_or_graph_constraints(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = _compiled_manifest(root)
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            broken = deepcopy(payload)
            broken["runtime_constraints"]["lag_metadata_usage"] = "runtime_tuning"
            manifest.write_text(json.dumps(broken), encoding="utf-8")

            with self.assertRaisesRegex(KnowledgeGraphError, "lag_metadata_usage"):
                load_compiled_manifest_runtime(manifest)

    def test_backtest_requires_exactly_one_config_or_manifest(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = _compiled_manifest(root)
            config = root / "data" / "config.toml"
            with self.assertRaisesRegex(SystemExit, "exactly one"):
                _capture(
                    [
                        "backtest",
                        "--config",
                        str(config),
                        "--manifest",
                        str(manifest),
                        "--out",
                        str(root / "run"),
                    ]
                )


if __name__ == "__main__":
    unittest.main()
