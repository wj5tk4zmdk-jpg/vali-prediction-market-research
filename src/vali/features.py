"""Point-in-time feature transformation and attention index construction."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import FeatureConfig
from .domain.attention import (
    compose_attention,
    frozen_equal_weight,
    transform_feature,
)
from .domain.divergence import rolling_prior_zscore as _rolling_prior_zscore
from .data.point_in_time import asof_feature_values
from .data.validation import validate_frozen_feature_manifest


def rolling_prior_zscore(series: pd.Series, window: int, min_periods: int) -> pd.Series:
    """Standardize against prior observations only; the current value is excluded."""
    return _rolling_prior_zscore(series, window, min_periods)


def _transform(series: pd.Series, name: str) -> pd.Series:
    return transform_feature(series, name)


def _asof_values(
    feature_rows: pd.DataFrame,
    cutoffs: pd.Series,
    availability_lag_days: int,
    missing_policy: str,
    max_age_days: int,
) -> pd.Series:
    return asof_feature_values(
        feature_rows,
        cutoffs,
        availability_lag_days,
        missing_policy,
        max_age_days,
    )


def build_attention_index(
    features: pd.DataFrame,
    manifest: pd.DataFrame,
    cutoff_times: pd.Series | pd.DatetimeIndex,
    config: FeatureConfig,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return daily A and a long-form feature audit table."""
    validate_frozen_feature_manifest(features, manifest)
    cutoffs = pd.Series(pd.DatetimeIndex(cutoff_times).unique()).sort_values().reset_index(drop=True)
    wide_z: dict[str, pd.Series] = {}
    audit_rows: list[pd.DataFrame] = []
    required: list[str] = []

    for spec in manifest.itertuples(index=False):
        rows = features.loc[features["feature_id"] == spec.feature_id]
        raw = _asof_values(
            rows,
            cutoffs,
            int(spec.availability_lag_days),
            str(spec.missing_policy),
            int(spec.max_age_days),
        )
        transformed = _transform(raw, str(spec.transformation)) * int(spec.polarity)
        zscore = rolling_prior_zscore(
            transformed,
            window=config.standardization_window,
            min_periods=config.min_periods,
        )
        wide_z[str(spec.feature_id)] = zscore
        if bool(spec.required):
            required.append(str(spec.feature_id))
        audit_rows.append(
            pd.DataFrame(
                {
                    "cutoff_at": cutoffs,
                    "feature_id": spec.feature_id,
                    "raw_value": raw,
                    "transformed_value": transformed,
                    "z_value": zscore,
                    "required": bool(spec.required),
                    "available_for_signal": zscore.notna(),
                }
            )
        )

    zframe = pd.DataFrame(wide_z)
    (
        attention,
        active_count,
        required_complete,
        composition_complete,
        rejection_reason,
    ) = compose_attention(
        zframe,
        required,
        config.optional_feature_policy,
    )
    output = pd.DataFrame(
        {
            "cutoff_at": cutoffs,
            "attention": attention,
            "active_features": active_count,
            "required_complete": required_complete,
            "composition_complete": composition_complete,
            "manifest_features": len(zframe.columns),
            "feature_composition_policy": config.optional_feature_policy,
            "attention_rejection_reason": rejection_reason,
        }
    )
    audit = pd.concat(audit_rows, ignore_index=True) if audit_rows else pd.DataFrame()
    audit["missing_for_signal"] = ~audit["available_for_signal"]
    audit["frozen_weight"] = frozen_equal_weight(len(zframe.columns))
    audit["feature_composition_policy"] = config.optional_feature_policy
    return output, audit
