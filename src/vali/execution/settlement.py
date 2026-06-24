"""Clear Horizon, settlement, and failed mandatory-exit helpers."""

from __future__ import annotations

from typing import Any

import pandas as pd


FAILED_PRE_SETTLEMENT_EXIT = (
    "forced_settlement_after_failed_pre_settlement_exit"
)


def latest_entry_at(meeting_at: Any, days_before_settlement: int) -> Any:
    return meeting_at - pd.Timedelta(days=days_before_settlement)


def settlement_probability(outcome: float, side: str) -> float:
    return float(outcome) if side == "long_yes" else 1.0 - float(outcome)


def finalize_settlement_exit(
    exit_reason: str, mandatory_exit_failed: bool
) -> tuple[str, bool]:
    execution_failure = exit_reason == "settlement" and mandatory_exit_failed
    if execution_failure:
        exit_reason = FAILED_PRE_SETTLEMENT_EXIT
    return exit_reason, execution_failure


__all__ = [
    "FAILED_PRE_SETTLEMENT_EXIT",
    "finalize_settlement_exit",
    "latest_entry_at",
    "settlement_probability",
]
