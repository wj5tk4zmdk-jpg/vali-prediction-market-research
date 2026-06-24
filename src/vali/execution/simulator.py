"""Execution-aware fixed-notional trade simulation."""

from __future__ import annotations

import pandas as pd

from ..configuration.contracts import ValiConfig
from ..data.validation import validate_event_identity
from .fees import provisional_fee, provisional_fee_metadata
from .liquidity import capacity_used, capped_notional, entry_is_executable
from .settlement import (
    finalize_settlement_exit,
    latest_entry_at,
    settlement_probability,
)
from .snapshots import entry_quote, exit_is_executable, liquidation_value


def simulate_trades(
    signals: pd.DataFrame,
    events: pd.DataFrame,
    config: ValiConfig,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Simulate at most one fixed-notional trade per out-of-sample event."""
    validate_event_identity(events, signals)
    resolved = (
        events.loc[events["outcome"].notna()]
        .sort_values("meeting_at")
        .reset_index(drop=True)
    )
    test_events = resolved.iloc[config.backtest.min_train_events :]
    trades: list[dict] = []
    exclusions: list[dict] = []

    for event in test_events.itertuples(index=False):
        history = signals.loc[
            signals["contract_id"] == event.contract_id
        ].sort_values("cutoff_at")
        latest_entry = latest_entry_at(
            event.meeting_at, config.backtest.days_before_settlement
        )
        candidates = history.loc[
            (history["cutoff_at"] <= latest_entry)
            & history["action"].isin(["long_yes", "long_no"])
        ]
        if candidates.empty:
            exclusions.append(
                {
                    "event_id": event.event_id,
                    "contract_id": event.contract_id,
                    "stage": "execution",
                    "reason": "no_trade_signal",
                }
            )
            continue
        entry = candidates.iloc[0]
        if not entry_is_executable(entry):
            exclusions.append(
                {
                    "event_id": event.event_id,
                    "contract_id": event.contract_id,
                    "stage": "execution",
                    "reason": "entry_not_executable",
                }
            )
            continue
        side = str(entry["action"])
        entry_probability, available_depth = entry_quote(entry, side)
        notional = capped_notional(config.backtest.notional, available_depth)
        if notional <= 0 or not 0 < entry_probability < 1:
            exclusions.append(
                {
                    "event_id": event.event_id,
                    "contract_id": event.contract_id,
                    "stage": "execution",
                    "reason": "entry_not_executable",
                }
            )
            continue
        units = notional / entry_probability
        entry_fee = provisional_fee(notional, config.market.fee_bps)
        exit_at = event.settlement_at
        exit_probability = settlement_probability(event.outcome, side)
        exit_value = units * exit_probability
        exit_fee = 0.0
        exit_reason = "settlement"
        mandatory_exit_failed = False

        later = history.loc[
            (history["cutoff_at"] > entry["cutoff_at"])
            & (history["cutoff_at"] <= event.settlement_at)
        ]
        for _, row in later.iterrows():
            if not exit_is_executable(row):
                if row["cutoff_at"] >= latest_entry:
                    mandatory_exit_failed = True
                continue
            current_value, current_probability = liquidation_value(
                row, side, units
            )
            holding_days = (
                row["cutoff_at"] - entry["cutoff_at"]
            ).total_seconds() / 86400
            reason = None
            if current_value <= notional * (
                1 - config.backtest.stop_loss_fraction
            ):
                reason = "stop_loss"
            elif row["regime"] != "attention_leading":
                reason = "regime_change"
            elif (
                abs(float(row["signed_divergence"]))
                <= config.signal.exit_threshold
            ):
                reason = "convergence"
            elif holding_days >= config.backtest.max_holding_days:
                reason = "max_holding_period"
            elif row["cutoff_at"] >= latest_entry:
                reason = "pre_settlement"
            if reason:
                exit_at = row["cutoff_at"]
                exit_probability = current_probability
                exit_value = current_value
                exit_fee = provisional_fee(
                    current_value, config.market.fee_bps
                )
                exit_reason = reason
                break

        exit_reason, execution_failure = finalize_settlement_exit(
            exit_reason, mandatory_exit_failed
        )
        pnl = exit_value - notional - entry_fee - exit_fee
        trades.append(
            {
                "trade_id": f"{event.event_id}-1",
                "event_id": event.event_id,
                "contract_id": event.contract_id,
                "side": side,
                "entry_at": entry["cutoff_at"],
                "entry_probability": entry_probability,
                "entry_notional": notional,
                "available_depth": available_depth,
                "capacity_used": capacity_used(notional, available_depth),
                "units": units,
                "exit_at": exit_at,
                "exit_probability": exit_probability,
                "exit_reason": exit_reason,
                "outcome": int(event.outcome),
                "entry_fee": entry_fee,
                "exit_fee": exit_fee,
                **provisional_fee_metadata(config.market.fee_bps),
                "execution_failure": execution_failure,
                "net_pnl": pnl,
                "return": pnl / (notional + entry_fee),
                "hit": pnl > 0,
            }
        )
    return pd.DataFrame(trades), pd.DataFrame(exclusions)


__all__ = ["simulate_trades"]
