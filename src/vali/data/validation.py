"""VALI input, manifest, provenance, and internal-event validation."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .contracts import (
    EVENT_COLUMNS,
    EVENT_IDENTITY_FIELDS,
    FEATURE_COLUMNS,
    MANIFEST_COLUMNS,
    QUOTE_COLUMNS,
    TRADE_COLUMNS,
    DataValidationError,
    InputBundle,
    ValidationSummary,
)
from .point_in_time import parse_utc
from .provenance import validate_public_input_boundary


def require_columns(frame: pd.DataFrame, required: set[str], label: str) -> None:
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise DataValidationError(f"{label} is missing columns: {', '.join(missing)}")


def reject_duplicates(frame: pd.DataFrame, keys: list[str], label: str) -> None:
    duplicated = frame.duplicated(keys, keep=False)
    if duplicated.any():
        sample = frame.loc[duplicated, keys].head(3).to_dict("records")
        raise DataValidationError(f"{label} contains duplicate keys {keys}: {sample}")


def parse_manifest_bool(value) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes", "y"}:
        return True
    if normalized in {"false", "0", "no", "n"}:
        return False
    raise DataValidationError(f"Invalid boolean value in feature manifest: {value!r}")


def validate_frozen_feature_manifest(
    features: pd.DataFrame,
    manifest: pd.DataFrame,
) -> None:
    """Reject missing manifests and observations outside the frozen universe."""
    if manifest.empty:
        raise ValueError("A frozen feature manifest is required")
    unfrozen_features = sorted(
        set(features["feature_id"]).difference(set(manifest["feature_id"]))
    )
    if unfrozen_features:
        raise ValueError(
            f"Features outside the frozen manifest are prohibited: {unfrozen_features[:5]}"
        )


def validate_event_identity(
    events: pd.DataFrame, related: pd.DataFrame | None = None
) -> None:
    """Enforce one stable internal EASING event for every represented meeting."""
    missing = sorted(EVENT_IDENTITY_FIELDS.difference(events.columns))
    if missing:
        raise DataValidationError(
            f"Event identity validation is missing columns: {', '.join(missing)}"
        )
    if events.empty:
        raise DataValidationError(
            "Event identity validation found a missing internal EASING event"
        )

    type_column = next(
        (
            column
            for column in ("internal_event_type", "event_type", "contract_type")
            if column in events.columns
        ),
        None,
    )
    event_types = (
        events[type_column].fillna("").astype(str).str.strip().str.upper()
        if type_column
        else pd.Series("EASING", index=events.index)
    )
    meeting_dates = pd.to_datetime(
        events["meeting_at"], utc=True, errors="raise"
    ).dt.date
    easing = events.loc[event_types == "EASING"].copy()
    easing_dates = meeting_dates.loc[event_types == "EASING"]
    missing_dates = sorted(set(meeting_dates).difference(set(easing_dates)))
    if easing.empty or missing_dates:
        detail = f" for meeting dates {missing_dates[:5]}" if missing_dates else ""
        raise DataValidationError(
            f"Event identity has a missing internal EASING event{detail}"
        )
    duplicated = easing_dates.duplicated(keep=False)
    if duplicated.any():
        duplicate_dates = sorted(set(easing_dates.loc[duplicated]))
        raise DataValidationError(
            "Event identity contains duplicate internal EASING events for "
            f"meeting dates {duplicate_dates[:5]}"
        )
    if events["event_id"].isna().any() or events["contract_id"].isna().any():
        raise DataValidationError("Internal EASING event identifiers cannot be missing")

    if related is None or related.empty:
        return
    if "contract_id" not in related:
        raise DataValidationError("Related research table is missing contract_id")
    expected = events.set_index("contract_id")["event_id"]
    unknown = sorted(set(related["contract_id"]).difference(expected.index))
    if unknown:
        raise DataValidationError(
            f"Related research table references unknown event contracts: {unknown[:5]}"
        )
    if "event_id" in related:
        expected_ids = related["contract_id"].map(expected)
        mismatched = related["event_id"].astype(str) != expected_ids.astype(str)
        if mismatched.any():
            raise DataValidationError(
                "Related research table contains an event identity mismatch"
            )


def validate_feature_manifest(
    features: pd.DataFrame,
    manifest: pd.DataFrame,
) -> None:
    """Validate frozen feature membership, transformations, and provenance."""
    manifest["polarity"] = pd.to_numeric(manifest["polarity"], errors="coerce")
    manifest["availability_lag_days"] = pd.to_numeric(
        manifest["availability_lag_days"], errors="coerce"
    )
    manifest["max_age_days"] = pd.to_numeric(
        manifest["max_age_days"], errors="coerce"
    )
    manifest["required"] = manifest["required"].map(parse_manifest_bool)
    if not manifest["polarity"].isin([-1, 1]).all():
        raise DataValidationError("feature polarity must be -1 or 1")
    if (manifest[["availability_lag_days", "max_age_days"]] < 0).any().any():
        raise DataValidationError(
            "feature availability lag and max age cannot be negative"
        )
    allowed_transforms = {"level", "diff", "pct_change", "log_diff", "log1p"}
    if not manifest["transformation"].isin(allowed_transforms).all():
        raise DataValidationError(
            f"feature transformations must be one of {sorted(allowed_transforms)}"
        )
    if not manifest["missing_policy"].isin({"reject", "asof"}).all():
        raise DataValidationError("feature missing_policy must be reject or asof")
    missing_manifest = sorted(
        set(features["feature_id"]).difference(manifest["feature_id"])
    )
    if missing_manifest:
        raise DataValidationError(
            f"features are absent from the manifest: {missing_manifest[:5]}"
        )
    missing_data = sorted(
        set(manifest.loc[manifest["required"], "feature_id"]).difference(
            features["feature_id"]
        )
    )
    if missing_data:
        raise DataValidationError(
            f"required manifest features have no observations: {missing_data[:5]}"
        )
    source_map = manifest.set_index("feature_id")["source"].astype(str)
    expected_sources = features["feature_id"].map(source_map)
    if (features["source"].astype(str) != expected_sources).any():
        raise DataValidationError(
            "features.source must match the frozen manifest source"
        )


def validate_frames(
    events: pd.DataFrame,
    quotes: pd.DataFrame,
    features: pd.DataFrame,
    manifest: pd.DataFrame,
    trades: pd.DataFrame | None = None,
) -> InputBundle:
    events = events.copy()
    quotes = quotes.copy()
    features = features.copy()
    manifest = manifest.copy()
    trades = trades.copy() if trades is not None else None

    require_columns(events, EVENT_COLUMNS, "events")
    require_columns(quotes, QUOTE_COLUMNS, "quotes")
    require_columns(features, FEATURE_COLUMNS, "features")
    require_columns(manifest, MANIFEST_COLUMNS, "feature_manifest")
    if trades is not None:
        require_columns(trades, TRADE_COLUMNS, "trades")

    validate_public_input_boundary(
        events=events,
        quotes=quotes,
        features=features,
        feature_manifest=manifest,
        trades=trades,
    )

    parse_utc(events, ["open_at", "meeting_at", "settlement_at"], "events")
    parse_utc(quotes, ["observed_at"], "quotes")
    parse_utc(features, ["observation_at", "available_at"], "features")
    if trades is not None:
        parse_utc(trades, ["observed_at"], "trades")

    reject_duplicates(events, ["event_id"], "events")
    reject_duplicates(events, ["contract_id"], "events")
    reject_duplicates(quotes, ["contract_id", "observed_at"], "quotes")
    reject_duplicates(
        features,
        ["feature_id", "observation_at", "available_at", "vintage"],
        "features",
    )
    reject_duplicates(manifest, ["feature_id"], "feature_manifest")
    if trades is not None:
        reject_duplicates(trades, ["trade_id"], "trades")

    validate_event_identity(events)

    if not (
        (events["open_at"] < events["meeting_at"])
        & (events["meeting_at"] <= events["settlement_at"])
    ).all():
        raise DataValidationError(
            "Every event must satisfy open_at < meeting_at <= settlement_at"
        )
    outcomes = pd.to_numeric(events["outcome"], errors="coerce")
    invalid_outcome = outcomes.notna() & ~outcomes.isin([0, 1])
    if invalid_outcome.any():
        raise DataValidationError("events.outcome must be 0, 1, or blank")
    events["outcome"] = outcomes

    numeric_quote = ["bid", "ask", "last", "volume", "bid_depth", "ask_depth"]
    quotes[numeric_quote] = quotes[numeric_quote].apply(pd.to_numeric, errors="coerce")
    if quotes[["bid", "ask"]].isna().any().any():
        raise DataValidationError("quotes.bid and quotes.ask must be numeric")
    if not (quotes["bid"].between(0, 1) & quotes["ask"].between(0, 1)).all():
        raise DataValidationError("quote probabilities must lie in [0, 1]")
    if (quotes["bid"] > quotes["ask"]).any():
        raise DataValidationError("quote bid cannot exceed ask")
    if (quotes[["volume", "bid_depth", "ask_depth"]].fillna(0) < 0).any().any():
        raise DataValidationError("quote volume and depths cannot be negative")
    if "depth_observed" not in quotes:
        quotes["depth_observed"] = quotes[["bid_depth", "ask_depth"]].notna().all(axis=1)
    quotes["depth_observed"] = quotes["depth_observed"].map(parse_manifest_bool)

    known_contracts = set(events["contract_id"])
    unknown_quotes = sorted(set(quotes["contract_id"]).difference(known_contracts))
    if unknown_quotes:
        raise DataValidationError(
            f"quotes reference unknown contracts: {unknown_quotes[:5]}"
        )
    settlement_map = events.set_index("contract_id")["settlement_at"]
    quote_settlement = quotes["contract_id"].map(settlement_map)
    if (quotes["observed_at"] > quote_settlement).any():
        raise DataValidationError("quotes contain post-settlement observations")

    features["value"] = pd.to_numeric(features["value"], errors="coerce")
    if features["value"].isna().any() or not np.isfinite(features["value"]).all():
        raise DataValidationError("features.value must contain finite numeric values")
    if (features["available_at"] < features["observation_at"]).any():
        raise DataValidationError(
            "feature availability cannot precede observation time"
        )

    validate_feature_manifest(features, manifest)

    if trades is not None:
        trades[["price", "size"]] = trades[["price", "size"]].apply(
            pd.to_numeric, errors="coerce"
        )
        if trades[["price", "size"]].isna().any().any():
            raise DataValidationError("trades.price and trades.size must be numeric")
        if not trades["price"].between(0, 1).all() or (trades["size"] <= 0).any():
            raise DataValidationError(
                "trade price must be in [0, 1] and size must be positive"
            )
        if not set(trades["contract_id"]).issubset(known_contracts):
            raise DataValidationError("trades reference unknown contracts")
        trade_settlement = trades["contract_id"].map(settlement_map)
        if (trades["observed_at"] > trade_settlement).any():
            raise DataValidationError("trades contain post-settlement observations")

    summary = ValidationSummary(
        rows={
            "events": len(events),
            "quotes": len(quotes),
            "features": len(features),
            "feature_manifest": len(manifest),
            "trades": 0 if trades is None else len(trades),
        },
        unresolved_events=int(events["outcome"].isna().sum()),
    )
    if summary.unresolved_events:
        summary.warnings.append(
            "Unresolved events are allowed for signal generation but are "
            "excluded from walk-forward training and scoring."
        )
    return InputBundle(events, quotes, features, manifest, trades, summary)
