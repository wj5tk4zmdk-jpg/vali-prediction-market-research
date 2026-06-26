"""Conservative baseline entry decisions."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import ValiConfig
from .execution.liquidity import signal_execution_rejection


def generate_decisions(signals: pd.DataFrame, config: ValiConfig) -> pd.DataFrame:
    frame = signals.copy()
    actions: list[str] = []
    reasons: list[str] = []
    entry_confirmed: list[bool] = []
    entry_streak_values: list[int] = []
    streaks: dict[str, int] = {}
    required_streak = config.backtest.entry_regime_confirmation_periods
    for row in frame.itertuples(index=False):
        contract_id = str(getattr(row, "contract_id", "__global__"))
        streak = streaks.get(contract_id, 0)
        row_confirmed = False
        row_streak = 0
        if not np.isfinite(row.signed_divergence):
            action, reason = "none", "signal_unavailable"
        elif row.regime != "attention_leading":
            action, reason = "none", f"regime_{row.regime}"
        else:
            execution_rejection = signal_execution_rejection(row)
            if execution_rejection:
                action, reason = "none", execution_rejection
            elif row.signed_divergence >= config.signal.entry_threshold:
                streak += 1
                row_streak = streak
                row_confirmed = streak >= required_streak
                if row_confirmed:
                    action, reason = "long_yes", "entry_positive_divergence"
                else:
                    action, reason = "none", "entry_regime_unconfirmed"
            elif row.signed_divergence <= -config.signal.entry_threshold:
                streak += 1
                row_streak = streak
                row_confirmed = streak >= required_streak
                if row_confirmed:
                    action, reason = "long_no", "entry_negative_divergence"
                else:
                    action, reason = "none", "entry_regime_unconfirmed"
            else:
                action, reason = "none", "below_entry_threshold"
        if reason not in {
            "entry_positive_divergence",
            "entry_negative_divergence",
            "entry_regime_unconfirmed",
        }:
            streak = 0
        streaks[contract_id] = streak
        actions.append(action)
        reasons.append(reason)
        entry_confirmed.append(row_confirmed)
        entry_streak_values.append(row_streak)
    frame["action"] = actions
    frame["decision_reason"] = reasons
    frame["entry_regime_confirmed"] = entry_confirmed
    frame["entry_confirmation_streak"] = entry_streak_values
    return frame
