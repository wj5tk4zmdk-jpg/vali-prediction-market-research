"""Event-grouped walk-forward calibration and execution-aware simulation."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import ValiConfig
from .io import validate_event_identity
from .research.walk_forward import (
    event_snapshots as _research_event_snapshots,
    run_walk_forward as _research_run_walk_forward,
)


@dataclass
class BacktestResult:
    forecasts: pd.DataFrame
    trades: pd.DataFrame
    exclusions: pd.DataFrame


def _event_snapshots(
    signals: pd.DataFrame,
    events: pd.DataFrame,
    days_before: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    return _research_event_snapshots(signals, events, days_before)


def run_walk_forward(
    signals: pd.DataFrame, events: pd.DataFrame, config: ValiConfig
) -> tuple[pd.DataFrame, pd.DataFrame]:
    return _research_run_walk_forward(signals, events, config)


def _liquidation_value(row: pd.Series, side: str, units: float) -> tuple[float, float]:
    if side == "long_yes":
        probability = float(row["bid"])
    else:
        probability = 1.0 - float(row["ask"])
    return units * probability, probability


def simulate_trades(
    signals: pd.DataFrame,
    events: pd.DataFrame,
    config: ValiConfig,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Simulate at most one fixed-notional trade per out-of-sample event."""
    validate_event_identity(events, signals)
    resolved = events.loc[events["outcome"].notna()].sort_values("meeting_at").reset_index(drop=True)
    test_events = resolved.iloc[config.backtest.min_train_events :]
    trades: list[dict] = []
    exclusions: list[dict] = []
    fee_rate = config.market.fee_bps / 10_000

    for event in test_events.itertuples(index=False):
        history = signals.loc[signals["contract_id"] == event.contract_id].sort_values("cutoff_at")
        latest_entry = event.meeting_at - pd.Timedelta(days=config.backtest.days_before_settlement)
        candidates = history.loc[(history["cutoff_at"] <= latest_entry) & history["action"].isin(["long_yes", "long_no"])]
        if candidates.empty:
            exclusions.append(
                {"event_id": event.event_id, "contract_id": event.contract_id, "stage": "execution", "reason": "no_trade_signal"}
            )
            continue
        entry = candidates.iloc[0]
        entry_executable = bool(entry.get("executable", False))
        entry_liquid = bool(entry.get("execution_liquidity_pass", entry_executable))
        entry_closed = bool(entry.get("market_closed", False))
        if entry_closed or not entry_executable or not entry_liquid:
            exclusions.append(
                {"event_id": event.event_id, "contract_id": event.contract_id, "stage": "execution", "reason": "entry_not_executable"}
            )
            continue
        side = str(entry["action"])
        if side == "long_yes":
            entry_probability = float(entry["ask"])
            available_depth = float(entry["ask_depth"])
        else:
            entry_probability = 1.0 - float(entry["bid"])
            available_depth = float(entry["bid_depth"])
        notional = min(config.backtest.notional, available_depth)
        if notional <= 0 or not 0 < entry_probability < 1:
            exclusions.append(
                {"event_id": event.event_id, "contract_id": event.contract_id, "stage": "execution", "reason": "entry_not_executable"}
            )
            continue
        units = notional / entry_probability
        entry_fee = notional * fee_rate
        exit_at = event.settlement_at
        exit_probability = float(event.outcome) if side == "long_yes" else 1.0 - float(event.outcome)
        exit_value = units * exit_probability
        exit_fee = 0.0
        exit_reason = "settlement"
        mandatory_exit_failed = False

        later = history.loc[
            (history["cutoff_at"] > entry["cutoff_at"]) & (history["cutoff_at"] <= event.settlement_at)
        ]
        for _, row in later.iterrows():
            market_closed = bool(row.get("market_closed", False))
            executable = (
                bool(row["executable"])
                and bool(row.get("execution_liquidity_pass", True))
                and not market_closed
                and pd.notna(row["bid"])
                and pd.notna(row["ask"])
            )
            if not executable:
                if row["cutoff_at"] >= latest_entry:
                    mandatory_exit_failed = True
                continue
            current_value, current_probability = _liquidation_value(row, side, units)
            holding_days = (row["cutoff_at"] - entry["cutoff_at"]).total_seconds() / 86400
            reason = None
            if current_value <= notional * (1 - config.backtest.stop_loss_fraction):
                reason = "stop_loss"
            elif row["regime"] != "attention_leading":
                reason = "regime_change"
            elif abs(float(row["signed_divergence"])) <= config.signal.exit_threshold:
                reason = "convergence"
            elif holding_days >= config.backtest.max_holding_days:
                reason = "max_holding_period"
            elif row["cutoff_at"] >= latest_entry:
                reason = "pre_settlement"
            if reason:
                exit_at = row["cutoff_at"]
                exit_probability = current_probability
                exit_value = current_value
                exit_fee = current_value * fee_rate
                exit_reason = reason
                break

        execution_failure = exit_reason == "settlement" and mandatory_exit_failed
        if execution_failure:
            exit_reason = "forced_settlement_after_failed_pre_settlement_exit"

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
                "capacity_used": notional / available_depth if available_depth else np.nan,
                "units": units,
                "exit_at": exit_at,
                "exit_probability": exit_probability,
                "exit_reason": exit_reason,
                "outcome": int(event.outcome),
                "entry_fee": entry_fee,
                "exit_fee": exit_fee,
                "fee_model": "provisional_bps",
                "fee_bps": config.market.fee_bps,
                "fee_assumption_provisional": True,
                "execution_failure": execution_failure,
                "net_pnl": pnl,
                "return": pnl / (notional + entry_fee),
                "hit": pnl > 0,
            }
        )
    return pd.DataFrame(trades), pd.DataFrame(exclusions)


def run_backtest(
    signals: pd.DataFrame, events: pd.DataFrame, config: ValiConfig
) -> BacktestResult:
    forecasts, forecast_exclusions = run_walk_forward(signals, events, config)
    trades, trade_exclusions = simulate_trades(signals, events, config)
    exclusions = pd.concat([forecast_exclusions, trade_exclusions], ignore_index=True)
    return BacktestResult(forecasts=forecasts, trades=trades, exclusions=exclusions)
