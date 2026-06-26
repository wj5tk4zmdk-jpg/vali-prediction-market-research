from dataclasses import replace
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import pandas as pd

from vali.backtest import run_backtest
from vali.config import BacktestConfig, ConfigError, ValiConfig
from vali.io import load_inputs
from vali.research.pipeline import _build_signals
from vali.research.regime_confirmation import (
    ConfirmationArm,
    build_confirmation_grid,
    confirmation_deltas,
    delayed_exit_decomposition,
    delayed_exit_summary,
    parse_confirmation_grid,
    run_confirmation_panel,
)
from vali.sample import make_synthetic_dataset


class RegimeConfirmationPanelTests(unittest.TestCase):
    def test_default_grid_includes_predeclared_arms_and_current_config(self):
        with TemporaryDirectory() as temporary:
            config = ValiConfig.from_toml(
                make_synthetic_dataset(Path(temporary), event_count=20)
            )
            default_labels = [
                arm.label for arm in build_confirmation_grid(config)
            ]
            self.assertEqual(
                default_labels, ["1/1", "1/2", "2/1", "2/2", "3/3"]
            )

            custom_config = replace(
                config,
                backtest=replace(
                    config.backtest,
                    entry_regime_confirmation_periods=4,
                    exit_regime_confirmation_periods=2,
                ),
            )
            self.assertEqual(
                [arm.label for arm in build_confirmation_grid(custom_config)],
                ["1/1", "1/2", "2/1", "2/2", "3/3", "4/2"],
            )

    def test_custom_grid_parsing_rejects_invalid_and_duplicate_entries(self):
        self.assertEqual(
            [arm.label for arm in parse_confirmation_grid("1/1, 1/2,2/2")],
            ["1/1", "1/2", "2/2"],
        )
        for value in ("0/1", "1/0", "1.5/2", "bad", "1/1,1/1"):
            with self.subTest(value=value):
                with self.assertRaises(ConfigError):
                    parse_confirmation_grid(value)

    def test_baseline_arm_matches_normal_backtest_trade_count_and_outputs(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = ValiConfig.from_toml(
                make_synthetic_dataset(root / "data", seed=21, event_count=20)
            )
            result = run_confirmation_panel(config, root / "panel")
            bundle = load_inputs(config)
            signals, _ = _build_signals(config, bundle)
            normal = run_backtest(signals, bundle.events, config)
            baseline = result.panel.set_index("grid_label").loc["1/1"]

            self.assertEqual(baseline["trades"], len(normal.trades))
            self.assertEqual(
                baseline["entry_signal_count"],
                int(signals["action"].isin(["long_yes", "long_no"]).sum()),
            )
            self.assertTrue(
                (root / "panel" / "regime_confirmation_panel.csv").exists()
            )
            self.assertTrue(
                (root / "panel" / "regime_confirmation_deltas.csv").exists()
            )
            self.assertTrue(
                (
                    root
                    / "panel"
                    / "regime_confirmation_delayed_exit_summary.csv"
                ).exists()
            )
            self.assertTrue(
                (
                    root
                    / "panel"
                    / "regime_confirmation_delayed_exit_summary.parquet"
                ).exists()
            )
            self.assertTrue(
                (
                    root
                    / "panel"
                    / "regime_confirmation_delayed_exits.csv"
                ).exists()
            )
            manifest = (
                root / "panel" / "regime_confirmation_manifest.json"
            ).read_text(encoding="utf-8")
            manifest_payload = json.loads(manifest)
            report = (
                root / "panel" / "regime_confirmation_report.html"
            ).read_text(encoding="utf-8")
            for text in (manifest, report):
                self.assertIn("execution sensitivity overlay", text)
                self.assertIn("not a new signal", text)
                self.assertIn("not classifier tuning", text)
                self.assertIn("not alpha evidence", text)
            self.assertEqual(
                result.manifest["confirmation_panel"]["baseline"], "1/1"
            )
            self.assertIn(
                "regime_confirmation_delayed_exit_summary",
                manifest_payload["outputs"],
            )
            self.assertIn(
                "Delayed Exit Summary (Dragon Under the Bridge)", report
            )
            for label in (
                "delayed_exits_total",
                "delayed_exits_helped",
                "delayed_exits_hurt",
                "net_delay_pnl",
                "helped_pct",
                "hurt_pct",
            ):
                self.assertIn(label, report)
            self.assertIn("Delayed exit decomposition", report)

    def test_deltas_are_computed_against_one_one_baseline(self):
        panel = pd.DataFrame(
            [
                {"grid_label": "1/1", "trades": 10, "net_pnl": 5.0},
                {"grid_label": "2/2", "trades": 8, "net_pnl": 7.5},
            ]
        )

        deltas = confirmation_deltas(panel).set_index(["grid_label", "metric"])

        self.assertEqual(deltas.loc[("2/2", "trades"), "delta"], -2)
        self.assertEqual(deltas.loc[("2/2", "net_pnl"), "delta"], 2.5)

    def test_delayed_exit_decomposition_labels_saved_and_bad_delays(self):
        baseline = pd.DataFrame(
            [
                {
                    "trade_id": "saved",
                    "event_id": "event-1",
                    "contract_id": "contract-1",
                    "side": "long_yes",
                    "exit_at": pd.Timestamp("2025-01-02", tz="UTC"),
                    "exit_reason": "regime_change",
                    "exit_probability": 0.40,
                    "units": 100.0,
                    "net_pnl": -10.0,
                },
                {
                    "trade_id": "bad",
                    "event_id": "event-2",
                    "contract_id": "contract-2",
                    "side": "long_yes",
                    "exit_at": pd.Timestamp("2025-01-02", tz="UTC"),
                    "exit_reason": "regime_change",
                    "exit_probability": 0.60,
                    "units": 100.0,
                    "net_pnl": 10.0,
                },
            ]
        )
        buffered = pd.DataFrame(
            [
                {
                    "trade_id": "saved",
                    "event_id": "event-1",
                    "contract_id": "contract-1",
                    "side": "long_yes",
                    "exit_at": pd.Timestamp("2025-01-04", tz="UTC"),
                    "exit_reason": "settlement",
                    "exit_probability": 0.70,
                    "units": 100.0,
                    "net_pnl": 20.0,
                },
                {
                    "trade_id": "bad",
                    "event_id": "event-2",
                    "contract_id": "contract-2",
                    "side": "long_yes",
                    "exit_at": pd.Timestamp("2025-01-04", tz="UTC"),
                    "exit_reason": "stop_loss",
                    "exit_probability": 0.30,
                    "units": 100.0,
                    "net_pnl": -15.0,
                },
            ]
        )

        decomposition = delayed_exit_decomposition(
            baseline, buffered, ConfirmationArm(1, 2)
        ).set_index("trade_id")

        self.assertTrue(decomposition.loc["saved", "saved_exit"])
        self.assertFalse(decomposition.loc["saved", "bad_delayed_exit"])
        self.assertFalse(decomposition.loc["bad", "saved_exit"])
        self.assertTrue(decomposition.loc["bad", "bad_delayed_exit"])
        self.assertEqual(decomposition.loc["saved", "delay_days"], 2.0)
        self.assertEqual(
            decomposition.loc["saved", "gross_exit_value_delta"], 30.0
        )

    def test_delayed_exit_summary_handles_empty_and_rolls_up_delays(self):
        empty = delayed_exit_summary(pd.DataFrame()).iloc[0]
        self.assertEqual(empty["delayed_exits_total"], 0)
        self.assertEqual(empty["delayed_exits_helped"], 0)
        self.assertEqual(empty["delayed_exits_hurt"], 0)
        self.assertEqual(empty["net_delay_pnl"], 0.0)
        self.assertEqual(empty["helped_pct"], 0.0)
        self.assertEqual(empty["hurt_pct"], 0.0)

        summary = delayed_exit_summary(
            pd.DataFrame(
                [
                    {
                        "saved_exit": True,
                        "bad_delayed_exit": False,
                        "net_pnl_delta": 30.0,
                    },
                    {
                        "saved_exit": False,
                        "bad_delayed_exit": True,
                        "net_pnl_delta": -25.0,
                    },
                    {
                        "saved_exit": True,
                        "bad_delayed_exit": False,
                        "net_pnl_delta": 5.0,
                    },
                ]
            )
        ).iloc[0]

        self.assertEqual(summary["delayed_exits_total"], 3)
        self.assertEqual(summary["delayed_exits_helped"], 2)
        self.assertEqual(summary["delayed_exits_hurt"], 1)
        self.assertEqual(summary["net_delay_pnl"], 10.0)
        self.assertAlmostEqual(summary["helped_pct"], 2 / 3)
        self.assertAlmostEqual(summary["hurt_pct"], 1 / 3)


if __name__ == "__main__":
    unittest.main()
