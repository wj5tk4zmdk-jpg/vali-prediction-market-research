"""Conservative baseline entry decisions."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import ValiConfig


def generate_decisions(signals: pd.DataFrame, config: ValiConfig) -> pd.DataFrame:
    frame = signals.copy()
    actions: list[str] = []
    reasons: list[str] = []
    for row in frame.itertuples(index=False):
        if not np.isfinite(row.signed_divergence):
            action, reason = "none", "signal_unavailable"
        elif row.regime != "attention_leading":
            action, reason = "none", f"regime_{row.regime}"
        elif bool(getattr(row, "market_closed", False)):
            action, reason = "none", "market_closed"
        elif not bool(row.price_quality_pass):
            action, reason = "none", "price_quality_failed"
        elif not bool(row.execution_liquidity_pass):
            action, reason = "none", (
                "depth_unobserved" if not bool(row.depth_observed) else "execution_liquidity_failed"
            )
        elif not bool(row.executable):
            action, reason = "none", "price_not_executable"
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
