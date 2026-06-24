"""Typed VALI configuration contracts, TOML loading, and validation."""

from .contracts import (
    BacktestConfig,
    ConfigError,
    DataConfig,
    FeatureConfig,
    MarketConfig,
    RegimeConfig,
    SignalConfig,
    ValiConfig,
)
from .loading import load_config, load_toml, required_setting, resolve_config_path
from .validation import (
    validate_backtest_config,
    validate_feature_config,
    validate_market_config,
    validate_public_research_config,
    validate_regime_config,
    validate_signal_config,
    validate_vali_config,
)

__all__ = [
    "BacktestConfig",
    "ConfigError",
    "DataConfig",
    "FeatureConfig",
    "MarketConfig",
    "RegimeConfig",
    "SignalConfig",
    "ValiConfig",
    "load_config",
    "load_toml",
    "required_setting",
    "resolve_config_path",
    "validate_backtest_config",
    "validate_feature_config",
    "validate_market_config",
    "validate_public_research_config",
    "validate_regime_config",
    "validate_signal_config",
    "validate_vali_config",
]
