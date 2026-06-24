import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from vali.backtest import run_walk_forward
from vali.config import (
    BacktestConfig,
    DataConfig,
    FeatureConfig,
    MarketConfig,
    RegimeConfig,
    SignalConfig,
    ValiConfig,
)
from vali.decisions import generate_decisions
from vali.market import select_daily_market
from vali.regimes import classify_regimes
from vali.signals import compute_vali_signals


def isolation_config() -> ValiConfig:
    return ValiConfig(
        data=DataConfig(Path("events"), Path("quotes"), Path("features"), Path("manifest")),
        market=MarketConfig(0.10, 100, 30, 120, 5),
        features=FeatureConfig(
            timezone="UTC", daily_cutoff="16:00", standardization_window=3, min_periods=3
        ),
        signal=SignalConfig(
            velocity_window=3,
            normalization_window=3,
            min_periods=3,
            entry_threshold=2.0,
            exit_threshold=0.5,
            sensitivity_windows=(3, 14, 30),
        ),
        regime=RegimeConfig(
            window=7,
            min_periods=3,
            max_lag=2,
            min_abs_correlation=0.20,
            tie_margin=0.05,
        ),
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


def signal_time_tables(outcome: int):
    event = pd.DataFrame(
        [
            {
                "event_id": "future-event",
                "contract_id": "future-contract",
                "open_at": pd.Timestamp("2025-01-01 09:00", tz="UTC"),
                "meeting_at": pd.Timestamp("2025-01-16 19:00", tz="UTC"),
                "settlement_at": pd.Timestamp("2025-01-16 22:00", tz="UTC"),
                "outcome": outcome,
            }
        ]
    )
    quote_days = pd.date_range("2025-01-01", "2025-01-16", freq="D", tz="UTC")
    quote_rows = []
    for index, day in enumerate(quote_days):
        midpoint = 0.45 + 0.04 * np.sin(index / 2)
        quote_rows.append(
            {
                "contract_id": "future-contract",
                "observed_at": day.replace(hour=15, minute=55),
                "bid": midpoint - 0.02,
                "ask": midpoint + 0.02,
                "last": midpoint,
                "volume": 1000,
                "bid_depth": 500,
                "ask_depth": 500,
            }
        )
    market = select_daily_market(event, pd.DataFrame(quote_rows), None, isolation_config())
    attention = pd.DataFrame(
        {
            "cutoff_at": market["cutoff_at"].drop_duplicates().sort_values(),
            "attention": [
                float(index + np.sin(index / 3))
                for index in range(market["cutoff_at"].nunique())
            ],
        }
    )
    signals = compute_vali_signals(market, attention, isolation_config())
    predecision = classify_regimes(signals, isolation_config().regime)
    decisions = generate_decisions(predecision, isolation_config())
    return market, signals, predecision, decisions


class LabelIsolationTests(unittest.TestCase):
    def test_outcome_is_absent_from_signal_time_and_predecision_tables(self):
        market, signals, predecision, decisions = signal_time_tables(outcome=1)
        for table in (market, signals, predecision, decisions):
            self.assertNotIn("outcome", table.columns)

    def test_changing_future_outcome_cannot_change_prior_signals_or_decisions(self):
        zero = signal_time_tables(outcome=0)
        one = signal_time_tables(outcome=1)
        for zero_table, one_table in zip(zero, one, strict=True):
            pd.testing.assert_frame_equal(zero_table, one_table)

    def test_outcome_enters_only_walk_forward_evaluation_after_clear_horizon(self):
        meetings = pd.date_range("2025-03-01 19:00", periods=3, freq="30D", tz="UTC")
        events = pd.DataFrame(
            [
                {
                    "event_id": f"event-{index}",
                    "contract_id": f"contract-{index}",
                    "open_at": meeting - pd.Timedelta(days=20),
                    "meeting_at": meeting,
                    "settlement_at": meeting + pd.Timedelta(hours=4),
                    "outcome": index % 2,
                }
                for index, meeting in enumerate(meetings)
            ]
        )
        signals = pd.DataFrame(
            [
                {
                    "event_id": event.event_id,
                    "contract_id": event.contract_id,
                    "cutoff_at": event.meeting_at - pd.Timedelta(days=2),
                    "price": 0.40 + 0.05 * index,
                    "logit_price": np.log(
                        (0.40 + 0.05 * index) / (0.60 - 0.05 * index)
                    ),
                    "signed_divergence": -1.0 + index,
                    "regime": "attention_leading",
                }
                for index, event in enumerate(events.itertuples(index=False))
            ]
        )
        self.assertNotIn("outcome", signals.columns)

        forecasts, _ = run_walk_forward(signals, events, isolation_config())

        self.assertIn("outcome", forecasts.columns)
        self.assertEqual(len(forecasts), 1)
        self.assertLessEqual(
            forecasts.iloc[0]["forecast_at"],
            forecasts.iloc[0]["meeting_at"] - pd.Timedelta(days=1),
        )

        changed = events.copy()
        changed.loc[changed.index[-1], "outcome"] = 1 - changed.loc[changed.index[-1], "outcome"]
        changed_forecasts, _ = run_walk_forward(signals, changed, isolation_config())
        pd.testing.assert_series_equal(
            forecasts[["market_probability", "historical_probability", "vali_calibrated_probability"]].iloc[0],
            changed_forecasts[["market_probability", "historical_probability", "vali_calibrated_probability"]].iloc[0],
            check_names=False,
        )


if __name__ == "__main__":
    unittest.main()
