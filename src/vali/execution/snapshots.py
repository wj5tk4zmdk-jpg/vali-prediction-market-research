"""Executable snapshot completeness and public quote transformations."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def entry_quote(entry: Any, side: str) -> tuple[float, float]:
    if side == "long_yes":
        return float(entry["ask"]), float(entry["ask_depth"])
    return 1.0 - float(entry["bid"]), float(entry["bid_depth"])


def liquidation_value(
    row: pd.Series, side: str, units: float
) -> tuple[float, float]:
    if side == "long_yes":
        probability = float(row["bid"])
    else:
        probability = 1.0 - float(row["ask"])
    return units * probability, probability


def exit_is_executable(row: pd.Series) -> bool:
    market_closed = bool(row.get("market_closed", False))
    return (
        bool(row["executable"])
        and bool(row.get("execution_liquidity_pass", True))
        and not market_closed
        and pd.notna(row["bid"])
        and pd.notna(row["ask"])
    )


def execution_validation_summary(signals: pd.DataFrame) -> dict[str, Any]:
    """Summarize whether every research cutoff has a known execution state."""
    row_count = len(signals)
    if row_count == 0:
        return {
            "status": "unvalidated_incomplete_execution_snapshots",
            "snapshot_completeness": 0.0,
            "depth_observed_fraction": 0.0,
            "capacity_claims_enabled": False,
            "required_snapshot_rows": 0,
        }

    index = signals.index
    depth_observed = (
        signals["depth_observed"].fillna(False).astype(bool)
        if "depth_observed" in signals
        else pd.Series(False, index=index)
    )
    market_closed = (
        signals["market_closed"].fillna(False).astype(bool)
        if "market_closed" in signals
        else pd.Series(False, index=index)
    )
    numeric_complete = pd.Series(True, index=index)
    for column in ("bid", "ask", "bid_depth", "ask_depth", "spread"):
        if column not in signals:
            numeric_complete &= False
        else:
            numeric_complete &= np.isfinite(
                pd.to_numeric(signals[column], errors="coerce")
            )

    incomplete_reasons = {
        "no_quote",
        "stale_quote",
        "depth_unobserved",
        "non_executable_vwap",
    }
    rejection_reason = (
        signals["rejection_reason"].fillna("").astype(str)
        if "rejection_reason" in signals
        else pd.Series("", index=index)
    )
    price_quality_pass = (
        signals["price_quality_pass"].fillna(False).astype(bool)
        if "price_quality_pass" in signals
        else pd.Series(False, index=index)
    )
    execution_liquidity_pass = (
        signals["execution_liquidity_pass"].fillna(False).astype(bool)
        if "execution_liquidity_pass" in signals
        else pd.Series(False, index=index)
    )
    executable = (
        signals["executable"].fillna(False).astype(bool)
        if "executable" in signals
        else pd.Series(False, index=index)
    )
    open_snapshot_complete = (
        depth_observed
        & numeric_complete
        & price_quality_pass
        & execution_liquidity_pass
        & executable
        & ~rejection_reason.isin(incomplete_reasons)
    )
    snapshot_complete = market_closed | open_snapshot_complete
    all_complete = bool(snapshot_complete.all())
    return {
        "status": (
            "complete_executable_snapshots"
            if all_complete
            else "unvalidated_incomplete_execution_snapshots"
        ),
        "snapshot_completeness": float(snapshot_complete.mean()),
        "depth_observed_fraction": float(depth_observed.mean()),
        "capacity_claims_enabled": all_complete,
        "required_snapshot_rows": row_count,
    }


__all__ = [
    "entry_quote",
    "execution_validation_summary",
    "exit_is_executable",
    "liquidation_value",
]
