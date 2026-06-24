"""Frozen Google Trends query-manifest validation and request planning."""

from __future__ import annotations

from dataclasses import asdict
from datetime import date, timedelta
from importlib.resources import files
import json
from pathlib import Path
from typing import Sequence

import pandas as pd

from .contracts import (
    ALLOWED_AGGREGATIONS,
    ALLOWED_BASKETS,
    ALLOWED_QUERY_KINDS,
    PROVIDER,
    PUBLIC_CAPABILITY_VERSION,
    QUERY_MANIFEST_COLUMNS,
    QUERY_MANIFEST_VERSION,
    TrendsDataError,
    TrendsQuerySpec,
    TrendsRequest,
    parse_bool,
    sha256_value,
)


def default_query_manifest_path() -> Path:
    return Path(
        str(
            files("vali").joinpath(
                "data/google_trends_query_manifest.v1.csv"
            )
        )
    )


def load_query_manifest(
    path: str | Path | None = None,
) -> tuple[TrendsQuerySpec, ...]:
    source = Path(path) if path is not None else default_query_manifest_path()
    if not source.exists():
        raise TrendsDataError(
            f"Google Trends query manifest does not exist: {source}"
        )
    frame = pd.read_csv(source, dtype=str, keep_default_na=False)
    missing = sorted(QUERY_MANIFEST_COLUMNS.difference(frame.columns))
    if missing:
        raise TrendsDataError(
            "Google Trends query manifest is missing columns: "
            f"{', '.join(missing)}"
        )
    specs: list[TrendsQuerySpec] = []
    for row in frame.itertuples(index=False):
        try:
            polarity = int(row.polarity)
        except (TypeError, ValueError) as exc:
            raise TrendsDataError(
                f"Invalid polarity for query {row.query_id!r}"
            ) from exc
        specs.append(
            TrendsQuerySpec(
                manifest_version=str(row.manifest_version).strip(),
                query_id=str(row.query_id).strip(),
                query=str(row.query).strip(),
                query_kind=str(row.query_kind).strip(),
                basket=str(row.basket).strip(),
                polarity=polarity,
                active=parse_bool(row.active, f"{row.query_id}.active"),
                required=parse_bool(
                    row.required, f"{row.query_id}.required"
                ),
                rationale=str(row.rationale).strip(),
                geography=str(row.geography).strip(),
                aggregation=str(row.aggregation).strip(),
                candidate_since=str(row.candidate_since).strip(),
                freeze_date=str(row.freeze_date).strip(),
            )
        )
    validate_query_manifest(specs)
    return tuple(specs)


def validate_query_manifest(specs: Sequence[TrendsQuerySpec]) -> None:
    if not specs:
        raise TrendsDataError("Google Trends query manifest is empty")
    versions = {spec.manifest_version for spec in specs}
    if len(versions) != 1 or "" in versions:
        raise TrendsDataError(
            "Query manifest must contain one non-empty version"
        )
    if versions != {QUERY_MANIFEST_VERSION}:
        raise TrendsDataError(
            "Unsupported Google Trends query manifest version: "
            f"{sorted(versions)}"
        )
    identifiers = [spec.query_id for spec in specs]
    if any(not identifier for identifier in identifiers) or len(
        identifiers
    ) != len(set(identifiers)):
        raise TrendsDataError("Query IDs must be non-empty and unique")
    normalized_queries = [spec.query.casefold() for spec in specs]
    if any(not spec.query for spec in specs) or len(
        normalized_queries
    ) != len(set(normalized_queries)):
        raise TrendsDataError("Query text must be non-empty and unique")
    for spec in specs:
        if spec.query_kind not in ALLOWED_QUERY_KINDS:
            raise TrendsDataError(
                f"Unsupported query kind for {spec.query_id}: "
                f"{spec.query_kind}"
            )
        if spec.basket not in ALLOWED_BASKETS:
            raise TrendsDataError(
                f"Unsupported basket for {spec.query_id}: {spec.basket}"
            )
        if spec.aggregation not in ALLOWED_AGGREGATIONS:
            raise TrendsDataError(
                f"Unsupported aggregation for {spec.query_id}: "
                f"{spec.aggregation}"
            )
        if not spec.geography or not spec.rationale or not spec.candidate_since:
            raise TrendsDataError(
                f"Query {spec.query_id} has incomplete metadata"
            )
        expected = {
            "easing": 1,
            "tightening": -1,
            "control": 0,
            "stress": 1,
        }[spec.basket]
        if spec.polarity != expected:
            raise TrendsDataError(
                f"Query {spec.query_id} in {spec.basket} basket must have "
                f"polarity {expected}"
            )
        if spec.active and spec.basket not in {"easing", "tightening"}:
            raise TrendsDataError(
                "Only easing and tightening queries may be active initially"
            )
        if spec.active and not spec.required:
            raise TrendsDataError(
                f"Active query {spec.query_id} must be required"
            )
    active_easing = sum(
        spec.active and spec.basket == "easing" for spec in specs
    )
    active_tightening = sum(
        spec.active and spec.basket == "tightening" for spec in specs
    )
    if active_easing == 0 or active_easing != active_tightening:
        raise TrendsDataError(
            "Active easing and tightening baskets must be non-empty and balanced"
        )


def query_manifest_sha256(specs: Sequence[TrendsQuerySpec]) -> str:
    return sha256_value(
        [asdict(spec) for spec in sorted(specs, key=lambda item: item.query_id)]
    )


def query_manifest_frame(
    specs: Sequence[TrendsQuerySpec],
) -> pd.DataFrame:
    columns = [
        "manifest_version",
        "query_id",
        "query",
        "query_kind",
        "basket",
        "polarity",
        "active",
        "required",
        "rationale",
        "geography",
        "aggregation",
        "candidate_since",
        "freeze_date",
    ]
    return pd.DataFrame(
        [asdict(spec) for spec in specs], columns=columns
    ).sort_values("query_id")


def build_request_plan(
    specs: Sequence[TrendsQuerySpec], start_date: date, end_date: date
) -> tuple[TrendsRequest, ...]:
    validate_query_manifest(specs)
    if end_date < start_date:
        raise TrendsDataError(
            "Google Trends request end date precedes start date"
        )
    if (end_date - start_date).days + 1 > 1800:
        raise TrendsDataError(
            "Google Trends public alpha is limited to a rolling 1,800-day window"
        )
    groups: dict[tuple[str, str], list[TrendsQuerySpec]] = {}
    for spec in specs:
        groups.setdefault((spec.geography, spec.aggregation), []).append(spec)
    return tuple(
        TrendsRequest(
            queries=tuple(sorted(group, key=lambda item: item.query_id)),
            start_date=start_date,
            end_date=end_date,
            geography=geography,
            aggregation=aggregation,
        )
        for (geography, aggregation), group in sorted(groups.items())
    )


def write_request_plan(
    output_dir: str | Path,
    specs: Sequence[TrendsQuerySpec],
    *,
    as_of: date,
    days: int = 1800,
) -> Path:
    if not 1 <= days <= 1800:
        raise TrendsDataError("Trends plan days must be in [1, 1800]")
    end_date = as_of - timedelta(days=2)
    start_date = end_date - timedelta(days=days - 1)
    requests = build_request_plan(specs, start_date, end_date)
    target = Path(output_dir).resolve()
    target.mkdir(parents=True, exist_ok=True)
    query_manifest_frame(specs).to_csv(
        target / "query_manifest.csv", index=False
    )
    payload = {
        "provider": PROVIDER,
        "mode": "official_api_alpha_readiness",
        "public_capability_version": PUBLIC_CAPABILITY_VERSION,
        "as_of": as_of.isoformat(),
        "latest_requested_date": end_date.isoformat(),
        "days": days,
        "query_manifest_sha256": query_manifest_sha256(specs),
        "query_set_frozen": all(
            spec.freeze_date for spec in specs if spec.active
        ),
        "requests": [request.as_dict() for request in requests],
        "live_access_required": True,
        "unofficial_fallbacks_allowed": False,
    }
    path = target / "request_plan.json"
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
    )
    return path


__all__ = [
    "build_request_plan",
    "default_query_manifest_path",
    "load_query_manifest",
    "query_manifest_frame",
    "query_manifest_sha256",
    "validate_query_manifest",
    "write_request_plan",
]
