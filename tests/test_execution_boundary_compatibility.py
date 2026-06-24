from pathlib import Path
import unittest

import numpy as np
import pandas as pd

from vali.backtest import simulate_trades as legacy_simulate_trades
from vali.config import BacktestConfig, DataConfig, MarketConfig, ValiConfig
from vali.decisions import generate_decisions
from vali.execution.fees import (
    FEE_MODEL,
    provisional_fee,
    provisional_fee_metadata,
)
from vali.execution.liquidity import (
    capped_notional,
    entry_is_executable,
    signal_execution_rejection,
)
from vali.execution.settlement import (
    FAILED_PRE_SETTLEMENT_EXIT,
    finalize_settlement_exit,
)
from vali.execution.simulator import simulate_trades
from vali.execution.snapshots import (
    entry_quote,
    execution_validation_summary,
    exit_is_executable,
    liquidation_value,
)
from vali.pipeline import (
    execution_validation_summary as legacy_execution_validation_summary,
)
from vali.reporting import forecast_metrics


def execution_config() -> ValiConfig:
    return ValiConfig(
        data=DataConfig(
            Path("events"),
            Path("quotes"),
            Path("features"),
            Path("manifest"),
        ),
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


def execution_events() -> pd.DataFrame:
    meetings = pd.date_range(
        "2025-01-01 19:00", periods=3, freq="30D", tz="UTC"
    )
    return pd.DataFrame(
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


def failed_exit_signals(events: pd.DataFrame) -> pd.DataFrame:
    event = events.iloc[-1]
    return pd.DataFrame(
        [
            {
                "event_id": event["event_id"],
                "contract_id": event["contract_id"],
                "cutoff_at": event["meeting_at"] - pd.Timedelta(days=3),
                "action": "long_yes",
                "executable": True,
                "execution_liquidity_pass": True,
                "market_closed": False,
                "bid": 0.40,
                "ask": 0.50,
                "bid_depth": 200.0,
                "ask_depth": 80.0,
                "signed_divergence": 2.5,
                "regime": "attention_leading",
            },
            {
                "event_id": event["event_id"],
                "contract_id": event["contract_id"],
                "cutoff_at": event["meeting_at"] - pd.Timedelta(hours=23),
                "action": "none",
                "executable": False,
                "execution_liquidity_pass": False,
                "market_closed": True,
                "bid": np.nan,
                "ask": np.nan,
                "bid_depth": np.nan,
                "ask_depth": np.nan,
                "signed_divergence": 2.5,
                "regime": "attention_leading",
            },
        ]
    )


class ExecutionBoundaryCompatibilityTests(unittest.TestCase):
    def test_old_call_sites_and_new_execution_imports_are_available(self):
        for function in (
            legacy_simulate_trades,
            generate_decisions,
            legacy_execution_validation_summary,
            forecast_metrics,
            simulate_trades,
            signal_execution_rejection,
            provisional_fee,
            execution_validation_summary,
            finalize_settlement_exit,
        ):
            self.assertTrue(callable(function))

    def test_decision_execution_gates_and_closed_entries_are_unchanged(self):
        rows = pd.DataFrame(
            [
                {
                    "signed_divergence": 3.0,
                    "regime": "attention_leading",
                    "price_quality_pass": True,
                    "execution_liquidity_pass": True,
                    "depth_observed": True,
                    "executable": True,
                    "market_closed": True,
                },
                {
                    "signed_divergence": 3.0,
                    "regime": "attention_leading",
                    "price_quality_pass": True,
                    "execution_liquidity_pass": False,
                    "depth_observed": False,
                    "executable": False,
                    "market_closed": False,
                },
            ]
        )

        decisions = generate_decisions(rows, execution_config())

        self.assertEqual(
            decisions["decision_reason"].tolist(),
            ["market_closed", "depth_unobserved"],
        )
        self.assertEqual(
            [signal_execution_rejection(row) for row in rows.itertuples()],
            decisions["decision_reason"].tolist(),
        )
        self.assertFalse(entry_is_executable(rows.iloc[0]))

    def test_snapshot_summary_preserves_no_depth_capacity_gate(self):
        signals = pd.DataFrame(
            [
                {
                    "depth_observed": True,
                    "bid": 0.40,
                    "ask": 0.46,
                    "bid_depth": 200.0,
                    "ask_depth": 150.0,
                    "spread": 0.06,
                    "rejection_reason": "",
                    "price_quality_pass": True,
                    "execution_liquidity_pass": True,
                    "executable": True,
                    "market_closed": False,
                },
                {
                    "depth_observed": False,
                    "bid": np.nan,
                    "ask": np.nan,
                    "bid_depth": np.nan,
                    "ask_depth": np.nan,
                    "spread": np.nan,
                    "rejection_reason": "depth_unobserved",
                    "price_quality_pass": False,
                    "execution_liquidity_pass": False,
                    "executable": False,
                    "market_closed": False,
                },
            ]
        )

        legacy = legacy_execution_validation_summary(signals)
        extracted = execution_validation_summary(signals)

        self.assertEqual(legacy, extracted)
        self.assertEqual(extracted["snapshot_completeness"], 0.5)
        self.assertFalse(extracted["capacity_claims_enabled"])

    def test_quote_inversion_depth_cap_and_provisional_fee_are_unchanged(self):
        entry = pd.Series(
            {
                "bid": 0.40,
                "ask": 0.50,
                "bid_depth": 80.0,
                "ask_depth": 200.0,
            }
        )
        probability, depth = entry_quote(entry, "long_no")
        value, exit_probability = liquidation_value(
            pd.Series({"bid": 0.20, "ask": 0.30}), "long_no", 100.0
        )

        self.assertAlmostEqual(probability, 0.60)
        self.assertEqual(depth, 80.0)
        self.assertEqual(capped_notional(100.0, depth), 80.0)
        self.assertAlmostEqual(exit_probability, 0.70)
        self.assertAlmostEqual(value, 70.0)
        self.assertAlmostEqual(provisional_fee(80.0, 5), 0.04)
        self.assertEqual(FEE_MODEL, "provisional_bps")
        self.assertEqual(
            provisional_fee_metadata(5),
            {
                "fee_model": "provisional_bps",
                "fee_bps": 5,
                "fee_assumption_provisional": True,
            },
        )

    def test_incomplete_exit_and_failed_settlement_label_are_unchanged(self):
        row = pd.Series(
            {
                "executable": False,
                "execution_liquidity_pass": False,
                "market_closed": True,
                "bid": np.nan,
                "ask": np.nan,
            }
        )
        self.assertFalse(exit_is_executable(row))
        self.assertEqual(
            finalize_settlement_exit("settlement", True),
            (FAILED_PRE_SETTLEMENT_EXIT, True),
        )

    def test_simulator_wrapper_preserves_trades_schema_and_failed_exit(self):
        events = execution_events()
        events.loc[events.index[-1], "outcome"] = 1
        signals = failed_exit_signals(events)

        legacy_trades, legacy_exclusions = legacy_simulate_trades(
            signals, events, execution_config()
        )
        trades, exclusions = simulate_trades(
            signals, events, execution_config()
        )

        pd.testing.assert_frame_equal(legacy_trades, trades)
        pd.testing.assert_frame_equal(legacy_exclusions, exclusions)
        self.assertEqual(
            trades.iloc[0]["exit_reason"], FAILED_PRE_SETTLEMENT_EXIT
        )
        self.assertTrue(trades.iloc[0]["execution_failure"])
        self.assertEqual(trades.iloc[0]["entry_notional"], 80.0)
        self.assertEqual(trades.iloc[0]["fee_model"], "provisional_bps")
        self.assertEqual(
            trades.columns.tolist(),
            [
                "trade_id",
                "event_id",
                "contract_id",
                "side",
                "entry_at",
                "entry_probability",
                "entry_notional",
                "available_depth",
                "capacity_used",
                "units",
                "exit_at",
                "exit_probability",
                "exit_reason",
                "outcome",
                "entry_fee",
                "exit_fee",
                "fee_model",
                "fee_bps",
                "fee_assumption_provisional",
                "execution_failure",
                "net_pnl",
                "return",
                "hit",
            ],
        )


if __name__ == "__main__":
    unittest.main()
