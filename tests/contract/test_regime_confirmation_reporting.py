from pathlib import Path
import unittest

import pandas as pd

from vali.config import BacktestConfig, DataConfig, MarketConfig, ValiConfig
from vali.research.pipeline import regime_confirmation_metrics


class RegimeConfirmationReportingTests(unittest.TestCase):
    def test_pipeline_metrics_disclose_confirmation_settings_and_delays(self):
        config = ValiConfig(
            data=DataConfig(
                Path("events"),
                Path("quotes"),
                Path("features"),
                Path("manifest"),
            ),
            market=MarketConfig(0.10, 100, 30, 120, 5),
            backtest=BacktestConfig(
                entry_regime_confirmation_periods=2,
                exit_regime_confirmation_periods=3,
            ),
            parameter_freeze_date="2026-06-23",
        )
        signals = pd.DataFrame(
            {
                "decision_reason": [
                    "entry_regime_unconfirmed",
                    "entry_positive_divergence",
                    "entry_regime_unconfirmed",
                    "below_entry_threshold",
                ]
            }
        )
        trades = pd.DataFrame(
            {
                "exit_reason": ["regime_change", "regime_change", "stop_loss"],
                "exit_confirmation_delay_days": [2.0, 0.0, 0.0],
            }
        )

        metrics = regime_confirmation_metrics(
            signals, trades, config
        ).set_index("metric")

        self.assertEqual(
            metrics.loc["entry_regime_confirmation_periods", "value"], 2
        )
        self.assertEqual(
            metrics.loc["exit_regime_confirmation_periods", "value"], 3
        )
        self.assertEqual(
            metrics.loc[
                "entries_suppressed_by_regime_confirmation", "value"
            ],
            2,
        )
        self.assertEqual(
            metrics.loc["exits_delayed_by_regime_confirmation", "value"], 1
        )
        self.assertEqual(
            metrics.loc["mean_exit_confirmation_delay_days", "value"], 2.0
        )


if __name__ == "__main__":
    unittest.main()
