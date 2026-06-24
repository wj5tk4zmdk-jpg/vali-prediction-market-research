"""Event-grouped, leak-free walk-forward research evaluation."""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..configuration.contracts import ValiConfig
from ..data.point_in_time import strictly_prior_rows
from ..data.validation import validate_event_identity
from .calibration import fit_logistic, predict_logistic


def event_snapshots(
    signals: pd.DataFrame,
    events: pd.DataFrame,
    days_before: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    snapshots: list[dict] = []
    exclusions: list[dict] = []
    for event in events.sort_values("meeting_at").itertuples(index=False):
        if pd.isna(event.outcome):
            exclusions.append(
                {
                    "event_id": event.event_id,
                    "contract_id": event.contract_id,
                    "stage": "walk_forward",
                    "reason": "unresolved_event",
                }
            )
            continue
        deadline = event.meeting_at - pd.Timedelta(days=days_before)
        eligible = signals.loc[
            (signals["contract_id"] == event.contract_id)
            & (signals["cutoff_at"] <= deadline)
        ].sort_values("cutoff_at")
        price_rows = eligible.loc[eligible["price"].notna()]
        if price_rows.empty:
            exclusions.append(
                {
                    "event_id": event.event_id,
                    "contract_id": event.contract_id,
                    "stage": "walk_forward",
                    "reason": "no_eligible_market_price",
                }
            )
            continue
        row = price_rows.iloc[-1]
        snapshots.append(
            {
                "event_id": event.event_id,
                "contract_id": event.contract_id,
                "meeting_at": event.meeting_at,
                "forecast_at": row["cutoff_at"],
                "outcome": int(event.outcome),
                "market_probability": float(row["price"]),
                "market_logit": float(row["logit_price"]),
                "signed_divergence": (
                    float(row["signed_divergence"])
                    if pd.notna(row["signed_divergence"])
                    else np.nan
                ),
                "regime": row["regime"],
            }
        )
    return pd.DataFrame(snapshots), pd.DataFrame(exclusions)


def run_walk_forward(
    signals: pd.DataFrame,
    events: pd.DataFrame,
    config: ValiConfig,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    validate_event_identity(events, signals)
    snapshots, exclusions = event_snapshots(
        signals, events, config.backtest.days_before_settlement
    )
    if snapshots.empty:
        return pd.DataFrame(), exclusions
    snapshots = snapshots.sort_values("meeting_at").reset_index(drop=True)
    resolved_events = (
        events.loc[events["outcome"].notna()]
        .sort_values("meeting_at")
        .reset_index(drop=True)
    )
    predictions: list[dict] = []
    exclusion_rows = exclusions.to_dict("records") if not exclusions.empty else []

    for _, test in snapshots.iterrows():
        prior_events = strictly_prior_rows(
            resolved_events, "meeting_at", test["meeting_at"]
        )
        training = strictly_prior_rows(snapshots, "meeting_at", test["meeting_at"])
        if len(prior_events) < config.backtest.min_train_events:
            exclusion_rows.append(
                {
                    "event_id": test["event_id"],
                    "contract_id": test["contract_id"],
                    "stage": "walk_forward",
                    "reason": "insufficient_prior_events",
                }
            )
            continue
        history_probability = float(
            (prior_events["outcome"].sum() + 0.5) / (len(prior_events) + 1)
        )
        complete = training.dropna(subset=["market_logit", "signed_divergence"])
        if len(complete) < config.backtest.min_train_events:
            calibrated = np.nan
            exclusion_rows.append(
                {
                    "event_id": test["event_id"],
                    "contract_id": test["contract_id"],
                    "stage": "calibration",
                    "reason": "insufficient_complete_prior_signals",
                }
            )
        elif not np.isfinite(test["signed_divergence"]):
            calibrated = np.nan
            exclusion_rows.append(
                {
                    "event_id": test["event_id"],
                    "contract_id": test["contract_id"],
                    "stage": "calibration",
                    "reason": "test_signal_unavailable",
                }
            )
        else:
            coefficients = fit_logistic(
                complete[["market_logit", "signed_divergence"]].to_numpy(),
                complete["outcome"].to_numpy(),
                l2=config.backtest.calibration_l2,
            )
            calibrated = float(
                predict_logistic(
                    coefficients,
                    np.array([[test["market_logit"], test["signed_divergence"]]]),
                )[0]
            )
        predictions.append(
            {
                **test.to_dict(),
                "fold": len(prior_events) - config.backtest.min_train_events + 1,
                "training_events": len(prior_events),
                "calibration_training_events": len(complete),
                "historical_probability": history_probability,
                "vali_calibrated_probability": calibrated,
            }
        )
    return pd.DataFrame(predictions), pd.DataFrame(exclusion_rows)
