import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import numpy as np
import pandas as pd

from vali.backtest import run_walk_forward as legacy_run_walk_forward
from vali.calibration import (
    fit_logistic as legacy_fit_logistic,
    predict_logistic as legacy_predict_logistic,
)
from vali.config import BacktestConfig, DataConfig, MarketConfig, ValiConfig
from vali.pipeline import (
    PipelineResult as LegacyPipelineResult,
    execution_validation_summary as legacy_execution_summary,
    run_backtest_pipeline as legacy_run_backtest_pipeline,
    run_signal_pipeline as legacy_run_signal_pipeline,
)
from vali.research.calibration import fit_logistic, predict_logistic
from vali.research.pipeline import (
    PipelineResult,
    execution_validation_summary,
    run_backtest_pipeline,
    run_signal_pipeline,
)
from vali.research.sensitivity import run_sensitivity
from vali.research.walk_forward import run_walk_forward
from vali.sample import make_synthetic_dataset


def research_config() -> ValiConfig:
    return ValiConfig(
        data=DataConfig(Path("events"), Path("quotes"), Path("features"), Path("manifest")),
        market=MarketConfig(0.10, 100, 30, 120, 5),
        backtest=BacktestConfig(
            min_train_events=2,
            notional=100,
            stop_loss_fraction=0.25,
            max_holding_days=14,
            days_before_settlement=1,
            calibration_l2=1.0,
        ),
        parameter_freeze_date="2026-06-23",
    )


def research_frames(count=4):
    meetings = pd.date_range("2025-01-31 19:00", periods=count, freq="45D", tz="UTC")
    events = []
    signals = []
    for index, meeting in enumerate(meetings):
        probability = 0.35 + 0.05 * index
        events.append(
            {
                "event_id": f"event-{index}",
                "contract_id": f"contract-{index}",
                "open_at": meeting - pd.Timedelta(days=20),
                "meeting_at": meeting,
                "settlement_at": meeting + pd.Timedelta(hours=4),
                "yes_label": "lower",
                "outcome": index % 2,
            }
        )
        signals.append(
            {
                "event_id": f"event-{index}",
                "contract_id": f"contract-{index}",
                "cutoff_at": meeting - pd.Timedelta(days=2),
                "price": probability,
                "logit_price": np.log(probability / (1 - probability)),
                "signed_divergence": -1.0 + index,
                "regime": "attention_leading",
            }
        )
    return pd.DataFrame(events), pd.DataFrame(signals)


class ResearchBoundaryCompatibilityTests(unittest.TestCase):
    def test_old_and_new_research_imports_are_available(self):
        self.assertIs(LegacyPipelineResult, PipelineResult)
        for function in (
            legacy_fit_logistic,
            fit_logistic,
            legacy_run_walk_forward,
            run_walk_forward,
            legacy_run_signal_pipeline,
            run_signal_pipeline,
            legacy_run_backtest_pipeline,
            run_backtest_pipeline,
            run_sensitivity,
        ):
            self.assertTrue(callable(function))

    def test_calibration_wrapper_matches_research_boundary(self):
        x = np.array([[-1.0, 0.5], [0.0, -0.5], [1.0, 1.5], [2.0, -1.0]])
        y = np.array([0.0, 0.0, 1.0, 1.0])
        legacy_coefficients = legacy_fit_logistic(x, y, l2=1.0)
        coefficients = fit_logistic(x, y, l2=1.0)

        np.testing.assert_array_equal(legacy_coefficients, coefficients)
        np.testing.assert_array_equal(
            legacy_predict_logistic(legacy_coefficients, x),
            predict_logistic(coefficients, x),
        )

    def test_walk_forward_wrapper_preserves_folds_and_outputs(self):
        events, signals = research_frames()
        legacy_forecasts, legacy_exclusions = legacy_run_walk_forward(
            signals, events, research_config()
        )
        forecasts, exclusions = run_walk_forward(signals, events, research_config())

        pd.testing.assert_frame_equal(legacy_forecasts, forecasts)
        pd.testing.assert_frame_equal(legacy_exclusions, exclusions)
        self.assertEqual(forecasts["training_events"].tolist(), [2, 3])
        self.assertTrue(forecasts["event_id"].is_unique)

    def test_execution_summary_wrapper_is_identical(self):
        signals = pd.DataFrame(
            [
                {
                    "depth_observed": True,
                    "bid": 0.40,
                    "ask": 0.45,
                    "bid_depth": 200.0,
                    "ask_depth": 200.0,
                    "spread": 0.05,
                    "rejection_reason": "",
                    "price_quality_pass": True,
                    "execution_liquidity_pass": True,
                    "executable": True,
                    "market_closed": False,
                }
            ]
        )
        self.assertEqual(
            legacy_execution_summary(signals), execution_validation_summary(signals)
        )

    def test_signal_pipeline_wrapper_preserves_tables_and_manifest(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            config_path = make_synthetic_dataset(root / "data", seed=7, event_count=3)
            config = ValiConfig.from_toml(config_path)

            legacy = legacy_run_signal_pipeline(config, root / "legacy")
            extracted = run_signal_pipeline(config, root / "extracted")

            pd.testing.assert_frame_equal(legacy.signals, extracted.signals)
            pd.testing.assert_frame_equal(legacy.exclusions, extracted.exclusions)
            legacy_files = {path.name for path in (root / "legacy").iterdir()}
            extracted_files = {path.name for path in (root / "extracted").iterdir()}
            self.assertEqual(legacy_files, extracted_files)
            legacy_manifest = json.loads(
                (root / "legacy" / "run_manifest.json").read_text(encoding="utf-8")
            )
            extracted_manifest = json.loads(
                (root / "extracted" / "run_manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(legacy_manifest, extracted_manifest)


if __name__ == "__main__":
    unittest.main()
