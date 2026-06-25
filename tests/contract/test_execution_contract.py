import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from vali.backtest import simulate_trades
from vali.config import (
    BacktestConfig,
    ConfigError,
    DataConfig,
    MarketConfig,
    ValiConfig,
)
from vali.decisions import generate_decisions
from vali.pipeline import execution_validation_summary


def execution_config(
    *,
    entry_confirmation: int = 1,
    exit_confirmation: int = 1,
    max_holding_days: int = 14,
) -> ValiConfig:
    return ValiConfig(
        data=DataConfig(Path("events"), Path("quotes"), Path("features"), Path("manifest")),
        market=MarketConfig(0.10, 100, 30, 120, 5),
        backtest=BacktestConfig(
            min_train_events=2,
            notional=100,
            stop_loss_fraction=0.25,
            max_holding_days=max_holding_days,
            days_before_settlement=1,
            calibration_l2=1.0,
            entry_regime_confirmation_periods=entry_confirmation,
            exit_regime_confirmation_periods=exit_confirmation,
        ),
        parameter_freeze_date="2026-06-23",
    )


def execution_events() -> pd.DataFrame:
    meetings = pd.date_range("2025-01-01 19:00", periods=3, freq="30D", tz="UTC")
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


def complete_snapshot(**overrides) -> dict:
    row = {
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
    }
    row.update(overrides)
    return row


def decision_snapshot(**overrides) -> dict:
    row = {
        "contract_id": "contract-2",
        "signed_divergence": 3.0,
        "regime": "attention_leading",
        "price_quality_pass": True,
        "execution_liquidity_pass": True,
        "depth_observed": True,
        "executable": True,
        "market_closed": False,
    }
    row.update(overrides)
    return row


def exit_signal(event: pd.Series, *, days_before: float, **overrides) -> dict:
    row = {
        "event_id": event["event_id"],
        "contract_id": event["contract_id"],
        "cutoff_at": event["meeting_at"] - pd.Timedelta(days=days_before),
        "action": "none",
        "executable": True,
        "execution_liquidity_pass": True,
        "market_closed": False,
        "bid": 0.40,
        "ask": 0.50,
        "bid_depth": 200.0,
        "ask_depth": 200.0,
        "signed_divergence": 2.5,
        "regime": "attention_leading",
    }
    row.update(overrides)
    return row


class ExecutionContractTests(unittest.TestCase):
    def test_any_observed_depth_is_not_sufficient_for_execution_reporting(self):
        signals = pd.DataFrame(
            [
                complete_snapshot(),
                complete_snapshot(
                    depth_observed=False,
                    bid=np.nan,
                    ask=np.nan,
                    bid_depth=np.nan,
                    ask_depth=np.nan,
                    spread=np.nan,
                    rejection_reason="depth_unobserved",
                ),
            ]
        )

        summary = execution_validation_summary(signals)

        self.assertEqual(summary["status"], "unvalidated_incomplete_execution_snapshots")
        self.assertAlmostEqual(summary["snapshot_completeness"], 0.5)
        self.assertFalse(summary["capacity_claims_enabled"])

    def test_spread_depth_and_executable_quote_gates_remain_separate(self):
        rows = pd.DataFrame(
            [
                {
                    "signed_divergence": 3.0,
                    "regime": "attention_leading",
                    "price_quality_pass": False,
                    "execution_liquidity_pass": True,
                    "depth_observed": True,
                    "executable": True,
                    "market_closed": False,
                },
                {
                    "signed_divergence": 3.0,
                    "regime": "attention_leading",
                    "price_quality_pass": True,
                    "execution_liquidity_pass": False,
                    "depth_observed": True,
                    "executable": False,
                    "market_closed": False,
                },
                {
                    "signed_divergence": 3.0,
                    "regime": "attention_leading",
                    "price_quality_pass": True,
                    "execution_liquidity_pass": True,
                    "depth_observed": True,
                    "executable": False,
                    "market_closed": False,
                },
            ]
        )

        decisions = generate_decisions(rows, execution_config())

        self.assertEqual(
            decisions["decision_reason"].tolist(),
            ["price_quality_failed", "execution_liquidity_failed", "price_not_executable"],
        )
        self.assertTrue((decisions["action"] == "none").all())

    def test_market_closure_prevents_execution_claim(self):
        signals = pd.DataFrame(
            [
                {
                    "signed_divergence": 3.0,
                    "regime": "attention_leading",
                    "price_quality_pass": True,
                    "execution_liquidity_pass": True,
                    "depth_observed": True,
                    "executable": True,
                    "market_closed": True,
                }
            ]
        )

        decisions = generate_decisions(signals, execution_config())

        self.assertEqual(decisions.iloc[0]["action"], "none")
        self.assertEqual(decisions.iloc[0]["decision_reason"], "market_closed")

    def test_default_regime_confirmation_preserves_entry_actions_and_reasons(self):
        rows = pd.DataFrame(
            [
                decision_snapshot(signed_divergence=3.0),
                decision_snapshot(signed_divergence=-3.0),
                decision_snapshot(signed_divergence=0.2),
                decision_snapshot(regime="unstable"),
            ]
        )

        decisions = generate_decisions(rows, execution_config())

        self.assertEqual(
            decisions["action"].tolist(),
            ["long_yes", "long_no", "none", "none"],
        )
        self.assertEqual(
            decisions["decision_reason"].tolist(),
            [
                "entry_positive_divergence",
                "entry_negative_divergence",
                "below_entry_threshold",
                "regime_unstable",
            ],
        )
        self.assertEqual(
            decisions["entry_regime_confirmed"].tolist(),
            [True, True, False, False],
        )
        self.assertEqual(
            decisions["entry_confirmation_streak"].tolist(), [1, 2, 0, 0]
        )

    def test_entry_confirmation_requires_consecutive_eligible_attention_rows(self):
        rows = pd.DataFrame([decision_snapshot(), decision_snapshot()])

        decisions = generate_decisions(
            rows, execution_config(entry_confirmation=2)
        )

        self.assertEqual(decisions["action"].tolist(), ["none", "long_yes"])
        self.assertEqual(
            decisions["decision_reason"].tolist(),
            ["entry_regime_unconfirmed", "entry_positive_divergence"],
        )
        self.assertEqual(
            decisions["entry_confirmation_streak"].tolist(), [1, 2]
        )
        self.assertEqual(
            decisions["entry_regime_confirmed"].tolist(), [False, True]
        )

    def test_entry_confirmation_resets_on_missing_regime_failed_gates_and_threshold(self):
        rows = pd.DataFrame(
            [
                decision_snapshot(),
                decision_snapshot(regime=np.nan),
                decision_snapshot(),
                decision_snapshot(execution_liquidity_pass=False),
                decision_snapshot(),
                decision_snapshot(market_closed=True),
                decision_snapshot(),
                decision_snapshot(signed_divergence=0.1),
                decision_snapshot(),
            ]
        )

        decisions = generate_decisions(
            rows, execution_config(entry_confirmation=2)
        )

        self.assertEqual(decisions["action"].tolist(), ["none"] * len(rows))
        self.assertEqual(
            decisions["decision_reason"].tolist(),
            [
                "entry_regime_unconfirmed",
                "regime_nan",
                "entry_regime_unconfirmed",
                "execution_liquidity_failed",
                "entry_regime_unconfirmed",
                "market_closed",
                "entry_regime_unconfirmed",
                "below_entry_threshold",
                "entry_regime_unconfirmed",
            ],
        )
        self.assertEqual(
            decisions["entry_confirmation_streak"].tolist(),
            [1, 0, 1, 0, 1, 0, 1, 0, 1],
        )

    def test_invalid_regime_confirmation_periods_are_rejected(self):
        for kwargs in (
            {"entry_regime_confirmation_periods": 0},
            {"exit_regime_confirmation_periods": 0},
            {"entry_regime_confirmation_periods": 1.5},
            {"exit_regime_confirmation_periods": False},
        ):
            with self.subTest(kwargs=kwargs):
                config = BacktestConfig(**kwargs)
                with self.assertRaisesRegex(
                    ConfigError, "regime confirmation periods"
                ):
                    config.validate()

    def test_long_no_inversion_depth_cap_and_provisional_fees_are_explicit(self):
        events = execution_events()
        event = events.iloc[-1]
        signals = pd.DataFrame(
            [
                {
                    "event_id": event["event_id"],
                    "contract_id": event["contract_id"],
                    "cutoff_at": event["meeting_at"] - pd.Timedelta(days=3),
                    "action": "long_no",
                    "executable": True,
                    "execution_liquidity_pass": True,
                    "market_closed": False,
                    "bid": 0.40,
                    "ask": 0.50,
                    "bid_depth": 80.0,
                    "ask_depth": 200.0,
                    "signed_divergence": -2.5,
                    "regime": "attention_leading",
                },
                {
                    "event_id": event["event_id"],
                    "contract_id": event["contract_id"],
                    "cutoff_at": event["meeting_at"] - pd.Timedelta(days=2),
                    "action": "none",
                    "executable": True,
                    "execution_liquidity_pass": True,
                    "market_closed": False,
                    "bid": 0.20,
                    "ask": 0.30,
                    "bid_depth": 500.0,
                    "ask_depth": 500.0,
                    "signed_divergence": 0.0,
                    "regime": "attention_leading",
                },
            ]
        )

        trades, _ = simulate_trades(signals, events, execution_config())

        trade = trades.iloc[0]
        self.assertAlmostEqual(trade["entry_probability"], 0.60)
        self.assertAlmostEqual(trade["exit_probability"], 0.70)
        self.assertAlmostEqual(trade["entry_notional"], 80.0)
        self.assertAlmostEqual(trade["capacity_used"], 1.0)
        self.assertEqual(trade["fee_model"], "provisional_bps")
        self.assertEqual(trade["fee_bps"], 5)
        self.assertTrue(trade["fee_assumption_provisional"])

    def test_failed_mandatory_exit_is_explicit_forced_settlement(self):
        events = execution_events()
        event = events.iloc[-1].copy()
        events.loc[events.index[-1], "outcome"] = 1
        signals = pd.DataFrame(
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
                    "ask_depth": 200.0,
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

        trades, _ = simulate_trades(signals, events, execution_config())

        trade = trades.iloc[0]
        self.assertEqual(trade["exit_reason"], "forced_settlement_after_failed_pre_settlement_exit")
        self.assertTrue(trade["execution_failure"])
        self.assertEqual(trade["exit_at"], events.iloc[-1]["settlement_at"])

    def test_exit_confirmation_buffers_single_day_regime_blip(self):
        events = execution_events()
        events.loc[events.index[-1], "outcome"] = 1
        event = events.iloc[-1]
        signals = pd.DataFrame(
            [
                exit_signal(
                    event,
                    days_before=5,
                    action="long_yes",
                    bid=0.40,
                    ask=0.50,
                ),
                exit_signal(event, days_before=4, regime="unstable"),
                exit_signal(event, days_before=3, regime="attention_leading"),
            ]
        )

        trades, _ = simulate_trades(
            signals, events, execution_config(exit_confirmation=2)
        )

        trade = trades.iloc[0]
        self.assertEqual(trade["exit_reason"], "settlement")
        self.assertFalse(trade["exit_regime_confirmed"])
        self.assertEqual(trade["exit_confirmation_streak"], 0)
        self.assertEqual(trade["exit_confirmation_delay_days"], 0.0)

    def test_exit_confirmation_exits_after_two_consecutive_non_attention_rows(self):
        events = execution_events()
        events.loc[events.index[-1], "outcome"] = 1
        event = events.iloc[-1]
        first_flip = event["meeting_at"] - pd.Timedelta(days=4)
        second_flip = event["meeting_at"] - pd.Timedelta(days=3)
        signals = pd.DataFrame(
            [
                exit_signal(event, days_before=5, action="long_yes"),
                exit_signal(event, days_before=4, regime="unstable"),
                exit_signal(event, days_before=3, regime="market_leading"),
            ]
        )

        trades, _ = simulate_trades(
            signals, events, execution_config(exit_confirmation=2)
        )

        trade = trades.iloc[0]
        self.assertEqual(trade["exit_reason"], "regime_change")
        self.assertEqual(trade["exit_at"], second_flip)
        self.assertTrue(trade["exit_regime_confirmed"])
        self.assertEqual(trade["exit_confirmation_streak"], 2)
        self.assertAlmostEqual(
            trade["exit_confirmation_delay_days"],
            (second_flip - first_flip).total_seconds() / 86400,
        )

    def test_immediate_exits_override_exit_confirmation(self):
        events = execution_events()
        events.loc[events.index[-1], "outcome"] = 1
        event = events.iloc[-1]
        cases = {
            "convergence": [
                exit_signal(event, days_before=5, action="long_yes"),
                exit_signal(
                    event,
                    days_before=4,
                    regime="unstable",
                    signed_divergence=0.1,
                ),
            ],
            "stop_loss": [
                exit_signal(event, days_before=5, action="long_yes"),
                exit_signal(event, days_before=4, regime="unstable", bid=0.30),
            ],
            "max_holding_period": [
                exit_signal(event, days_before=5, action="long_yes"),
                exit_signal(event, days_before=3, regime="unstable"),
            ],
            "pre_settlement": [
                exit_signal(event, days_before=5, action="long_yes"),
                exit_signal(event, days_before=1, regime="unstable"),
            ],
        }
        configs = {
            "convergence": execution_config(exit_confirmation=2),
            "stop_loss": execution_config(exit_confirmation=2),
            "max_holding_period": execution_config(
                exit_confirmation=2, max_holding_days=2
            ),
            "pre_settlement": execution_config(exit_confirmation=2),
        }
        for expected_reason, rows in cases.items():
            with self.subTest(expected_reason=expected_reason):
                trades, _ = simulate_trades(
                    pd.DataFrame(rows), events, configs[expected_reason]
                )
                trade = trades.iloc[0]
                self.assertEqual(trade["exit_reason"], expected_reason)
                self.assertFalse(trade["exit_regime_confirmed"])


if __name__ == "__main__":
    unittest.main()
