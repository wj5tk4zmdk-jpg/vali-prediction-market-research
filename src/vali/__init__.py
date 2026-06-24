"""VALI research package public API."""

from .backtest import run_walk_forward, simulate_trades
from .config import ValiConfig
from .features import build_attention_index, rolling_prior_zscore
from .pipeline import run_backtest_pipeline, run_signal_pipeline, validate_inputs
from .regimes import classify_regimes
from .signals import compute_vali_signals, logit_clip, rolling_ols_slope
from .providers.kalshi import ArchiveStore, KalshiAdapter, KalshiClient
from .providers.google_trends import (
    FixtureTrendsGateway,
    TrendsAdapter,
    TrendsGateway,
    TrendsQuerySpec,
    TrendsRequest,
)

__all__ = [
    "ValiConfig",
    "ArchiveStore",
    "KalshiAdapter",
    "KalshiClient",
    "FixtureTrendsGateway",
    "TrendsAdapter",
    "TrendsGateway",
    "TrendsQuerySpec",
    "TrendsRequest",
    "build_attention_index",
    "classify_regimes",
    "compute_vali_signals",
    "logit_clip",
    "rolling_ols_slope",
    "rolling_prior_zscore",
    "run_backtest_pipeline",
    "run_signal_pipeline",
    "run_walk_forward",
    "simulate_trades",
    "validate_inputs",
]

__version__ = "0.3.0"
