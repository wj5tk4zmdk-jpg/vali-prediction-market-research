"""Compatibility facade for typed VALI configuration."""

from __future__ import annotations

from .configuration.contracts import (
    BacktestConfig,
    ConfigError,
    DataConfig,
    FeatureConfig,
    MarketConfig,
    RegimeConfig,
    SignalConfig,
    ValiConfig,
)
from .configuration.loading import required_setting
from .configuration.validation import (
    validate_public_research_config as _validate_public_research_config,
)
from .data.provenance import (
    canonical_boundary_value,
    forbidden_public_input_marker as _forbidden_public_input_marker,
)


def _canonical_boundary_value(value: object) -> str:
    return canonical_boundary_value(value)


def forbidden_public_input_marker(value: object) -> str | None:
    """Return the forbidden marker present in a config or provenance value."""
    return _forbidden_public_input_marker(value)


def validate_public_research_config(raw: dict) -> None:
    """Reject private-data and trading interfaces from core research config."""
    _validate_public_research_config(raw)


def _required(section: dict, key: str, section_name: str):
    return required_setting(section, key, section_name)


__all__ = [
    "BacktestConfig",
    "ConfigError",
    "DataConfig",
    "FeatureConfig",
    "MarketConfig",
    "RegimeConfig",
    "SignalConfig",
    "ValiConfig",
    "forbidden_public_input_marker",
    "validate_public_research_config",
]
