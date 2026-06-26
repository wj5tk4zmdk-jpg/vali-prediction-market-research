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
from ..knowledge_graph.evidence import REQUIRED_CLAIM_BOUNDARIES, append_evidence
from ..knowledge_graph.handoff import KnowledgeGraphError, compute_graph_hash
from ..knowledge_graph.runtime import (
    CompiledManifestRuntime,
    load_compiled_manifest_runtime,
    load_inputs_from_compiled_manifest,
)
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


def regime_confirmation_metrics(
    signals: pd.DataFrame,
    trades: pd.DataFrame,
    config: ValiConfig,
) -> pd.DataFrame:
    """Report configured regime-confirmation execution sensitivity settings."""
    decision_reasons = (
        signals["decision_reason"]
        if "decision_reason" in signals
        else pd.Series(dtype=object)
    )
    entries_suppressed = int(
        (decision_reasons == "entry_regime_unconfirmed").sum()
    )
    exit_delays = (
        trades.loc[
            (trades.get("exit_reason", pd.Series(dtype=object)) == "regime_change")
            & (
                trades.get("exit_confirmation_delay_days", pd.Series(dtype=float))
                > 0
            ),
            "exit_confirmation_delay_days",
        ]
        if not trades.empty
        and {"exit_reason", "exit_confirmation_delay_days"}.issubset(trades.columns)
        else pd.Series(dtype=float)
    )
    return pd.DataFrame(
        [
            {
                "model": "pipeline",
                "metric": "entry_regime_confirmation_periods",
                "value": config.backtest.entry_regime_confirmation_periods,
                "observations": len(signals),
            },
            {
                "model": "pipeline",
                "metric": "exit_regime_confirmation_periods",
                "value": config.backtest.exit_regime_confirmation_periods,
                "observations": len(trades),
            },
            {
                "model": "pipeline",
                "metric": "entries_suppressed_by_regime_confirmation",
                "value": entries_suppressed,
                "observations": len(signals),
            },
            {
                "model": "pipeline",
                "metric": "exits_delayed_by_regime_confirmation",
                "value": len(exit_delays),
                "observations": len(trades),
            },
            {
                "model": "pipeline",
                "metric": "mean_exit_confirmation_delay_days",
                "value": (
                    float(exit_delays.mean()) if len(exit_delays) else np.nan
                ),
                "observations": len(exit_delays),
            },
        ]
    )


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


def _manifest_metric_payload(metrics: pd.DataFrame) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for row in metrics.itertuples(index=False):
        key = f"{getattr(row, 'model', 'metric')}.{getattr(row, 'metric')}"
        value = getattr(row, "value")
        payload[key] = None if pd.isna(value) else float(value)
    return payload


def _artifact_hashes(output_dir: Path, outputs: dict[str, dict[str, Any]]) -> list[str]:
    hashes: list[str] = []
    for name, descriptor in sorted(outputs.items()):
        csv_name = descriptor.get("csv")
        if csv_name:
            hashes.append(f"{name}.csv=sha256:{sha256_file(output_dir / csv_name)}")
    return hashes


def _manifest_target_node_ids(manifest: dict[str, Any]) -> list[str]:
    features = manifest.get("a_side", {}).get("features", [])
    targets = [str(feature.get("concept_id")) for feature in features if feature.get("concept_id")]
    return sorted(set(targets))


def _manifest_target_edge_ids(manifest: dict[str, Any]) -> list[str]:
    edges = manifest.get("relationships", [])
    targets = [str(edge.get("edge_id")) for edge in edges if edge.get("edge_id")]
    return sorted(set(targets))


def _compiled_manifest_summary(runtime: CompiledManifestRuntime) -> dict[str, Any]:
    source_graph = runtime.manifest["source_graph"]
    return {
        "manifest_id": runtime.manifest["manifest_id"],
        "manifest_path": str(runtime.manifest_path),
        "manifest_sha256": "sha256:" + sha256_file(runtime.manifest_path),
        "source_graph": {
            "graph_id": source_graph.get("graph_id"),
            "graph_hash": source_graph.get("graph_hash"),
            "graph_manifest_path": str(runtime.graph_path),
        },
        "runtime_constraints": runtime.manifest["runtime_constraints"],
        "claim_boundaries": runtime.manifest["claim_boundaries"],
        "a_side_feature_count": len(runtime.manifest.get("a_side", {}).get("features", [])),
        "p_side_market_count": len(runtime.manifest.get("p_side", {}).get("markets", [])),
        "expected_lag_metadata_usage": "documentation_and_falsification_only",
        "expected_lag_metadata_used_for_signal_construction": False,
    }


def _append_manifest_evidence(
    runtime: CompiledManifestRuntime,
    output_dir: Path,
    outputs: dict[str, dict[str, Any]],
    metrics: pd.DataFrame,
) -> Path:
    _, _, graph_hash = compute_graph_hash(runtime.graph_path)
    expected_hash = runtime.manifest["source_graph"]["graph_hash"]
    if graph_hash != expected_hash:
        raise KnowledgeGraphError(
            "Compiled manifest source_graph.graph_hash does not match current graph hash."
        )
    evidence_data = {
        "id": f"validation_evidence:{runtime.manifest['manifest_id']}:backtest",
        "type": "ValidationEvidence",
        "version": "v1",
        "source": {
            "experiment_id": f"vali_backtest:{runtime.manifest['manifest_id']}",
            "compiled_manifest_id": runtime.manifest["manifest_id"],
            "compiled_manifest_hash": "sha256:" + sha256_file(runtime.manifest_path),
            "output_dir": str(output_dir),
            "artifact_hashes": _artifact_hashes(output_dir, outputs),
        },
        "target_node_ids": _manifest_target_node_ids(runtime.manifest),
        "target_edge_ids": _manifest_target_edge_ids(runtime.manifest),
        "metrics": _manifest_metric_payload(metrics),
        "falsification_gate_results": runtime.manifest.get("falsification_gates", []),
        "walk_forward_folds": [],
        "execution_evidence": {
            "source": "vali_backtest_pipeline",
            "descriptive_only": True,
        },
        "status": "not_validated",
        "claim_status": list(REQUIRED_CLAIM_BOUNDARIES),
        "evidence_status": "not_validated",
    }
    return append_evidence(runtime.graph_path, evidence_data)


def _run_backtest_pipeline_with_bundle(
    config: ValiConfig,
    bundle: InputBundle,
    output_dir: str | Path,
    *,
    compiled_runtime: CompiledManifestRuntime | None = None,
) -> PipelineResult:
    target = Path(output_dir).resolve()
    target.mkdir(parents=True, exist_ok=True)
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
    metrics = pd.concat(
        [
            metrics,
            regime_confirmation_metrics(signals, backtest.trades, config),
        ],
        ignore_index=True,
        sort=False,
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
    if compiled_runtime is not None:
        manifest["compiled_manifest"] = _compiled_manifest_summary(compiled_runtime)

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
    if compiled_runtime is not None:
        evidence_path = _append_manifest_evidence(
            compiled_runtime,
            target,
            manifest["outputs"],
            metrics,
        )
        manifest["kg_validation_evidence"] = {
            "path": str(evidence_path),
            "append_only": True,
            "status": "not_validated",
            "claim_boundary": [
                "not_alpha_evidence",
                "not_trading_readiness_evidence",
                "human_review_required",
            ],
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


def run_backtest_pipeline(config: ValiConfig, output_dir: str | Path) -> PipelineResult:
    bundle = load_inputs(config)
    return _run_backtest_pipeline_with_bundle(config, bundle, output_dir)


def run_backtest_pipeline_from_manifest(
    manifest_path: str | Path,
    output_dir: str | Path,
) -> PipelineResult:
    runtime = load_compiled_manifest_runtime(manifest_path)
    bundle = load_inputs_from_compiled_manifest(runtime)
    return _run_backtest_pipeline_with_bundle(
        runtime.config,
        bundle,
        output_dir,
        compiled_runtime=runtime,
    )


def rebuild_report(run_dir: str | Path) -> Path:
    return _artifact_rebuild_report(run_dir)
