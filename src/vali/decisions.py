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
    for row in frame.itertuples(index=False):
        if not np.isfinite(row.signed_divergence):
            action, reason = "none", "signal_unavailable"
        elif row.regime != "attention_leading":
            action, reason = "none", f"regime_{row.regime}"
        else:
            execution_rejection = signal_execution_rejection(row)
            if execution_rejection:
                action, reason = "none", execution_rejection
            elif row.signed_divergence >= config.signal.entry_threshold:
                action, reason = "long_yes", "entry_positive_divergence"
            elif row.signed_divergence <= -config.signal.entry_threshold:
                action, reason = "long_no", "entry_negative_divergence"
            else:
                action, reason = "none", "below_entry_threshold"
        actions.append(action)
        reasons.append(reason)
    frame["action"] = actions
    frame["decision_reason"] = reasons
    return frame
