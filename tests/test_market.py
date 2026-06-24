import unittest
from pathlib import Path

import pandas as pd

from vali.config import DataConfig, FeatureConfig, MarketConfig, ValiConfig
from vali.market import select_daily_market


def config(max_age=30):
    return ValiConfig(
        data=DataConfig(Path("e"), Path("q"), Path("f"), Path("m")),
        market=MarketConfig(max_spread=0.1, min_depth=100, max_quote_age_minutes=max_age, fallback_trade_window_minutes=120, fee_bps=5),
        features=FeatureConfig(timezone="UTC", daily_cutoff="16:00", standardization_window=3, min_periods=2),
        parameter_freeze_date="2026-06-23",
    )


def events():
    return pd.DataFrame(
        [{"event_id": "e1", "contract_id": "c1", "open_at": pd.Timestamp("2025-01-01 09:00", tz="UTC"), "meeting_at": pd.Timestamp("2025-01-03 19:00", tz="UTC"), "settlement_at": pd.Timestamp("2025-01-03 22:00", tz="UTC"), "outcome": 1}]
    )


class MarketTests(unittest.TestCase):
    def test_valid_quote_uses_executable_midpoint(self):
        quotes = pd.DataFrame(
            [{"contract_id": "c1", "observed_at": pd.Timestamp("2025-01-01 15:55", tz="UTC"), "bid": 0.4, "ask": 0.46, "last": 0.43, "volume": 100, "bid_depth": 200, "ask_depth": 150}]
        )
        market = select_daily_market(events(), quotes, None, config())
        first = market.iloc[0]
        self.assertAlmostEqual(first["price"], 0.43)
        self.assertTrue(first["executable"])
        self.assertTrue(first["price_quality_pass"])
        self.assertTrue(first["execution_liquidity_pass"])

    def test_stale_quote_can_fall_back_to_non_executable_vwap(self):
        quotes = pd.DataFrame(
            [{"contract_id": "c1", "observed_at": pd.Timestamp("2025-01-01 12:00", tz="UTC"), "bid": 0.4, "ask": 0.46, "last": 0.43, "volume": 100, "bid_depth": 200, "ask_depth": 150}]
        )
        trades = pd.DataFrame(
            [
                {"trade_id": "t1", "contract_id": "c1", "observed_at": pd.Timestamp("2025-01-01 15:30", tz="UTC"), "price": 0.50, "size": 200},
                {"trade_id": "t2", "contract_id": "c1", "observed_at": pd.Timestamp("2025-01-01 15:40", tz="UTC"), "price": 0.60, "size": 200},
            ]
        )
        market = select_daily_market(events(), quotes, trades, config(max_age=10))
        first = market.iloc[0]
        self.assertAlmostEqual(first["price"], 0.55)
        self.assertEqual(first["price_source"], "trade_vwap")
        self.assertFalse(first["executable"])

    def test_thin_depth_rejects_quote(self):
        quotes = pd.DataFrame(
            [{"contract_id": "c1", "observed_at": pd.Timestamp("2025-01-01 15:55", tz="UTC"), "bid": 0.4, "ask": 0.46, "last": 0.43, "volume": 100, "bid_depth": 99, "ask_depth": 500}]
        )
        market = select_daily_market(events(), quotes, None, config())
        self.assertTrue(market.iloc[0]["price_quality_pass"])
        self.assertFalse(market.iloc[0]["execution_liquidity_pass"])
        self.assertEqual(market.iloc[0]["rejection_reason"], "thin_depth")

    def test_historical_quote_without_depth_is_usable_but_not_executable(self):
        quotes = pd.DataFrame(
            [{"contract_id": "c1", "observed_at": pd.Timestamp("2025-01-01 15:55", tz="UTC"), "bid": 0.4, "ask": 0.46, "last": 0.43, "volume": 100, "bid_depth": float("nan"), "ask_depth": float("nan"), "depth_observed": False}]
        )
        market = select_daily_market(events(), quotes, None, config())
        first = market.iloc[0]
        self.assertTrue(first["price_quality_pass"])
        self.assertFalse(first["execution_liquidity_pass"])
        self.assertFalse(first["executable"])
        self.assertEqual(first["rejection_reason"], "depth_unobserved")


if __name__ == "__main__":
    unittest.main()
