"""VALI velocity and signed-divergence calculations."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import ValiConfig
from .domain.conviction import logit_clip as _logit_clip
from .domain.divergence import (
    divergence_magnitude,
    rolling_ols_slope as _rolling_ols_slope,
    rolling_prior_zscore,
    signed_divergence,
)


def logit_clip(values: pd.Series | np.ndarray, epsilon: float = 1e-4):
    return _logit_clip(values, epsilon)


def rolling_ols_slope(series: pd.Series, window: int) -> pd.Series:
    """OLS slope over an exact observation window; missing values invalidate it."""
    return _rolling_ols_slope(series, window)


def compute_vali_signals(
    daily_market: pd.DataFrame,
    attention: pd.DataFrame,
    config: ValiConfig,
    velocity_window: int | None = None,
) -> pd.DataFrame:
    """Combine A and P into leak-free VALI S/M observations."""
    window = velocity_window or config.signal.velocity_window
    merged = daily_market.merge(attention, on="cutoff_at", how="left", validate="many_to_one")
    outputs: list[pd.DataFrame] = []
    for _, group in merged.groupby("contract_id", sort=False):
        frame = group.sort_values("cutoff_at").copy()
        frame["logit_price"] = logit_clip(frame["price"], config.market.probability_epsilon)
        frame["attention_velocity"] = rolling_ols_slope(frame["attention"], window)
        frame["price_velocity"] = rolling_ols_slope(frame["logit_price"], window)
        frame["z_attention_velocity"] = rolling_prior_zscore(
            frame["attention_velocity"],
            config.signal.normalization_window,
            config.signal.min_periods,
        )
        frame["z_price_velocity"] = rolling_prior_zscore(
            frame["price_velocity"],
            config.signal.normalization_window,
            config.signal.min_periods,
        )
        frame["signed_divergence"] = signed_divergence(
            frame["z_attention_velocity"], frame["z_price_velocity"]
        )
        frame["divergence_magnitude"] = divergence_magnitude(
            frame["signed_divergence"]
        )
        frame["velocity_window"] = window
        outputs.append(frame)
    if not outputs:
        return merged.assign(
            logit_price=np.nan,
            attention_velocity=np.nan,
            price_velocity=np.nan,
            z_attention_velocity=np.nan,
            z_price_velocity=np.nan,
            signed_divergence=np.nan,
            divergence_magnitude=np.nan,
            velocity_window=window,
        )
    return pd.concat(outputs, ignore_index=True).sort_values(
        ["contract_id", "cutoff_at"]
    ).reset_index(drop=True)
