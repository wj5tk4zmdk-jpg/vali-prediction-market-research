import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from vali.backtest import run_walk_forward
from vali.config import BacktestConfig, DataConfig, MarketConfig, ValiConfig


def population_config() -> ValiConfig:
    return ValiConfig(
        data=DataConfig(Path("events"), Path("quotes"), Path("features"), Path("manifest")),
        market=MarketConfig(0.10, 100, 30, 120, 5),
        backtest=BacktestConfig(
            min_train_events=5,
            notional=100,
            stop_loss_fraction=0.25,
            max_holding_days=14,
            days_before_settlement=1,
            calibration_l2=1.0,
        ),
        parameter_freeze_date="2026-06-23",
    )


def resolved_events(count=7) -> pd.DataFrame:
    meetings = pd.date_range("2024-01-31 19:00", periods=count, freq="45D", tz="UTC")
    outcomes = [1, 1, 1, 0, 0, 0, 1][:count]
    return pd.DataFrame(
        [
            {
                "event_id": f"event-{index}",
                "contract_id": f"contract-{index}",
                "open_at": meeting - pd.Timedelta(days=30),
                "meeting_at": meeting,
                "settlement_at": meeting + pd.Timedelta(hours=4),
                "outcome": outcomes[index],
            }
            for index, meeting in enumerate(meetings)
        ]
    )


def market_snapshots(events: pd.DataFrame, included: set[int], duplicate_rows=False) -> pd.DataFrame:
    rows = []
    for index, event in enumerate(events.itertuples(index=False)):
        if index not in included:
            continue
        offsets = (3, 2) if duplicate_rows else (2,)
        for offset in offsets:
            probability = 0.35 + index * 0.03
            rows.append(
                {
                    "event_id": event.event_id,
                    "contract_id": event.contract_id,
                    "cutoff_at": event.meeting_at - pd.Timedelta(days=offset),
                    "price": probability,
                    "logit_price": np.log(probability / (1 - probability)),
                    "signed_divergence": -1.0 + index * 0.25,
                    "regime": "attention_leading",
                }
            )
    return pd.DataFrame(rows)


class WalkForwardPopulationTests(unittest.TestCase):
    def test_historical_frequency_uses_all_prior_resolved_events(self):
        events = resolved_events(6)
        signals = market_snapshots(events, {0, 2, 4, 5})

        forecasts, exclusions = run_walk_forward(signals, events, population_config())

        self.assertEqual(len(forecasts), 1)
        forecast = forecasts.iloc[0]
        self.assertEqual(forecast["event_id"], "event-5")
        self.assertEqual(forecast["training_events"], 5)
        self.assertEqual(forecast["calibration_training_events"], 3)
        self.assertAlmostEqual(forecast["historical_probability"], 3.5 / 6.0)
        self.assertTrue(pd.isna(forecast["vali_calibrated_probability"]))
        self.assertEqual(
            set(exclusions.loc[exclusions["reason"] == "no_eligible_market_price", "event_id"]),
            {"event-1", "event-3"},
        )

    def test_current_and_future_events_never_enter_earlier_baseline(self):
        events = resolved_events(7)
        signals = market_snapshots(events, set(range(7)))
        baseline, _ = run_walk_forward(signals, events, population_config())
        event_five = baseline.loc[baseline["event_id"] == "event-5"].iloc[0]

        changed = events.copy()
        changed.loc[5, "outcome"] = 1 - changed.loc[5, "outcome"]
        changed.loc[6, "outcome"] = 1 - changed.loc[6, "outcome"]
        rerun, _ = run_walk_forward(signals, changed, population_config())
        rerun_five = rerun.loc[rerun["event_id"] == "event-5"].iloc[0]

        self.assertEqual(event_five["training_events"], 5)
        self.assertAlmostEqual(
            event_five["historical_probability"], rerun_five["historical_probability"]
        )
        self.assertAlmostEqual(
            event_five["vali_calibrated_probability"],
            rerun_five["vali_calibrated_probability"],
        )

    def test_multiple_rows_from_one_event_never_split_event_folds(self):
        events = resolved_events(7)
        signals = market_snapshots(events, set(range(7)), duplicate_rows=True)

        forecasts, _ = run_walk_forward(signals, events, population_config())

        self.assertTrue(forecasts["event_id"].is_unique)
        self.assertEqual(set(forecasts["event_id"]), {"event-5", "event-6"})
        event_five = forecasts.loc[forecasts["event_id"] == "event-5"].iloc[0]
        self.assertEqual(event_five["training_events"], 5)
        self.assertEqual(
            event_five["forecast_at"], events.loc[5, "meeting_at"] - pd.Timedelta(days=2)
        )


if __name__ == "__main__":
    unittest.main()
