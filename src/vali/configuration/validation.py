"""Validation rules for typed VALI configuration contracts."""

from __future__ import annotations

from datetime import date
from zoneinfo import ZoneInfo

from ..data.provenance import (
    validate_public_research_config as _validate_public_research_config,
)
from .contracts import (
    BacktestConfig,
    ConfigError,
    FeatureConfig,
    MarketConfig,
    RegimeConfig,
    SignalConfig,
    ValiConfig,
)


def validate_public_research_config(raw: dict) -> None:
    """Reject forbidden data and trading interfaces from research config."""
    _validate_public_research_config(raw, error_type=ConfigError)


def validate_market_config(config: MarketConfig) -> None:
    if not 0 < config.max_spread <= 1:
        raise ConfigError("market.max_spread must be in (0, 1]")
    if config.min_depth <= 0:
        raise ConfigError("market.min_depth must be positive")
    if config.max_quote_age_minutes <= 0 or config.fallback_trade_window_minutes <= 0:
        raise ConfigError("market age windows must be positive")
    if config.fee_bps < 0:
        raise ConfigError("market.fee_bps cannot be negative")
    if not 0 < config.probability_epsilon < 0.5:
        raise ConfigError("market.probability_epsilon must be in (0, 0.5)")


def validate_feature_config(config: FeatureConfig) -> None:
    try:
        ZoneInfo(config.timezone)
    except Exception as exc:
        raise ConfigError(f"Unknown timezone: {config.timezone}") from exc
    parts = config.daily_cutoff.split(":")
    if len(parts) != 2 or not (
        0 <= int(parts[0]) <= 23 and 0 <= int(parts[1]) <= 59
    ):
        raise ConfigError("features.daily_cutoff must be HH:MM")
    if config.standardization_window < config.min_periods or config.min_periods < 2:
        raise ConfigError("feature normalization window/min_periods are invalid")
    if config.optional_feature_policy not in {"reject", "dynamic_reweight"}:
        raise ConfigError(
            "features.optional_feature_policy must be reject or dynamic_reweight"
        )


def validate_signal_config(config: SignalConfig) -> None:
    if config.velocity_window < 2 or config.normalization_window < config.min_periods:
        raise ConfigError("signal windows are invalid")
    if config.entry_threshold <= config.exit_threshold or config.exit_threshold < 0:
        raise ConfigError("entry_threshold must exceed non-negative exit_threshold")
    if any(window < 2 for window in config.sensitivity_windows):
        raise ConfigError("all sensitivity windows must be at least two days")


def validate_regime_config(config: RegimeConfig) -> None:
    if config.window < config.min_periods or config.min_periods < 3:
        raise ConfigError("regime window/min_periods are invalid")
    if config.max_lag < 1 or not 0 <= config.min_abs_correlation <= 1:
        raise ConfigError("regime lag/correlation settings are invalid")
    if not 0 <= config.tie_margin <= 1:
        raise ConfigError("regime.tie_margin must be in [0, 1]")


def validate_backtest_config(config: BacktestConfig) -> None:
    if config.min_train_events < 2 or config.notional <= 0:
        raise ConfigError("backtest training count and notional must be positive")
    if not 0 < config.stop_loss_fraction < 1:
        raise ConfigError("backtest.stop_loss_fraction must be in (0, 1)")
    if config.max_holding_days < 1 or config.days_before_settlement < 0:
        raise ConfigError("backtest holding/settlement settings are invalid")
    if config.calibration_l2 < 0:
        raise ConfigError("backtest.calibration_l2 cannot be negative")


def validate_vali_config(config: ValiConfig) -> None:
    validate_public_research_config(
        {
            "data": {
                "events": str(config.data.events),
                "quotes": str(config.data.quotes),
                "features": str(config.data.features),
                "feature_manifest": str(config.data.feature_manifest),
                "trades": str(config.data.trades) if config.data.trades else None,
            }
        }
    )
    config.market.validate()
    config.features.validate()
    config.signal.validate()
    config.regime.validate()
    config.backtest.validate()
    if not config.parameter_freeze_date:
        raise ConfigError("run.parameter_freeze_date is required")
    try:
        date.fromisoformat(config.parameter_freeze_date)
    except ValueError as exc:
        raise ConfigError("run.parameter_freeze_date must be YYYY-MM-DD") from exc
