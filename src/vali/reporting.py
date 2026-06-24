"""Metrics, calibration tables, machine outputs, and dependency-light HTML."""

from __future__ import annotations

from html import escape
import json
from pathlib import Path

import numpy as np
import pandas as pd


WARNING = (
    "Research-only output. Small samples, in-sample relationships, or positive "
    "historical returns are not evidence of persistent alpha or live tradability."
)


def _log_loss(y: pd.Series, p: pd.Series) -> float:
    clipped = p.clip(1e-12, 1 - 1e-12)
    return float(-(y * np.log(clipped) + (1 - y) * np.log(1 - clipped)).mean())


def forecast_metrics(forecasts: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    metric_rows: list[dict] = []
    calibration_rows: list[dict] = []
    if forecasts.empty:
        return pd.DataFrame(columns=["model", "metric", "value", "observations"]), pd.DataFrame()
    models = {
        "market": "market_probability",
        "historical_frequency": "historical_probability",
        "vali_calibrated": "vali_calibrated_probability",
    }
    for model, column in models.items():
        valid = forecasts.dropna(subset=["outcome", column]).copy()
        if valid.empty:
            continue
        y = valid["outcome"].astype(float)
        p = valid[column].astype(float)
        metric_rows.extend(
            [
                {"model": model, "metric": "brier_score", "value": float(((p - y) ** 2).mean()), "observations": len(valid)},
                {"model": model, "metric": "log_loss", "value": _log_loss(y, p), "observations": len(valid)},
                {"model": model, "metric": "hit_rate", "value": float(((p >= 0.5).astype(int) == y).mean()), "observations": len(valid)},
            ]
        )
        bins = pd.cut(p, bins=np.linspace(0, 1, 11), include_lowest=True, duplicates="drop")
        grouped = valid.assign(_probability=p, _bin=bins).groupby("_bin", observed=True)
        for interval, group in grouped:
            calibration_rows.append(
                {
                    "model": model,
                    "probability_bin": str(interval),
                    "mean_probability": float(group["_probability"].mean()),
                    "observed_frequency": float(group["outcome"].mean()),
                    "count": len(group),
                }
            )
    return pd.DataFrame(metric_rows), pd.DataFrame(calibration_rows)


def trade_metrics(trades: pd.DataFrame, execution_validated: bool = True) -> pd.DataFrame:
    if not execution_validated:
        values = {
            "execution_validated": 0,
            "trade_count": 0,
            "net_pnl": np.nan,
            "hit_rate": np.nan,
            "payoff_ratio": np.nan,
            "max_drawdown": np.nan,
            "mean_capacity_used": np.nan,
        }
    elif trades.empty:
        values = {
            "execution_validated": 1,
            "trade_count": 0,
            "net_pnl": 0.0,
            "hit_rate": np.nan,
            "payoff_ratio": np.nan,
            "max_drawdown": 0.0,
            "mean_capacity_used": np.nan,
        }
    else:
        winners = trades.loc[trades["net_pnl"] > 0, "net_pnl"]
        losers = trades.loc[trades["net_pnl"] < 0, "net_pnl"].abs()
        equity = trades.sort_values("exit_at")["net_pnl"].cumsum()
        drawdown = equity - equity.cummax().clip(lower=0)
        values = {
            "execution_validated": 1,
            "trade_count": len(trades),
            "net_pnl": float(trades["net_pnl"].sum()),
            "hit_rate": float(trades["hit"].mean()),
            "payoff_ratio": float(winners.mean() / losers.mean()) if len(winners) and len(losers) else np.nan,
            "max_drawdown": float(drawdown.min()),
            "mean_capacity_used": float(trades["capacity_used"].mean()),
        }
    return pd.DataFrame([{"metric": key, "value": value} for key, value in values.items()])


def divergence_half_lives(signals: pd.DataFrame, entry_threshold: float, exit_threshold: float) -> pd.DataFrame:
    rows: list[dict] = []
    for contract_id, group in signals.groupby("contract_id"):
        frame = group.sort_values("cutoff_at").reset_index(drop=True)
        active = False
        start_at = None
        peak = np.nan
        for row in frame.itertuples(index=False):
            magnitude = row.divergence_magnitude
            if not active and pd.notna(magnitude) and magnitude >= entry_threshold:
                active, start_at, peak = True, row.cutoff_at, float(magnitude)
            elif active:
                peak = max(peak, float(magnitude)) if pd.notna(magnitude) else peak
                if pd.notna(magnitude) and magnitude <= exit_threshold:
                    rows.append(
                        {
                            "contract_id": contract_id,
                            "started_at": start_at,
                            "converged_at": row.cutoff_at,
                            "half_life_days": (row.cutoff_at - start_at).total_seconds() / 86400,
                            "peak_magnitude": peak,
                            "resolved": True,
                        }
                    )
                    active = False
        if active:
            rows.append(
                {
                    "contract_id": contract_id,
                    "started_at": start_at,
                    "converged_at": pd.NaT,
                    "half_life_days": np.nan,
                    "peak_magnitude": peak,
                    "resolved": False,
                }
            )
    return pd.DataFrame(rows)


def regime_confusion(signals: pd.DataFrame) -> pd.DataFrame:
    if signals.empty or "realized_regime" not in signals:
        return pd.DataFrame()
    eligible = signals.loc[signals["regime"].notna() & signals["realized_regime"].notna()]
    if eligible.empty:
        return pd.DataFrame()
    return (
        pd.crosstab(eligible["realized_regime"], eligible["regime"])
        .rename_axis(index="realized_regime", columns="predicted_regime")
        .stack()
        .rename("count")
        .reset_index()
    )


def write_dataframe(frame: pd.DataFrame, name: str, output_dir: Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / f"{name}.csv"
    parquet_path = output_dir / f"{name}.parquet"
    frame.to_csv(csv_path, index=False, date_format="%Y-%m-%dT%H:%M:%S%z")
    parquet_written = False
    try:
        frame.to_parquet(parquet_path, index=False)
        parquet_written = True
    except (ImportError, ModuleNotFoundError):
        pass
    return {"csv": csv_path.name, "parquet": parquet_path.name if parquet_written else None, "rows": len(frame)}


def _table(frame: pd.DataFrame, empty_message: str = "No observations") -> str:
    if frame.empty:
        return f"<p class='empty'>{escape(empty_message)}</p>"
    return frame.to_html(index=False, border=0, classes="data", na_rep="NA", float_format=lambda value: f"{value:.6g}")


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
    metric_view = metrics.copy()
    exclusion_counts = (
        exclusions.groupby(["stage", "reason"], dropna=False).size().rename("count").reset_index()
        if not exclusions.empty
        else pd.DataFrame()
    )
    execution_status = run_manifest.get("execution_validation", {}).get("status", "")
    validated_execution_statuses = {
        "complete_executable_snapshots",
        "observed_depth_available",
    }
    execution_warning = (
        "<div class='warning'><strong>Execution disabled:</strong> Historical inputs do not contain a complete executable snapshot record. P&amp;L, drawdown, and capacity are not validated.</div>"
        if execution_status and execution_status not in validated_execution_statuses
        else ""
    )
    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>VALI Research Report</title>
<style>
body{{font-family:Arial,sans-serif;color:#172033;margin:0;background:#f4f6f9}}main{{max-width:1120px;margin:32px auto;background:white;padding:40px;box-shadow:0 8px 30px #cdd3dd}}
h1{{margin:0;color:#152b4f}}h2{{margin-top:34px;border-bottom:2px solid #dce5f2;padding-bottom:7px}}.warning{{background:#fff4d6;border-left:5px solid #d39500;padding:14px 18px;margin:24px 0}}
.meta{{color:#526176}}table.data{{border-collapse:collapse;width:100%;font-size:13px}}table.data th{{background:#17365d;color:white;text-align:left;padding:8px}}table.data td{{padding:7px 8px;border-bottom:1px solid #dbe1e8}}.empty{{color:#6d7785;font-style:italic}}code{{background:#eef2f7;padding:2px 4px}}
</style></head><body><main>
<h1>VALI Fed-Rate Research Report</h1><p class="meta">Methodology {escape(str(run_manifest.get('methodology_version', '')))} | parameter freeze {escape(str(run_manifest.get('parameter_freeze_date', '')))}</p>
<div class="warning"><strong>Research warning:</strong> {escape(WARNING)}</div>
{execution_warning}
<h2>Forecast metrics</h2>{_table(metric_view)}
<h2>Walk-forward forecasts</h2>{_table(forecasts.tail(30))}
<h2>Calibration by decile</h2>{_table(calibration)}
<h2>Execution-aware trades</h2>{_table(trades)}
<h2>Sensitivity analysis</h2>{_table(sensitivity)}
<h2>Regime diagnostic</h2>{_table(regime_table)}
<h2>Exclusions and no-trade reasons</h2>{_table(exclusion_counts)}
<h2>Reproducibility manifest</h2><pre>{escape(json.dumps(run_manifest, indent=2, sort_keys=True))}</pre>
</main></body></html>"""
    output_path.write_text(html, encoding="utf-8")
