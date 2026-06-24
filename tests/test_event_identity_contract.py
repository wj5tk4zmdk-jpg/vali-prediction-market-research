import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from vali.backtest import run_walk_forward
from vali.config import BacktestConfig, DataConfig, MarketConfig, ValiConfig
from vali.io import DataValidationError, validate_event_identity
from vali.market import build_daily_cutoffs


def identity_config() -> ValiConfig:
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


def easing_events(count=3) -> pd.DataFrame:
    meetings = pd.date_range("2025-01-31 19:00", periods=count, freq="45D", tz="UTC")
    return pd.DataFrame(
        [
            {
                "event_id": f"event-{index}",
                "contract_id": f"contract-{index}",
                "internal_event_type": "EASING",
                "open_at": meeting - pd.Timedelta(days=20),
                "meeting_at": meeting,
                "settlement_at": meeting + pd.Timedelta(hours=4),
                "yes_label": "Fed target range lower after scheduled meeting",
                "outcome": index % 2,
            }
            for index, meeting in enumerate(meetings)
        ]
    )


def identity_signals(events: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for index, event in enumerate(events.itertuples(index=False)):
        probability = 0.40 + index * 0.05
        rows.append(
            {
                "event_id": event.event_id,
                "contract_id": event.contract_id,
                "cutoff_at": event.meeting_at - pd.Timedelta(days=2),
                "price": probability,
                "logit_price": np.log(probability / (1 - probability)),
                "signed_divergence": float(index - 1),
                "regime": "attention_leading",
            }
        )
    return pd.DataFrame(rows)


class EventIdentityContractTests(unittest.TestCase):
    def test_duplicate_easing_events_for_one_meeting_are_rejected(self):
        events = easing_events(2)
        duplicate = events.iloc[[0]].copy()
        duplicate["event_id"] = "event-duplicate"
        duplicate["contract_id"] = "contract-duplicate"

        with self.assertRaisesRegex(DataValidationError, "duplicate internal EASING"):
            validate_event_identity(pd.concat([events, duplicate], ignore_index=True))

    def test_missing_internal_easing_event_is_a_validation_failure(self):
        events = easing_events(1)
        events["internal_event_type"] = "TIGHTENING"

        with self.assertRaisesRegex(DataValidationError, "missing internal EASING"):
            validate_event_identity(events)

    def test_duplicate_identity_is_rejected_before_walk_forward(self):
        events = easing_events(3)
        duplicate = events.iloc[[0]].copy()
        duplicate["event_id"] = "event-duplicate"
        duplicate["contract_id"] = "contract-duplicate"
        invalid_events = pd.concat([events, duplicate], ignore_index=True)

        with self.assertRaisesRegex(DataValidationError, "duplicate internal EASING"):
            run_walk_forward(identity_signals(events), invalid_events, identity_config())

    def test_event_identifiers_remain_stable_across_core_tables(self):
        events = easing_events(3)
        signals = identity_signals(events)
        validate_event_identity(events, signals)
        market = build_daily_cutoffs(events, identity_config())
        forecasts, _ = run_walk_forward(signals, events, identity_config())
        expected = events.set_index("contract_id")["event_id"]

        for table in (market, signals, forecasts):
            actual = table["contract_id"].map(expected)
            pd.testing.assert_series_equal(
                table["event_id"].reset_index(drop=True),
                actual.reset_index(drop=True),
                check_names=False,
            )

        mismatched = signals.copy()
        mismatched.loc[0, "event_id"] = "wrong-event"
        with self.assertRaisesRegex(DataValidationError, "event identity mismatch"):
            validate_event_identity(events, mismatched)


if __name__ == "__main__":
    unittest.main()
