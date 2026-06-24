"""Predeclared sensitivity-panel orchestration."""

from __future__ import annotations

from typing import Callable

import numpy as np
import pandas as pd

from ..backtest import run_backtest
from ..configuration.contracts import ValiConfig
from ..data.contracts import InputBundle
from ..reporting import forecast_metrics


BuildSignals = Callable[
    [ValiConfig, InputBundle, int | None],
    tuple[pd.DataFrame, pd.DataFrame],
]
ExecutionSummary = Callable[[pd.DataFrame], dict]


def run_sensitivity(
    config: ValiConfig,
    bundle: InputBundle,
    build_signals: BuildSignals,
    execution_summary: ExecutionSummary,
) -> pd.DataFrame:
    """Run the frozen velocity-window panel without selecting a winner."""
    rows: list[dict] = []
    for window in config.signal.sensitivity_windows:
        signals, _ = build_signals(config, bundle, window)
        result = run_backtest(signals, bundle.events, config)
        execution_validated = execution_summary(signals)["capacity_claims_enabled"]
        fm, _ = forecast_metrics(result.forecasts)
        vali_brier = (
            fm.loc[
                (fm["model"] == "vali_calibrated")
                & (fm["metric"] == "brier_score"),
                "value",
            ]
            if not fm.empty
            else pd.Series(dtype=float)
        )
        rows.append(
            {
                "velocity_window": window,
                "forecast_count": len(result.forecasts),
                "vali_brier_score": (
                    float(vali_brier.iloc[0]) if len(vali_brier) else np.nan
                ),
                "trade_count": len(result.trades),
                "net_pnl": (
                    float(result.trades["net_pnl"].sum())
                    if execution_validated and not result.trades.empty
                    else (0.0 if execution_validated else np.nan)
                ),
                "execution_validated": execution_validated,
                "entry_signal_count": int(
                    signals["action"].isin(["long_yes", "long_no"]).sum()
                ),
                "no_trade_rate": (
                    float((signals["action"] == "none").mean())
                    if len(signals)
                    else np.nan
                ),
            }
        )
    return pd.DataFrame(rows)
