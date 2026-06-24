"""Pure lead-lag regime classification mathematics."""

from __future__ import annotations

import numpy as np


REGIMES = ("attention_leading", "market_leading", "coupled", "unstable")


def lagged_correlations(
    attention_velocity: np.ndarray,
    price_velocity: np.ndarray,
    max_lag: int,
    min_periods: int,
) -> dict[int, float]:
    """Positive lag means earlier attention is compared with later price."""
    correlations: dict[int, float] = {}
    a = np.asarray(attention_velocity, dtype=float)
    p = np.asarray(price_velocity, dtype=float)
    for lag in range(-max_lag, max_lag + 1):
        if lag > 0:
            left, right = a[:-lag], p[lag:]
        elif lag < 0:
            k = -lag
            left, right = a[k:], p[:-k]
        else:
            left, right = a, p
        valid = np.isfinite(left) & np.isfinite(right)
        if int(valid.sum()) < min_periods:
            correlations[lag] = np.nan
            continue
        lvalid, rvalid = left[valid], right[valid]
        if np.std(lvalid) == 0 or np.std(rvalid) == 0:
            correlations[lag] = np.nan
        else:
            correlations[lag] = float(np.corrcoef(lvalid, rvalid)[0, 1])
    return correlations


def classify_correlation_vector(
    correlations: dict[int, float],
    min_abs_correlation: float,
    tie_margin: float,
) -> tuple[str, float, float]:
    """Classify the strongest valid correlation using VALI lag conventions."""
    candidates = [(lag, corr) for lag, corr in correlations.items() if np.isfinite(corr)]
    if not candidates:
        return "unstable", np.nan, np.nan
    ranked = sorted(candidates, key=lambda pair: abs(pair[1]), reverse=True)
    best_lag, best_corr = ranked[0]
    if abs(best_corr) < min_abs_correlation:
        return "unstable", float(best_lag), float(best_corr)
    if len(ranked) > 1:
        second_lag, second_corr = ranked[1]
        conflicting = np.sign(second_lag) != np.sign(best_lag)
        if conflicting and abs(abs(best_corr) - abs(second_corr)) <= tie_margin:
            return "unstable", float(best_lag), float(best_corr)
    if best_lag > 0:
        regime = "attention_leading"
    elif best_lag < 0:
        regime = "market_leading"
    else:
        regime = "coupled"
    return regime, float(best_lag), float(best_corr)
