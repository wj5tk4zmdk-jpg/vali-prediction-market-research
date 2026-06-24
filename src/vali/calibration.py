"""Compatibility facade for deterministic research calibration."""

from __future__ import annotations

import numpy as np

from .research.calibration import (
    fit_logistic as _fit_logistic,
    predict_logistic as _predict_logistic,
    sigmoid as _sigmoid,
)


def sigmoid(values: np.ndarray) -> np.ndarray:
    return _sigmoid(values)


def fit_logistic(
    x: np.ndarray,
    y: np.ndarray,
    l2: float = 1.0,
    max_iter: int = 100,
    tolerance: float = 1e-9,
) -> np.ndarray:
    """Fit an intercept-bearing L2 logistic model with Newton updates."""
    return _fit_logistic(x, y, l2=l2, max_iter=max_iter, tolerance=tolerance)


def predict_logistic(coefficients: np.ndarray, x: np.ndarray) -> np.ndarray:
    return _predict_logistic(coefficients, x)
