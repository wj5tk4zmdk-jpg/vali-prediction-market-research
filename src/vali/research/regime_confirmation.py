"""Paired regime-confirmation execution sensitivity reporting."""

from __future__ import annotations

from dataclasses import dataclass, replace
from html import escape
import json
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from ..artifacts.manifests import build_run_manifest
from ..artifacts.reports import WARNING
from ..artifacts.serialization import write_dataframe
from ..backtest import BacktestResult, run_backtest
from ..configuration.contracts import BacktestConfig, ConfigError, ValiConfig
from ..execution.snapshots import execution_validation_summary
from ..io import load_inputs
from .pipeline import _build_signals


PANEL_WARNING = (
    "Regime confirmation panel is an execution sensitivity overlay only. "
    "It is not a new signal, not classifier tuning, and not alpha evidence. "
    "Paired deltas are descriptive unless backed by valid out-of-sample, "
    "execution-aware data."
)
DEFAULT_CONFIRMATION_GRID: tuple[tuple[int, int], ...] = (
    (1, 1),
    (1, 2),
    (2, 1),
    (2, 2),
    (3, 3),
)


@dataclass(frozen=True)
class ConfirmationArm:
    entry_periods: int
    exit_periods: int

    @property
    def label(self) -> str:
        return f"{self.entry_periods}/{self.exit_periods}"


@dataclass
class ConfirmationPanelResult:
    output_dir: Path
    panel: pd.DataFrame
    deltas: pd.DataFrame
    delayed_exit_summary: pd.DataFrame
    delayed_exits: pd.DataFrame
    manifest: dict
    report_path: Path


def _validate_arm(entry_periods: int, exit_periods: int) -> ConfirmationArm:
    values = (entry_periods, exit_periods)
    if any(
        not isinstance(value, int) or isinstance(value, bool) or value < 1
        for value in values
    ):
        raise ConfigError("confirmation grid values must be positive integers")
    return ConfirmationArm(entry_periods, exit_periods)


def parse_confirmation_grid(value: str | None) -> tuple[ConfirmationArm, ...]:
    """Parse a comma-separated grid such as ``1/1,1/2,2/2``."""
    if value is None or value.strip() == "":
        pairs = DEFAULT_CONFIRMATION_GRID
    else:
        pairs = []
        for raw_part in value.split(","):
            part = raw_part.strip()
            pieces = part.split("/")
            if len(pieces) != 2 or not all(piece.isdigit() for piece in pieces):
                raise ConfigError(
                    "confirmation grid entries must look like positive_integer/positive_integer"
                )
            pairs.append((int(pieces[0]), int(pieces[1])))

    arms: list[ConfirmationArm] = []
    seen: set[str] = set()
    for entry_periods, exit_periods in pairs:
        arm = _validate_arm(entry_periods, exit_periods)
        if arm.label in seen:
            raise ConfigError("confirmation grid entries must be unique")
        seen.add(arm.label)
        arms.append(arm)
    return tuple(arms)


def build_confirmation_grid(
    config: ValiConfig, value: str | None = None
) -> tuple[ConfirmationArm, ...]:
    """Return the requested grid plus baseline and current config arms."""
    arms = list(parse_confirmation_grid(value))
    baseline = ConfirmationArm(1, 1)
    current = _validate_arm(
        config.backtest.entry_regime_confirmation_periods,
        config.backtest.exit_regime_confirmation_periods,
    )
    for arm in (baseline, current):
        if arm.label not in {candidate.label for candidate in arms}:
            arms.append(arm)
    return tuple(arms)


def _with_confirmation(config: ValiConfig, arm: ConfirmationArm) -> ValiConfig:
    backtest = replace(
        config.backtest,
        entry_regime_confirmation_periods=arm.entry_periods,
        exit_regime_confirmation_periods=arm.exit_periods,
    )
    return replace(config, backtest=backtest)


def _exit_reason_count(trades: pd.DataFrame, reason: str) -> int:
    if trades.empty or "exit_reason" not in trades:
        return 0
    return int((trades["exit_reason"] == reason).sum())


def _forced_settlement_count(trades: pd.DataFrame) -> int:
    if trades.empty or "exit_reason" not in trades:
        return 0
    return int(trades["exit_reason"].astype(str).str.contains("forced_settlement").sum())


def _mean_holding_days(trades: pd.DataFrame) -> float:
    if trades.empty or not {"entry_at", "exit_at"}.issubset(trades.columns):
        return np.nan
    entry_at = pd.to_datetime(trades["entry_at"], utc=True)
    exit_at = pd.to_datetime(trades["exit_at"], utc=True)
    return float(((exit_at - entry_at).dt.total_seconds() / 86400).mean())


def _max_drawdown(trades: pd.DataFrame, execution_validated: bool) -> float:
    if not execution_validated:
        return np.nan
    if trades.empty:
        return 0.0
    equity = trades.sort_values("exit_at")["net_pnl"].cumsum()
    drawdown = equity - equity.cummax().clip(lower=0)
    return float(drawdown.min())


def _net_pnl(trades: pd.DataFrame, execution_validated: bool) -> float:
    if not execution_validated:
        return np.nan
    return float(trades["net_pnl"].sum()) if not trades.empty else 0.0


def count_regime_flip_episodes(signals: pd.DataFrame, trades: pd.DataFrame) -> int:
    """Count non-attention-leading regime episodes during live trades."""
    if trades.empty or signals.empty:
        return 0
    required = {"contract_id", "cutoff_at", "regime"}
    if not required.issubset(signals.columns):
        return 0
    count = 0
    for trade in trades.itertuples(index=False):
        contract_id = getattr(trade, "contract_id")
        entry_at = pd.Timestamp(getattr(trade, "entry_at"))
        exit_at = pd.Timestamp(getattr(trade, "exit_at"))
        timeline = signals.loc[
            (signals["contract_id"] == contract_id)
            & (signals["cutoff_at"] > entry_at)
            & (signals["cutoff_at"] <= exit_at)
        ].sort_values("cutoff_at")
        in_non_attention = False
        for regime in timeline["regime"]:
            is_non_attention = pd.notna(regime) and regime != "attention_leading"
            if is_non_attention and not in_non_attention:
                count += 1
            in_non_attention = is_non_attention
    return count


def summarize_confirmation_arm(
    arm: ConfirmationArm,
    signals: pd.DataFrame,
    trades: pd.DataFrame,
    execution_validated: bool,
) -> dict:
    """Summarize one confirmation arm in the paired panel."""
    action = (
        signals["action"] if "action" in signals else pd.Series(dtype=object)
    )
    delayed = (
        trades["exit_confirmation_delay_days"]
        if "exit_confirmation_delay_days" in trades
        else pd.Series(dtype=float)
    )
    fee_total = (
        float(trades.get("entry_fee", pd.Series(dtype=float)).sum())
        + float(trades.get("exit_fee", pd.Series(dtype=float)).sum())
        if not trades.empty
        else 0.0
    )
    return {
        "grid_label": arm.label,
        "entry_regime_confirmation_periods": arm.entry_periods,
        "exit_regime_confirmation_periods": arm.exit_periods,
        "execution_validated": bool(execution_validated),
        "trades": len(trades),
        "entry_signal_count": int(action.isin(["long_yes", "long_no"]).sum()),
        "no_trade_rate": (
            float((action == "none").mean()) if len(signals) else np.nan
        ),
        "regime_change_exits": _exit_reason_count(trades, "regime_change"),
        "delayed_regime_exits": int((delayed > 0).sum()),
        "stop_loss_exits": _exit_reason_count(trades, "stop_loss"),
        "convergence_exits": _exit_reason_count(trades, "convergence"),
        "max_holding_exits": _exit_reason_count(trades, "max_holding_period"),
        "pre_settlement_exits": _exit_reason_count(trades, "pre_settlement"),
        "forced_settlement_exits": _forced_settlement_count(trades),
        "mean_holding_days": _mean_holding_days(trades),
        "fees_paid": fee_total,
        "net_pnl": _net_pnl(trades, execution_validated),
        "max_drawdown": _max_drawdown(trades, execution_validated),
        "regime_flip_episodes_during_trades": count_regime_flip_episodes(
            signals, trades
        ),
    }


def confirmation_deltas(panel: pd.DataFrame) -> pd.DataFrame:
    """Return long-form metric deltas versus the ``1/1`` baseline."""
    if panel.empty:
        return pd.DataFrame()
    baseline_rows = panel.loc[panel["grid_label"] == "1/1"]
    if baseline_rows.empty:
        raise ConfigError("confirmation panel requires a 1/1 baseline")
    baseline = baseline_rows.iloc[0]
    skip = {
        "grid_label",
        "entry_regime_confirmation_periods",
        "exit_regime_confirmation_periods",
        "execution_validated",
    }
    metrics = [
        column
        for column in panel.columns
        if column not in skip and pd.api.types.is_numeric_dtype(panel[column])
    ]
    rows: list[dict] = []
    for _, arm in panel.loc[panel["grid_label"] != "1/1"].iterrows():
        for metric in metrics:
            baseline_value = baseline[metric]
            arm_value = arm[metric]
            rows.append(
                {
                    "grid_label": arm["grid_label"],
                    "metric": metric,
                    "baseline_value": baseline_value,
                    "arm_value": arm_value,
                    "delta": arm_value - baseline_value,
                }
            )
    return pd.DataFrame(rows)


def delayed_exit_decomposition(
    baseline_trades: pd.DataFrame,
    buffered_trades: pd.DataFrame,
    arm: ConfirmationArm,
) -> pd.DataFrame:
    """Compare buffered exits against matching baseline regime-change exits."""
    columns = [
        "grid_label",
        "trade_id",
        "event_id",
        "contract_id",
        "side",
        "baseline_exit_at",
        "baseline_exit_reason",
        "baseline_exit_probability",
        "buffered_exit_at",
        "buffered_exit_reason",
        "buffered_exit_probability",
        "delay_days",
        "gross_exit_value_delta",
        "net_pnl_delta",
        "saved_exit",
        "bad_delayed_exit",
    ]
    if baseline_trades.empty or buffered_trades.empty:
        return pd.DataFrame(columns=columns)
    if "trade_id" not in baseline_trades or "trade_id" not in buffered_trades:
        return pd.DataFrame(columns=columns)
    merged = baseline_trades.merge(
        buffered_trades,
        on="trade_id",
        suffixes=("_baseline", "_buffered"),
    )
    rows: list[dict] = []
    for row in merged.itertuples(index=False):
        baseline_exit_at = pd.Timestamp(getattr(row, "exit_at_baseline"))
        buffered_exit_at = pd.Timestamp(getattr(row, "exit_at_buffered"))
        baseline_reason = getattr(row, "exit_reason_baseline")
        if baseline_reason != "regime_change" or buffered_exit_at <= baseline_exit_at:
            continue
        baseline_value = (
            float(getattr(row, "units_baseline"))
            * float(getattr(row, "exit_probability_baseline"))
        )
        buffered_value = (
            float(getattr(row, "units_buffered"))
            * float(getattr(row, "exit_probability_buffered"))
        )
        net_delta = float(getattr(row, "net_pnl_buffered")) - float(
            getattr(row, "net_pnl_baseline")
        )
        rows.append(
            {
                "grid_label": arm.label,
                "trade_id": getattr(row, "trade_id"),
                "event_id": getattr(row, "event_id_baseline"),
                "contract_id": getattr(row, "contract_id_baseline"),
                "side": getattr(row, "side_baseline"),
                "baseline_exit_at": baseline_exit_at,
                "baseline_exit_reason": baseline_reason,
                "baseline_exit_probability": getattr(
                    row, "exit_probability_baseline"
                ),
                "buffered_exit_at": buffered_exit_at,
                "buffered_exit_reason": getattr(row, "exit_reason_buffered"),
                "buffered_exit_probability": getattr(
                    row, "exit_probability_buffered"
                ),
                "delay_days": (
                    buffered_exit_at - baseline_exit_at
                ).total_seconds()
                / 86400,
                "gross_exit_value_delta": buffered_value - baseline_value,
                "net_pnl_delta": net_delta,
                "saved_exit": net_delta > 0,
                "bad_delayed_exit": net_delta < 0,
            }
        )
    return pd.DataFrame(rows, columns=columns)


def delayed_exit_summary(delayed_exits: pd.DataFrame) -> pd.DataFrame:
    """Roll up delayed-exit decomposition into desk-facing diagnostics."""
    total = int(len(delayed_exits))
    if not total:
        return pd.DataFrame(
            [
                {
                    "delayed_exits_total": 0,
                    "delayed_exits_helped": 0,
                    "delayed_exits_hurt": 0,
                    "net_delay_pnl": 0.0,
                    "helped_pct": 0.0,
                    "hurt_pct": 0.0,
                }
            ]
        )
    helped = int(delayed_exits["saved_exit"].sum())
    hurt = int(delayed_exits["bad_delayed_exit"].sum())
    net_pnl = float(delayed_exits["net_pnl_delta"].sum())
    return pd.DataFrame(
        [
            {
                "delayed_exits_total": total,
                "delayed_exits_helped": helped,
                "delayed_exits_hurt": hurt,
                "net_delay_pnl": net_pnl,
                "helped_pct": helped / total,
                "hurt_pct": hurt / total,
            }
        ]
    )


def _table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "<p class='empty'>No observations</p>"
    return frame.to_html(index=False, border=0, classes="data", na_rep="NA")


def render_confirmation_report(
    output_path: Path,
    panel: pd.DataFrame,
    deltas: pd.DataFrame,
    summary: pd.DataFrame,
    delayed_exits: pd.DataFrame,
    manifest: dict,
) -> None:
    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>VALI Regime Confirmation Panel</title>
<style>
body{{font-family:Arial,sans-serif;color:#172033;margin:0;background:#f5f7fb}}main{{max-width:1160px;margin:32px auto;background:white;padding:40px;box-shadow:0 8px 30px #ccd3df}}
h1{{margin:0;color:#142a4d}}h2{{margin-top:32px;border-bottom:2px solid #dce5f2;padding-bottom:7px}}.warning{{background:#fff3d7;border-left:5px solid #cf8f00;padding:14px 18px;margin:24px 0}}
.meta{{color:#526176}}table.data{{border-collapse:collapse;width:100%;font-size:13px}}table.data th{{background:#17365d;color:white;text-align:left;padding:8px}}table.data td{{padding:7px 8px;border-bottom:1px solid #dbe1e8}}.empty{{color:#6d7785;font-style:italic}}
</style></head><body><main>
<h1>VALI Regime Confirmation Sensitivity Panel</h1>
<p class="meta">Baseline arm: 1/1 | methodology {escape(str(manifest.get('methodology_version', '')))}</p>
<div class="warning"><strong>Research warning:</strong> {escape(WARNING)}</div>
<div class="warning"><strong>Confirmation-panel warning:</strong> {escape(PANEL_WARNING)}</div>
<h2>Per-arm metrics</h2>{_table(panel)}
<h2>Deltas versus 1/1 baseline</h2>{_table(deltas)}
<h2>Delayed Exit Summary (Dragon Under the Bridge)</h2>{_table(summary)}
<h2>Delayed exit decomposition</h2>{_table(delayed_exits)}
<h2>Manifest</h2><pre>{escape(json.dumps(manifest, indent=2, sort_keys=True, default=str))}</pre>
</main></body></html>"""
    output_path.write_text(html, encoding="utf-8")


def run_confirmation_panel(
    config: ValiConfig,
    output_dir: str | Path,
    grid: str | None = None,
) -> ConfirmationPanelResult:
    target = Path(output_dir).resolve()
    target.mkdir(parents=True, exist_ok=True)
    bundle = load_inputs(config)
    arms = build_confirmation_grid(config, grid)
    arm_results: dict[str, tuple[pd.DataFrame, BacktestResult, bool]] = {}
    rows: list[dict] = []

    for arm in arms:
        arm_config = _with_confirmation(config, arm)
        signals, _ = _build_signals(arm_config, bundle)
        backtest = run_backtest(signals, bundle.events, arm_config)
        execution_validated = execution_validation_summary(signals)[
            "capacity_claims_enabled"
        ]
        rows.append(
            summarize_confirmation_arm(
                arm, signals, backtest.trades, execution_validated
            )
        )
        arm_results[arm.label] = (signals, backtest, execution_validated)

    panel = pd.DataFrame(rows)
    deltas = confirmation_deltas(panel)
    baseline_trades = arm_results["1/1"][1].trades
    delayed_exits = pd.concat(
        [
            delayed_exit_decomposition(
                baseline_trades, arm_results[arm.label][1].trades, arm
            )
            for arm in arms
            if arm.label != "1/1"
        ],
        ignore_index=True,
    )
    delayed_summary = delayed_exit_summary(delayed_exits)

    manifest = build_run_manifest(config)
    manifest["validation"] = bundle.validation.as_dict()
    manifest["confirmation_panel"] = {
        "baseline": "1/1",
        "grid": [arm.label for arm in arms],
        "warning": PANEL_WARNING,
        "paired_baseline_delta_analysis": "computed_against_1/1",
    }
    outputs = {
        "regime_confirmation_panel": panel,
        "regime_confirmation_deltas": deltas,
        "regime_confirmation_delayed_exit_summary": delayed_summary,
        "regime_confirmation_delayed_exits": delayed_exits,
    }
    manifest["outputs"] = {
        name: write_dataframe(frame, name, target)
        for name, frame in outputs.items()
    }
    manifest_path = target / "regime_confirmation_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, default=str),
        encoding="utf-8",
    )
    report_path = target / "regime_confirmation_report.html"
    render_confirmation_report(
        report_path, panel, deltas, delayed_summary, delayed_exits, manifest
    )
    return ConfirmationPanelResult(
        output_dir=target,
        panel=panel,
        deltas=deltas,
        delayed_exit_summary=delayed_summary,
        delayed_exits=delayed_exits,
        manifest=manifest,
        report_path=report_path,
    )


__all__ = [
    "ConfirmationArm",
    "ConfirmationPanelResult",
    "DEFAULT_CONFIRMATION_GRID",
    "PANEL_WARNING",
    "build_confirmation_grid",
    "confirmation_deltas",
    "count_regime_flip_episodes",
    "delayed_exit_decomposition",
    "delayed_exit_summary",
    "parse_confirmation_grid",
    "render_confirmation_report",
    "run_confirmation_panel",
    "summarize_confirmation_arm",
]
