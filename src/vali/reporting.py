"""Compatibility facade for research artifacts and reporting."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .artifacts.metrics import (
    _log_loss as _artifact_log_loss,
    divergence_half_lives as _artifact_divergence_half_lives,
    forecast_metrics as _artifact_forecast_metrics,
    regime_confusion as _artifact_regime_confusion,
    trade_metrics as _artifact_trade_metrics,
)
from .artifacts.reports import (
    WARNING,
    _table as _artifact_table,
    render_html_report as _artifact_render_html_report,
)
from .artifacts.serialization import write_dataframe as _artifact_write_dataframe


def _log_loss(y: pd.Series, p: pd.Series) -> float:
    return _artifact_log_loss(y, p)


def forecast_metrics(forecasts: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    return _artifact_forecast_metrics(forecasts)


def trade_metrics(trades: pd.DataFrame, execution_validated: bool = True) -> pd.DataFrame:
    return _artifact_trade_metrics(trades, execution_validated)


def divergence_half_lives(signals: pd.DataFrame, entry_threshold: float, exit_threshold: float) -> pd.DataFrame:
    return _artifact_divergence_half_lives(signals, entry_threshold, exit_threshold)


def regime_confusion(signals: pd.DataFrame) -> pd.DataFrame:
    return _artifact_regime_confusion(signals)


def write_dataframe(frame: pd.DataFrame, name: str, output_dir: Path) -> dict:
    return _artifact_write_dataframe(frame, name, output_dir)


def _table(frame: pd.DataFrame, empty_message: str = "No observations") -> str:
    return _artifact_table(frame, empty_message)


def render_html_report(
    output_path: Path,
    metrics: pd.DataFrame,
    forecasts: pd.DataFrame,
    trades: pd.DataFrame,
    sensitivity: pd.DataFrame,
    exclusions: pd.DataFrame,
    calibration: pd.DataFrame,
    regime_table: pd.DataFrame,
    run_manifest: dict,
) -> None:
    return _artifact_render_html_report(
        output_path,
        metrics,
        forecasts,
        trades,
        sensitivity,
        exclusions,
        calibration,
        regime_table,
        run_manifest,
    )


__all__ = [
    "WARNING",
    "divergence_half_lives",
    "forecast_metrics",
    "regime_confusion",
    "render_html_report",
    "trade_metrics",
    "write_dataframe",
]
