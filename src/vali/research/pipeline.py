"""High-level VALI research pipeline orchestration."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ..artifacts.manifests import build_run_manifest, sha256_file
from ..artifacts.metrics import (
    divergence_half_lives,
    forecast_metrics,
    regime_confusion,
    trade_metrics,
)
from ..artifacts.reports import rebuild_report as _artifact_rebuild_report
from ..artifacts.reports import render_html_report
from ..artifacts.serialization import write_dataframe
from ..backtest import BacktestResult, run_backtest
from ..configuration.contracts import ValiConfig
from ..data.contracts import InputBundle
from ..decisions import generate_decisions
from ..execution.fees import provisional_fee_metadata
from ..execution.snapshots import (
    execution_validation_summary as _execution_validation_summary,
)
from ..features import build_attention_index
from ..io import load_inputs
from ..market import select_daily_market
from ..regimes import add_realized_regime, classify_regimes
from ..signals import compute_vali_signals
from .sensitivity import run_sensitivity


@dataclass
class PipelineResult:
    signals: pd.DataFrame
    output_dir: Path | None = None
    forecasts: pd.DataFrame | None = None
    trades: pd.DataFrame | None = None
    exclusions: pd.DataFrame | None = None
    metrics: pd.DataFrame | None = None
    sensitivity: pd.DataFrame | None = None


def validate_inputs(config: ValiConfig) -> InputBundle:
    return load_inputs(config)


def execution_validation_summary(signals: pd.DataFrame) -> dict[str, Any]:
    """Summarize whether every research cutoff has a known execution state."""
    return _execution_validation_summary(signals)


def _sha256(path: Path) -> str:
    return sha256_file(path)


def _manifest(config: ValiConfig) -> dict[str, Any]:
    return build_run_manifest(config)


def _build_signals(
    config: ValiConfig,
    bundle: InputBundle,
    velocity_window: int | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    market = select_daily_market(bundle.events, bundle.quotes, bundle.trades, config)
    attention, feature_audit = build_attention_index(
        bundle.features, bundle.manifest, market["cutoff_at"], config.features
    )
    signals = compute_vali_signals(
        market, attention, config, velocity_window=velocity_window
    )
    signals = classify_regimes(signals, config.regime)
    signals = add_realized_regime(signals, config.regime)
    signals = generate_decisions(signals, config)
    return signals, feature_audit


def _daily_exclusions(signals: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    for row in signals.itertuples(index=False):
        common = {
            "event_id": row.event_id,
            "contract_id": row.contract_id,
            "cutoff_at": row.cutoff_at,
        }
        if row.rejection_reason:
            rows.append(
                {**common, "stage": "market", "reason": row.rejection_reason}
            )
        if row.attention_rejection_reason:
            rows.append(
                {
                    **common,
                    "stage": "attention",
                    "reason": row.attention_rejection_reason,
                }
            )
        if row.action == "none":
            rows.append(
                {**common, "stage": "decision", "reason": row.decision_reason}
            )
    return pd.DataFrame(rows)


def run_signal_pipeline(
    config: ValiConfig,
    output_dir: str | Path | None = None,
) -> PipelineResult:
    bundle = load_inputs(config)
    signals, feature_audit = _build_signals(config, bundle)
    exclusions = _daily_exclusions(signals)
    target = Path(output_dir).resolve() if output_dir else None
    if target:
        target.mkdir(parents=True, exist_ok=True)
        write_dataframe(signals, "signals", target)
        write_dataframe(feature_audit, "feature_audit", target)
        write_dataframe(exclusions, "exclusions", target)
        manifest = _manifest(config)
        manifest["validation"] = bundle.validation.as_dict()
        (target / "run_manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
        )
    return PipelineResult(signals=signals, exclusions=exclusions, output_dir=target)


def _sensitivity(config: ValiConfig, bundle: InputBundle) -> pd.DataFrame:
    return run_sensitivity(
        config,
        bundle,
        _build_signals,
        execution_validation_summary,
    )


def run_backtest_pipeline(config: ValiConfig, output_dir: str | Path) -> PipelineResult:
    target = Path(output_dir).resolve()
    target.mkdir(parents=True, exist_ok=True)
    bundle = load_inputs(config)
    signals, feature_audit = _build_signals(config, bundle)
    backtest: BacktestResult = run_backtest(signals, bundle.events, config)
    daily_exclusions = _daily_exclusions(signals)
    exclusions = pd.concat(
        [daily_exclusions, backtest.exclusions], ignore_index=True, sort=False
    )
    forecast_metric_table, calibration = forecast_metrics(backtest.forecasts)
    execution_summary = execution_validation_summary(signals)
    execution_validated = execution_summary["capacity_claims_enabled"]
    execution_metric_table = trade_metrics(
        backtest.trades, execution_validated=execution_validated
    ).assign(model="execution")
    metrics = pd.concat(
        [forecast_metric_table, execution_metric_table],
        ignore_index=True,
        sort=False,
    )
    metrics = pd.concat(
        [
            metrics,
            pd.DataFrame(
                [
                    {
                        "model": "pipeline",
                        "metric": "no_trade_rate",
                        "value": float((signals["action"] == "none").mean()),
                        "observations": len(signals),
                    },
                    {
                        "model": "pipeline",
                        "metric": "median_divergence_half_life",
                        "value": np.nan,
                        "observations": 0,
                    },
                ]
            ),
        ],
        ignore_index=True,
    )
    half_lives = divergence_half_lives(
        signals, config.signal.entry_threshold, config.signal.exit_threshold
    )
    resolved_half_lives = (
        half_lives.loc[
            half_lives.get("resolved", pd.Series(dtype=bool)) == True,
            "half_life_days",
        ]
        if not half_lives.empty
        else pd.Series(dtype=float)
    )
    if len(resolved_half_lives):
        index = metrics.index[metrics["metric"] == "median_divergence_half_life"]
        metrics.loc[index, "value"] = float(resolved_half_lives.median())
        metrics.loc[index, "observations"] = len(resolved_half_lives)
    regime_table = regime_confusion(signals)
    if not regime_table.empty:
        regime_total = int(regime_table["count"].sum())
        regime_correct = int(
            regime_table.loc[
                regime_table["realized_regime"]
                == regime_table["predicted_regime"],
                "count",
            ].sum()
        )
        metrics = pd.concat(
            [
                metrics,
                pd.DataFrame(
                    [
                        {
                            "model": "regime_classifier",
                            "metric": "diagnostic_accuracy",
                            "value": (
                                regime_correct / regime_total
                                if regime_total
                                else np.nan
                            ),
                            "observations": regime_total,
                        }
                    ]
                ),
            ],
            ignore_index=True,
        )
    sensitivity = _sensitivity(config, bundle)
    manifest = _manifest(config)
    manifest["validation"] = bundle.validation.as_dict()
    manifest["execution_validation"] = {
        **execution_summary,
        **provisional_fee_metadata(config.market.fee_bps),
    }

    outputs = {
        "signals": signals,
        "feature_audit": feature_audit,
        "forecasts": backtest.forecasts,
        "calibration": calibration,
        "trades": backtest.trades,
        "metrics": metrics,
        "sensitivity": sensitivity,
        "exclusions": exclusions,
        "divergence_half_lives": half_lives,
        "regime_confusion": regime_table,
    }
    manifest["outputs"] = {
        name: write_dataframe(frame, name, target) for name, frame in outputs.items()
    }
    (target / "run_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )
    render_html_report(
        target / "report.html",
        metrics,
        backtest.forecasts,
        backtest.trades,
        sensitivity,
        exclusions,
        calibration,
        regime_table,
        manifest,
    )
    return PipelineResult(
        signals=signals,
        output_dir=target,
        forecasts=backtest.forecasts,
        trades=backtest.trades,
        exclusions=exclusions,
        metrics=metrics,
        sensitivity=sensitivity,
    )


def rebuild_report(run_dir: str | Path) -> Path:
    return _artifact_rebuild_report(run_dir)
