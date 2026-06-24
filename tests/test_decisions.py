import unittest
from pathlib import Path

import pandas as pd

from vali.config import DataConfig, MarketConfig, ValiConfig
from vali.decisions import generate_decisions
from vali.reporting import trade_metrics


class DecisionLiquidityTests(unittest.TestCase):
    def setUp(self):
        self.config = ValiConfig(
            data=DataConfig(Path("e"), Path("q"), Path("f"), Path("m")),
            market=MarketConfig(0.1, 100, 30, 120, 0),
            parameter_freeze_date="2026-06-23",
        )

    def test_price_only_historical_signal_never_becomes_trade(self):
        signals = pd.DataFrame(
            [
                {
                    "signed_divergence": 3.0,
                    "regime": "attention_leading",
                    "price_quality_pass": True,
                    "execution_liquidity_pass": False,
                    "depth_observed": False,
                    "executable": False,
                }
            ]
        )
        result = generate_decisions(signals, self.config)
        self.assertEqual(result.iloc[0]["action"], "none")
        self.assertEqual(result.iloc[0]["decision_reason"], "depth_unobserved")

    def test_unvalidated_execution_metrics_are_not_zero_returns(self):
        metrics = trade_metrics(pd.DataFrame(), execution_validated=False).set_index("metric")
        self.assertEqual(metrics.loc["execution_validated", "value"], 0)
        self.assertTrue(pd.isna(metrics.loc["net_pnl", "value"]))


if __name__ == "__main__":
    unittest.main()
