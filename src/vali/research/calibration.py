"""Deterministic research calibration without external ML dependencies."""

from __future__ import annotations

import numpy as np


def sigmoid(values: np.ndarray) -> np.ndarray:
    values = np.clip(values, -35, 35)
    return 1.0 / (1.0 + np.exp(-values))


def fit_logistic(
    x: np.ndarray,
    y: np.ndarray,
    l2: float = 1.0,
    max_iter: int = 100,
    tolerance: float = 1e-9,
) -> np.ndarray:
    """Fit an intercept-bearing L2 logistic model with Newton updates."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if x.ndim != 2 or len(x) != len(y):
        raise ValueError("x must be 2D and aligned with y")
    design = np.column_stack([np.ones(len(x)), x])
    if len(np.unique(y)) < 2:
        probability = float(
            np.clip((y.sum() + 0.5) / (len(y) + 1), 1e-6, 1 - 1e-6)
        )
        coefficients = np.zeros(design.shape[1])
        coefficients[0] = np.log(probability / (1 - probability))
        return coefficients
    coefficients = np.zeros(design.shape[1])
    penalty = np.diag([0.0] + [l2] * x.shape[1])
    for _ in range(max_iter):
        probability = sigmoid(design @ coefficients)
        weights = np.clip(probability * (1 - probability), 1e-8, None)
        gradient = design.T @ (probability - y) + penalty @ coefficients
        hessian = design.T @ (design * weights[:, None]) + penalty
        try:
            step = np.linalg.solve(hessian, gradient)
        except np.linalg.LinAlgError:
            step = np.linalg.pinv(hessian) @ gradient
        coefficients -= step
        if np.max(np.abs(step)) < tolerance:
            break
    return coefficients


def predict_logistic(coefficients: np.ndarray, x: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    design = np.column_stack([np.ones(len(x)), x])
    return sigmoid(design @ coefficients)
