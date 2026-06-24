"""Point-in-time availability, vintage, fold, and label-isolation helpers."""

from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd

from .contracts import DataValidationError


def parse_utc(frame: pd.DataFrame, columns: Iterable[str], label: str) -> None:
    """Parse timezone-aware timestamps in place using the existing contract."""
    for column in columns:
        for value in frame[column].dropna():
            try:
                if pd.Timestamp(value).tzinfo is None:
                    raise DataValidationError(
                        f"{label}.{column} contains a timezone-free timestamp"
                    )
            except DataValidationError:
                raise
            except Exception as exc:
                raise DataValidationError(
                    f"{label}.{column} contains an invalid timestamp"
                ) from exc
        try:
            frame[column] = pd.to_datetime(frame[column], utc=True, errors="raise")
        except Exception as exc:
            raise DataValidationError(
                f"{label}.{column} contains an invalid or timezone-free timestamp"
            ) from exc


def asof_feature_values(
    feature_rows: pd.DataFrame,
    cutoffs: pd.Series,
    availability_lag_days: int,
    missing_policy: str,
    max_age_days: int,
) -> pd.Series:
    """Select only the latest vintage publicly available at each cutoff."""
    rows = feature_rows.copy().sort_values(["available_at", "observation_at"])
    rows["effective_available_at"] = rows[["available_at"]].max(axis=1)
    lagged = rows["observation_at"] + pd.to_timedelta(availability_lag_days, unit="D")
    rows["effective_available_at"] = pd.concat(
        [rows["effective_available_at"], lagged.rename("lagged")], axis=1
    ).max(axis=1)
    values: list[float] = []
    for cutoff in cutoffs:
        known = rows.loc[
            (rows["effective_available_at"] <= cutoff)
            & (rows["observation_at"] <= cutoff)
        ]
        if known.empty:
            values.append(np.nan)
            continue
        known = known.sort_values(
            ["observation_at", "effective_available_at", "vintage"]
        )
        point_in_time = known.groupby("observation_at", as_index=False).tail(1)
        latest = point_in_time.sort_values("observation_at").iloc[-1]
        age_days = (cutoff - latest["observation_at"]).total_seconds() / 86400
        same_day = latest["observation_at"].date() == cutoff.date()
        permitted = age_days <= max_age_days and (
            missing_policy == "asof" or same_day
        )
        values.append(float(latest["value"]) if permitted else np.nan)
    return pd.Series(values, index=cutoffs.index, dtype=float)


def strictly_prior_rows(
    frame: pd.DataFrame, time_column: str, cutoff: pd.Timestamp
) -> pd.DataFrame:
    """Return rows strictly earlier than a walk-forward test cutoff."""
    return frame.loc[frame[time_column] < cutoff].copy()


def validate_label_isolation(
    frame: pd.DataFrame,
    label_columns: tuple[str, ...] = ("outcome",),
) -> None:
    """Reject evaluation labels from a signal-time table."""
    present = sorted(set(label_columns).intersection(frame.columns))
    if present:
        raise DataValidationError(
            f"Signal-time table contains evaluation labels: {', '.join(present)}"
        )
