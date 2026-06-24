"""Rolling lead-lag regime classification."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import RegimeConfig
from .domain.regimes import (
    REGIMES,
    classify_correlation_vector as _classify_correlation_vector,
    lagged_correlations as _lagged_correlations,
)


def lagged_correlations(
    attention_velocity: np.ndarray,
    price_velocity: np.ndarray,
    max_lag: int,
    min_periods: int,
) -> dict[int, float]:
    """Positive lag means earlier attention is compared with later price."""
    return _lagged_correlations(
        attention_velocity, price_velocity, max_lag, min_periods
    )


def classify_correlation_vector(
    correlations: dict[int, float],
    min_abs_correlation: float,
    tie_margin: float,
) -> tuple[str, float, float]:
    return _classify_correlation_vector(
        correlations, min_abs_correlation, tie_margin
    )


def classify_regimes(signals: pd.DataFrame, config: RegimeConfig) -> pd.DataFrame:
    outputs: list[pd.DataFrame] = []
    for _, group in signals.groupby("contract_id", sort=False):
        frame = group.sort_values("cutoff_at").copy().reset_index(drop=True)
        regimes: list[str] = []
        best_lags: list[float] = []
        best_corrs: list[float] = []
        for index in range(len(frame)):
            start = max(0, index - config.window + 1)
            history = frame.iloc[start : index + 1]
            correlations = lagged_correlations(
                history["z_attention_velocity"].to_numpy(),
                history["z_price_velocity"].to_numpy(),
                config.max_lag,
                config.min_periods,
            )
            regime, lag, corr = classify_correlation_vector(
                correlations, config.min_abs_correlation, config.tie_margin
            )
            if not bool(frame.loc[index, "liquidity_pass"]):
                regime = "unstable"
            regimes.append(regime)
            best_lags.append(lag)
            best_corrs.append(corr)
        frame["regime"] = regimes
        frame["regime_best_lag"] = best_lags
        frame["regime_correlation"] = best_corrs
        outputs.append(frame)
    if not outputs:
        return signals.assign(
            regime=pd.Series(dtype=str),
            regime_best_lag=pd.Series(dtype=float),
            regime_correlation=pd.Series(dtype=float),
        )
    return pd.concat(outputs, ignore_index=True).sort_values(
        ["contract_id", "cutoff_at"]
    ).reset_index(drop=True)


def add_realized_regime(signals: pd.DataFrame, config: RegimeConfig) -> pd.DataFrame:
    """Attach a full-contract diagnostic label used only after simulation."""
    frames: list[pd.DataFrame] = []
    for _, group in signals.groupby("contract_id", sort=False):
        frame = group.copy()
        correlations = lagged_correlations(
            frame["z_attention_velocity"].to_numpy(),
            frame["z_price_velocity"].to_numpy(),
            config.max_lag,
            config.min_periods,
        )
        realized, _, _ = classify_correlation_vector(
            correlations, config.min_abs_correlation, config.tie_margin
        )
        frame["realized_regime"] = realized
        frames.append(frame)
    return pd.concat(frames, ignore_index=True) if frames else signals.assign(realized_regime="")
