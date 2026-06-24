"""Pure behavioral-attention transformation and composition helpers."""

from __future__ import annotations

import numpy as np
import pandas as pd


def transform_feature(series: pd.Series, name: str) -> pd.Series:
    """Apply a frozen feature transformation without accessing external state."""
    if name == "level":
        return series.astype(float)
    if name == "diff":
        return series.astype(float).diff()
    if name == "pct_change":
        return series.astype(float).pct_change(fill_method=None)
    if name == "log_diff":
        safe = series.astype(float).where(series.astype(float) > 0)
        return np.log(safe).diff()
    if name == "log1p":
        values = series.astype(float)
        if (values.dropna() < 0).any():
            raise ValueError("log1p feature transformation requires non-negative values")
        return np.log1p(values)
    raise ValueError(f"Unsupported feature transformation: {name}")


def frozen_equal_weight(feature_count: int) -> float:
    """Return the fixed per-feature weight for an equal-weight composite."""
    if feature_count <= 0:
        raise ValueError("feature_count must be positive")
    return 1.0 / feature_count


def compose_attention(
    zframe: pd.DataFrame,
    required_features: list[str],
    optional_feature_policy: str,
) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series, np.ndarray]:
    """Compose A from polarity-aligned z-scores using the frozen policy."""
    required_complete = (
        zframe[required_features].notna().all(axis=1)
        if required_features
        else pd.Series(True, index=zframe.index)
    )
    optional = [column for column in zframe.columns if column not in required_features]
    optional_complete = (
        zframe[optional].notna().all(axis=1)
        if optional
        else pd.Series(True, index=zframe.index)
    )
    composition_complete = required_complete & optional_complete
    active_count = zframe.notna().sum(axis=1)
    if optional_feature_policy == "dynamic_reweight":
        signal_eligible = required_complete & active_count.gt(0)
    else:
        signal_eligible = composition_complete & active_count.eq(len(zframe.columns))
    attention = zframe.mean(axis=1, skipna=True).where(signal_eligible)
    rejection_reason = np.select(
        [
            ~required_complete,
            (optional_feature_policy == "reject") & ~optional_complete,
            ~active_count.gt(0),
        ],
        ["missing_required_feature", "missing_optional_feature", "no_active_features"],
        default="",
    )
    return (
        attention,
        active_count,
        required_complete,
        composition_complete,
        rejection_reason,
    )
