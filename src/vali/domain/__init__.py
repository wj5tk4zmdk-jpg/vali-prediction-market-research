"""Pure deterministic VALI domain mathematics."""

from .attention import compose_attention, frozen_equal_weight, transform_feature
from .conviction import logit_clip
from .divergence import (
    divergence_magnitude,
    rolling_ols_slope,
    rolling_prior_zscore,
    signed_divergence,
)
from .regimes import REGIMES, classify_correlation_vector, lagged_correlations

__all__ = [
    "REGIMES",
    "classify_correlation_vector",
    "compose_attention",
    "divergence_magnitude",
    "frozen_equal_weight",
    "lagged_correlations",
    "logit_clip",
    "rolling_ols_slope",
    "rolling_prior_zscore",
    "signed_divergence",
    "transform_feature",
]
