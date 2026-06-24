"""Google Trends observations, features, exclusions, and merge behavior."""

from __future__ import annotations

from datetime import date, datetime, time as datetime_time, timedelta, timezone
from pathlib import Path
from typing import Any, Sequence

import pandas as pd

from .contracts import (
    SOURCE,
    TrendsDataError,
    TrendsGatewayResponse,
    TrendsQuerySpec,
    sha256_value,
)


def feature_manifest_frame(
    specs: Sequence[TrendsQuerySpec],
) -> pd.DataFrame:
    rows = []
    for spec in specs:
        if not spec.active:
            continue
        rows.append(
            {
                "feature_id": spec.feature_id,
                "rationale": spec.rationale,
                "transformation": "log1p",
                "polarity": spec.polarity,
                "availability_lag_days": 2,
                "missing_policy": "asof",
                "max_age_days": 3,
                "required": spec.required,
                "source": SOURCE,
            }
        )
    return pd.DataFrame(rows).sort_values("feature_id").reset_index(drop=True)


def normalize_response(
    response: TrendsGatewayResponse,
    specs: Sequence[TrendsQuerySpec],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    spec_map = {spec.query_id: spec for spec in specs}
    latest_usable = response.retrieved_at.date() - timedelta(days=2)
    feature_rows: list[dict[str, Any]] = []
    observation_rows: list[dict[str, Any]] = []
    exclusion_rows: list[dict[str, Any]] = []
    seen_observations: set[tuple[str, date]] = set()
    for observation in response.observations:
        observation_key = (
            observation.query_id,
            observation.observation_date,
        )
        if observation_key in seen_observations:
            raise TrendsDataError(
                "Response contains duplicate query/date observations: "
                f"{observation.query_id} {observation.observation_date}"
            )
        seen_observations.add(observation_key)
        spec = spec_map.get(observation.query_id)
        if spec is None:
            raise TrendsDataError(
                "Response contains an unknown query ID: "
                f"{observation.query_id}"
            )
        reason = ""
        if observation.partial:
            reason = "partial_period"
        elif observation.observation_date > latest_usable:
            reason = "newer_than_t_minus_2"
        elif observation.status != "available":
            reason = observation.status
        usable = not reason
        observation_rows.append(
            {
                "query_id": observation.query_id,
                "query": spec.query,
                "basket": spec.basket,
                "active": spec.active,
                "observation_date": observation.observation_date.isoformat(),
                "value": observation.value,
                "status": observation.status,
                "partial": observation.partial,
                "usable": usable,
                "rejection_reason": reason,
                "retrieved_at": response.retrieved_at,
                "request_id": response.request_id,
                "api_version": response.api_version,
            }
        )
        if reason:
            exclusion_rows.append(
                {
                    "query_id": observation.query_id,
                    "observation_date": (
                        observation.observation_date.isoformat()
                    ),
                    "reason": reason,
                    "retrieved_at": response.retrieved_at,
                }
            )
        if not usable or not spec.active:
            continue
        observation_at = datetime.combine(
            observation.observation_date,
            datetime_time.min,
            tzinfo=timezone.utc,
        )
        vintage = sha256_value(
            {
                "query_id": observation.query_id,
                "date": observation.observation_date.isoformat(),
                "value": observation.value,
                "status": observation.status,
                "request_id": response.request_id,
            }
        )[:20]
        feature_rows.append(
            {
                "feature_id": spec.feature_id,
                "observation_at": observation_at,
                "available_at": response.retrieved_at,
                "vintage": vintage,
                "source": SOURCE,
                "value": float(observation.value),
            }
        )
    feature_columns = [
        "feature_id",
        "observation_at",
        "available_at",
        "vintage",
        "source",
        "value",
    ]
    observation_columns = [
        "query_id",
        "query",
        "basket",
        "active",
        "observation_date",
        "value",
        "status",
        "partial",
        "usable",
        "rejection_reason",
        "retrieved_at",
        "request_id",
        "api_version",
    ]
    exclusion_columns = [
        "query_id",
        "observation_date",
        "reason",
        "retrieved_at",
    ]
    features = pd.DataFrame(feature_rows, columns=feature_columns)
    observations = pd.DataFrame(
        observation_rows, columns=observation_columns
    )
    exclusions = pd.DataFrame(exclusion_rows, columns=exclusion_columns)
    return features, observations, exclusions


def read_existing_csv(
    path: Path, columns: Sequence[str]
) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame(columns=columns)
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame(columns=columns)


def merge_features(
    existing: pd.DataFrame, new: pd.DataFrame
) -> pd.DataFrame:
    combined = pd.concat([existing, new], ignore_index=True, sort=False)
    if combined.empty:
        return new.copy()
    combined["observation_at"] = pd.to_datetime(
        combined["observation_at"], utc=True
    )
    combined["available_at"] = pd.to_datetime(
        combined["available_at"], utc=True
    )
    combined["value"] = pd.to_numeric(combined["value"], errors="raise")
    combined = combined.sort_values(
        ["feature_id", "observation_at", "available_at", "vintage"]
    )
    return combined.drop_duplicates(
        ["feature_id", "observation_at", "value", "vintage"],
        keep="first",
    ).reset_index(drop=True)


def merge_observations(
    existing: pd.DataFrame, new: pd.DataFrame
) -> pd.DataFrame:
    combined = pd.concat([existing, new], ignore_index=True, sort=False)
    if combined.empty:
        return new.copy()
    combined["retrieved_at"] = pd.to_datetime(
        combined["retrieved_at"], utc=True
    )
    keys = [
        "query_id",
        "observation_date",
        "retrieved_at",
        "request_id",
        "status",
    ]
    return (
        combined.sort_values(keys)
        .drop_duplicates(keys, keep="last")
        .reset_index(drop=True)
    )


__all__ = [
    "feature_manifest_frame",
    "merge_features",
    "merge_observations",
    "normalize_response",
    "read_existing_csv",
]
