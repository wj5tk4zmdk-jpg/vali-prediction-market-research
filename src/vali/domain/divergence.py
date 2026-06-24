"""Pure velocity, normalization, and divergence mathematics."""

from __future__ import annotations

import numpy as np
import pandas as pd


def rolling_prior_zscore(series: pd.Series, window: int, min_periods: int) -> pd.Series:
    """Standardize against prior observations only; exclude the current value."""
    prior = series.shift(1)
    mean = prior.rolling(window=window, min_periods=min_periods).mean()
    std = prior.rolling(window=window, min_periods=min_periods).std(ddof=0)
    return (series - mean) / std.replace(0, np.nan)


def rolling_ols_slope(series: pd.Series, window: int) -> pd.Series:
    """Calculate OLS slope over an exact window; missing values invalidate it."""
    x = np.arange(window, dtype=float)
    centered_x = x - x.mean()
    denominator = float(np.dot(centered_x, centered_x))

    def slope(values: np.ndarray) -> float:
        if len(values) != window or not np.isfinite(values).all():
            return np.nan
        centered_y = values - values.mean()
        return float(np.dot(centered_x, centered_y) / denominator)

    return series.rolling(window=window, min_periods=window).apply(slope, raw=True)


def signed_divergence(
    standardized_attention_velocity: pd.Series,
    standardized_price_velocity: pd.Series,
) -> pd.Series:
    """Return signed VALI divergence S_t = z(gA_t) - z(gP_t)."""
    return standardized_attention_velocity - standardized_price_velocity


def divergence_magnitude(divergence: pd.Series) -> pd.Series:
    """Return M_t = abs(S_t)."""
    return divergence.abs()
