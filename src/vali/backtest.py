"""Event-grouped walk-forward calibration and execution-aware simulation."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .config import ValiConfig
from .execution.simulator import simulate_trades as _execution_simulate_trades
from .execution.snapshots import liquidation_value as _execution_liquidation_value
from .research.walk_forward import (
    event_snapshots as _research_event_snapshots,
    run_walk_forward as _research_run_walk_forward,
)


@dataclass
class BacktestResult:
    forecasts: pd.DataFrame
    trades: pd.DataFrame
    exclusions: pd.DataFrame


def _event_snapshots(
    signals: pd.DataFrame,
    events: pd.DataFrame,
    days_before: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    return _research_event_snapshots(signals, events, days_before)


def run_walk_forward(
    signals: pd.DataFrame, events: pd.DataFrame, config: ValiConfig
) -> tuple[pd.DataFrame, pd.DataFrame]:
    return _research_run_walk_forward(signals, events, config)


def _liquidation_value(
    row: pd.Series, side: str, units: float
) -> tuple[float, float]:
    return _execution_liquidation_value(row, side, units)


def simulate_trades(
    signals: pd.DataFrame,
    events: pd.DataFrame,
    config: ValiConfig,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    return _execution_simulate_trades(signals, events, config)


def run_backtest(
    signals: pd.DataFrame, events: pd.DataFrame, config: ValiConfig
) -> BacktestResult:
    forecasts, forecast_exclusions = run_walk_forward(signals, events, config)
    trades, trade_exclusions = simulate_trades(signals, events, config)
    exclusions = pd.concat(
        [forecast_exclusions, trade_exclusions], ignore_index=True
    )
    return BacktestResult(
        forecasts=forecasts, trades=trades, exclusions=exclusions
    )
