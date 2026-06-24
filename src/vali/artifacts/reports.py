"""Dependency-light HTML report assembly and reconstruction."""

from __future__ import annotations

from html import escape
import json
from pathlib import Path

import pandas as pd


WARNING = (
    "Research-only output. Small samples, in-sample relationships, or positive "
    "historical returns are not evidence of persistent alpha or live tradability."
)


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


__all__ = ["WARNING", "rebuild_report", "render_html_report"]
