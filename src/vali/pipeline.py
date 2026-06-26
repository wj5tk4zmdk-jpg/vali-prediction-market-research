"""Compatibility facade for VALI research pipeline orchestration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .config import ValiConfig
from .io import InputBundle
from .research.pipeline import (
    PipelineResult,
    _build_signals as _research_build_signals,
    _daily_exclusions as _research_daily_exclusions,
    _manifest as _research_manifest,
    _sensitivity as _research_sensitivity,
    _sha256 as _research_sha256,
    execution_validation_summary as _research_execution_validation_summary,
    rebuild_report as _research_rebuild_report,
    run_backtest_pipeline as _research_run_backtest_pipeline,
    run_backtest_pipeline_from_manifest as _research_run_backtest_pipeline_from_manifest,
    run_signal_pipeline as _research_run_signal_pipeline,
    validate_inputs as _research_validate_inputs,
)


def validate_inputs(config: ValiConfig) -> InputBundle:
    return _research_validate_inputs(config)


def execution_validation_summary(signals: pd.DataFrame) -> dict[str, Any]:
    """Summarize whether every research cutoff has a known execution state."""
    return _research_execution_validation_summary(signals)


def _sha256(path: Path) -> str:
    return _research_sha256(path)


def _manifest(config: ValiConfig) -> dict[str, Any]:
    return _research_manifest(config)


def _build_signals(
    config: ValiConfig,
    bundle: InputBundle,
    velocity_window: int | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    return _research_build_signals(config, bundle, velocity_window)


def _daily_exclusions(signals: pd.DataFrame) -> pd.DataFrame:
    return _research_daily_exclusions(signals)


def run_signal_pipeline(
    config: ValiConfig,
    output_dir: str | Path | None = None,
) -> PipelineResult:
    return _research_run_signal_pipeline(config, output_dir)


def _sensitivity(config: ValiConfig, bundle: InputBundle) -> pd.DataFrame:
    return _research_sensitivity(config, bundle)


def run_backtest_pipeline(config: ValiConfig, output_dir: str | Path) -> PipelineResult:
    return _research_run_backtest_pipeline(config, output_dir)


def run_backtest_pipeline_from_manifest(
    manifest_path: str | Path,
    output_dir: str | Path,
) -> PipelineResult:
    return _research_run_backtest_pipeline_from_manifest(manifest_path, output_dir)


def rebuild_report(run_dir: str | Path) -> Path:
    return _research_rebuild_report(run_dir)


__all__ = [
    "PipelineResult",
    "execution_validation_summary",
    "rebuild_report",
    "run_backtest_pipeline",
    "run_backtest_pipeline_from_manifest",
    "run_signal_pipeline",
    "validate_inputs",
]
