"""Deterministic research metrics and diagnostic tables."""

from __future__ import annotations

import numpy as np
import pandas as pd


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


__all__ = [
    "divergence_half_lives",
    "forecast_metrics",
    "regime_confusion",
    "trade_metrics",
]
