"""High-level VALI research pipeline orchestration."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from ..backtest import BacktestResult, run_backtest
from ..configuration.contracts import ValiConfig
from ..data.contracts import InputBundle
from ..decisions import generate_decisions
from ..features import build_attention_index
from ..io import load_inputs
from ..market import select_daily_market
from ..regimes import add_realized_regime, classify_regimes
from ..reporting import (
    WARNING,
    divergence_half_lives,
    forecast_metrics,
    regime_confusion,
    render_html_report,
    trade_metrics,
    write_dataframe,
)
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
    row_count = len(signals)
    if row_count == 0:
        return {
            "status": "unvalidated_incomplete_execution_snapshots",
            "snapshot_completeness": 0.0,
            "depth_observed_fraction": 0.0,
            "capacity_claims_enabled": False,
            "required_snapshot_rows": 0,
        }

    index = signals.index
    depth_observed = (
        signals["depth_observed"].fillna(False).astype(bool)
        if "depth_observed" in signals
        else pd.Series(False, index=index)
    )
    market_closed = (
        signals["market_closed"].fillna(False).astype(bool)
        if "market_closed" in signals
        else pd.Series(False, index=index)
    )
    numeric_complete = pd.Series(True, index=index)
    for column in ("bid", "ask", "bid_depth", "ask_depth", "spread"):
        if column not in signals:
            numeric_complete &= False
        else:
            numeric_complete &= np.isfinite(
                pd.to_numeric(signals[column], errors="coerce")
            )

    incomplete_reasons = {
        "no_quote",
        "stale_quote",
        "depth_unobserved",
        "non_executable_vwap",
    }
    rejection_reason = (
        signals["rejection_reason"].fillna("").astype(str)
        if "rejection_reason" in signals
        else pd.Series("", index=index)
    )
    price_quality_pass = (
        signals["price_quality_pass"].fillna(False).astype(bool)
        if "price_quality_pass" in signals
        else pd.Series(False, index=index)
    )
    execution_liquidity_pass = (
        signals["execution_liquidity_pass"].fillna(False).astype(bool)
        if "execution_liquidity_pass" in signals
        else pd.Series(False, index=index)
    )
    executable = (
        signals["executable"].fillna(False).astype(bool)
        if "executable" in signals
        else pd.Series(False, index=index)
    )
    open_snapshot_complete = (
        depth_observed
        & numeric_complete
        & price_quality_pass
        & execution_liquidity_pass
        & executable
        & ~rejection_reason.isin(incomplete_reasons)
    )
    snapshot_complete = market_closed | open_snapshot_complete
    all_complete = bool(snapshot_complete.all())
    return {
        "status": (
            "complete_executable_snapshots"
            if all_complete
            else "unvalidated_incomplete_execution_snapshots"
        ),
        "snapshot_completeness": float(snapshot_complete.mean()),
        "depth_observed_fraction": float(depth_observed.mean()),
        "capacity_claims_enabled": all_complete,
        "required_snapshot_rows": row_count,
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest(config: ValiConfig) -> dict[str, Any]:
    paths = {
        "events": config.data.events,
        "quotes": config.data.quotes,
        "features": config.data.features,
        "feature_manifest": config.data.feature_manifest,
    }
    if config.data.trades:
        paths["trades"] = config.data.trades
    return {
        "package_version": "0.3.0",
        "methodology_version": config.methodology_version,
        "parameter_freeze_date": config.parameter_freeze_date,
        "config_path": str(config.source_path) if config.source_path else None,
        "config_sha256": _sha256(config.source_path) if config.source_path else None,
        "input_sha256": {name: _sha256(path) for name, path in paths.items()},
        "research_warning": WARNING,
    }


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
        "fee_model": "provisional_bps",
        "fee_bps": config.market.fee_bps,
        "fee_assumption_provisional": True,
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
    directory = Path(run_dir).resolve()
    required = [
        "metrics",
        "forecasts",
        "trades",
        "sensitivity",
        "exclusions",
        "calibration",
        "regime_confusion",
    ]
    frames: dict[str, pd.DataFrame] = {}
    for name in required:
        path = directory / f"{name}.csv"
        if not path.exists():
            raise FileNotFoundError(f"Missing run output: {path}")
        try:
            frames[name] = pd.read_csv(path)
        except pd.errors.EmptyDataError:
            frames[name] = pd.DataFrame()
    manifest = json.loads(
        (directory / "run_manifest.json").read_text(encoding="utf-8")
    )
    report = directory / "report.html"
    render_html_report(
        report,
        metrics=frames["metrics"],
        forecasts=frames["forecasts"],
        trades=frames["trades"],
        sensitivity=frames["sensitivity"],
        exclusions=frames["exclusions"],
        calibration=frames["calibration"],
        regime_table=frames["regime_confusion"],
        run_manifest=manifest,
    )
    return report
