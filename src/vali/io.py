"""Compatibility I/O facade over the versioned VALI data boundary."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd

from .config import ValiConfig
from .data.contracts import (
    EVENT_COLUMNS,
    FEATURE_COLUMNS,
    MANIFEST_COLUMNS,
    QUOTE_COLUMNS,
    TRADE_COLUMNS,
    DataValidationError,
    InputBundle,
    ValidationSummary,
)
from .data.point_in_time import parse_utc
from .data.provenance import validate_public_input_boundary as _validate_public_boundary
from .data.validation import (
    parse_manifest_bool,
    reject_duplicates,
    require_columns,
    validate_event_identity as _validate_event_identity,
    validate_frames as _validate_frames,
)


def read_table(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        raise DataValidationError(f"Input file does not exist: {path}")
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in {".parquet", ".pq"}:
        try:
            return pd.read_parquet(path)
        except ImportError as exc:
            raise DataValidationError(
                f"Reading {path.name} requires the declared pyarrow dependency"
            ) from exc
    raise DataValidationError(f"Unsupported input format for {path}; use CSV or Parquet")


def _require_columns(frame: pd.DataFrame, required: set[str], label: str) -> None:
    require_columns(frame, required, label)


def _parse_utc(frame: pd.DataFrame, columns: Iterable[str], label: str) -> None:
    parse_utc(frame, columns, label)


def _reject_duplicates(frame: pd.DataFrame, keys: list[str], label: str) -> None:
    reject_duplicates(frame, keys, label)


def _parse_bool(value) -> bool:
    return parse_manifest_bool(value)


def validate_public_input_boundary(**frames: pd.DataFrame | None) -> None:
    """Compatibility wrapper for the public-input boundary."""
    _validate_public_boundary(**frames)


def validate_event_identity(
    events: pd.DataFrame, related: pd.DataFrame | None = None
) -> None:
    """Compatibility wrapper for internal EASING identity validation."""
    _validate_event_identity(events, related)


def validate_frames(
    events: pd.DataFrame,
    quotes: pd.DataFrame,
    features: pd.DataFrame,
    manifest: pd.DataFrame,
    trades: pd.DataFrame | None = None,
) -> InputBundle:
    """Compatibility wrapper for versioned frame validation."""
    return _validate_frames(events, quotes, features, manifest, trades)


def load_inputs(config: ValiConfig) -> InputBundle:
    return validate_frames(
        read_table(config.data.events),
        read_table(config.data.quotes),
        read_table(config.data.features),
        read_table(config.data.feature_manifest),
        read_table(config.data.trades) if config.data.trades else None,
    )
