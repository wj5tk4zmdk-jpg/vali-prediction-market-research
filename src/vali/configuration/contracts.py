"""Typed configuration contracts for reproducible VALI research runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


class ConfigError(ValueError):
    """Raised when a configuration is incomplete or internally inconsistent."""


@dataclass(frozen=True)
class DataConfig:
    events: Path
    quotes: Path
    features: Path
    feature_manifest: Path
    trades: Path | None = None


@dataclass(frozen=True)
class MarketConfig:
    max_spread: float
    min_depth: float
    max_quote_age_minutes: int
    fallback_trade_window_minutes: int
    fee_bps: float
    probability_epsilon: float = 1e-4

    def validate(self) -> None:
        from .validation import validate_market_config

        validate_market_config(self)


@dataclass(frozen=True)
class FeatureConfig:
    timezone: str = "America/New_York"
    daily_cutoff: str = "16:00"
    standardization_window: int = 90
    min_periods: int = 30
    optional_feature_policy: str = "reject"

    def validate(self) -> None:
        from .validation import validate_feature_config

        validate_feature_config(self)


@dataclass(frozen=True)
class SignalConfig:
    velocity_window: int = 7
    normalization_window: int = 90
    min_periods: int = 30
    entry_threshold: float = 2.0
    exit_threshold: float = 0.5
    sensitivity_windows: tuple[int, ...] = (3, 14, 30)

    def validate(self) -> None:
        from .validation import validate_signal_config

        validate_signal_config(self)


@dataclass(frozen=True)
class RegimeConfig:
    window: int = 90
    min_periods: int = 30
    max_lag: int = 7
    min_abs_correlation: float = 0.20
    tie_margin: float = 0.05

    def validate(self) -> None:
        from .validation import validate_regime_config

        validate_regime_config(self)


@dataclass(frozen=True)
class BacktestConfig:
    min_train_events: int = 16
    notional: float = 100.0
    stop_loss_fraction: float = 0.25
    max_holding_days: int = 14
    days_before_settlement: int = 1
    calibration_l2: float = 1.0

    def validate(self) -> None:
        from .validation import validate_backtest_config

        validate_backtest_config(self)


@dataclass(frozen=True)
class ValiConfig:
    data: DataConfig
    market: MarketConfig
    features: FeatureConfig = field(default_factory=FeatureConfig)
    signal: SignalConfig = field(default_factory=SignalConfig)
    regime: RegimeConfig = field(default_factory=RegimeConfig)
    backtest: BacktestConfig = field(default_factory=BacktestConfig)
    parameter_freeze_date: str = ""
    methodology_version: str = "1.0.1"
    source_path: Path | None = None

    @classmethod
    def from_toml(cls, path: str | Path) -> "ValiConfig":
        from .loading import load_config

        return load_config(path, config_type=cls)

    def validate(self) -> None:
        from .validation import validate_vali_config

        validate_vali_config(self)
