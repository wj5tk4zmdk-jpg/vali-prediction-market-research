"""Execution eligibility, liquidity gates, and capacity helpers."""

from __future__ import annotations

from typing import Any


def signal_execution_rejection(row: Any) -> str | None:
    """Return the existing decision-time execution rejection, if any."""
    if bool(getattr(row, "market_closed", False)):
        return "market_closed"
    if not bool(row.price_quality_pass):
        return "price_quality_failed"
    if not bool(row.execution_liquidity_pass):
        return (
            "depth_unobserved"
            if not bool(row.depth_observed)
            else "execution_liquidity_failed"
        )
    if not bool(row.executable):
        return "price_not_executable"
    return None


def entry_is_executable(entry: Any) -> bool:
    entry_executable = bool(entry.get("executable", False))
    entry_liquid = bool(
        entry.get("execution_liquidity_pass", entry_executable)
    )
    entry_closed = bool(entry.get("market_closed", False))
    return not entry_closed and entry_executable and entry_liquid


def capped_notional(requested_notional: float, available_depth: float) -> float:
    return min(requested_notional, available_depth)


def capacity_used(notional: float, available_depth: float) -> float:
    return notional / available_depth if available_depth else float("nan")


__all__ = [
    "capacity_used",
    "capped_notional",
    "entry_is_executable",
    "signal_execution_rejection",
]
