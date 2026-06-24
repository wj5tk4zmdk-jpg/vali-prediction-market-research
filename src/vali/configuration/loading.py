"""TOML loading and path resolution for the existing VALI config format."""

from __future__ import annotations

from pathlib import Path
import tomllib
from typing import TypeVar

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
from .validation import validate_public_research_config


ConfigType = TypeVar("ConfigType", bound=ValiConfig)


def required_setting(section: dict, key: str, section_name: str):
    if key not in section:
        raise ConfigError(f"Missing required setting [{section_name}].{key}")
    return section[key]


def resolve_config_path(value: str | None, base: Path) -> Path | None:
    if not value:
        return None
    candidate = Path(value)
    return candidate if candidate.is_absolute() else (base / candidate).resolve()


def load_toml(path: str | Path) -> tuple[Path, dict]:
    source = Path(path).resolve()
    with source.open("rb") as handle:
        raw = tomllib.load(handle)
    return source, raw


def load_config(
    path: str | Path,
    config_type: type[ConfigType] = ValiConfig,
) -> ConfigType:
    """Load the unchanged VALI TOML schema into typed configuration objects."""
    source, raw = load_toml(path)
    validate_public_research_config(raw)
    base = source.parent
    data_raw = raw.get("data", {})
    market_raw = raw.get("market", {})

    data = DataConfig(
        events=resolve_config_path(
            required_setting(data_raw, "events", "data"), base
        ),
        quotes=resolve_config_path(
            required_setting(data_raw, "quotes", "data"), base
        ),
        features=resolve_config_path(
            required_setting(data_raw, "features", "data"), base
        ),
        feature_manifest=resolve_config_path(
            required_setting(data_raw, "feature_manifest", "data"), base
        ),
        trades=resolve_config_path(data_raw.get("trades"), base),
    )
    market = MarketConfig(
        max_spread=float(required_setting(market_raw, "max_spread", "market")),
        min_depth=float(required_setting(market_raw, "min_depth", "market")),
        max_quote_age_minutes=int(
            required_setting(market_raw, "max_quote_age_minutes", "market")
        ),
        fallback_trade_window_minutes=int(
            required_setting(
                market_raw, "fallback_trade_window_minutes", "market"
            )
        ),
        fee_bps=float(required_setting(market_raw, "fee_bps", "market")),
        probability_epsilon=float(market_raw.get("probability_epsilon", 1e-4)),
    )
    features = FeatureConfig(**raw.get("features", {}))
    signal_raw = dict(raw.get("signal", {}))
    if "sensitivity_windows" in signal_raw:
        signal_raw["sensitivity_windows"] = tuple(signal_raw["sensitivity_windows"])
    signal = SignalConfig(**signal_raw)
    regime = RegimeConfig(**raw.get("regime", {}))
    backtest = BacktestConfig(**raw.get("backtest", {}))
    meta = raw.get("run", {})
    config = config_type(
        data=data,
        market=market,
        features=features,
        signal=signal,
        regime=regime,
        backtest=backtest,
        parameter_freeze_date=str(
            required_setting(meta, "parameter_freeze_date", "run")
        ),
        methodology_version=str(meta.get("methodology_version", "1.0.1")),
        source_path=source,
    )
    config.validate()
    return config
