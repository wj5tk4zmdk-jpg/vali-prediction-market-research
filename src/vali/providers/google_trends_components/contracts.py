"""Typed contracts and safety utilities for Google Trends alpha readiness."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Protocol

import pandas as pd


PROVIDER = "google_trends"
SOURCE = "google_trends_api_alpha"
PUBLIC_CAPABILITY_VERSION = "alpha-public-2025-07"
QUERY_MANIFEST_VERSION = "1"
QUERY_MANIFEST_COLUMNS = {
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
}
ALLOWED_BASKETS = {"easing", "tightening", "control", "stress"}
ALLOWED_QUERY_KINDS = {"term", "topic"}
ALLOWED_AGGREGATIONS = {"daily", "weekly", "monthly", "yearly"}
ALLOWED_STATUSES = {"available", "suppressed", "low_volume", "missing"}
SENSITIVE_KEYS = {
    "api_key",
    "apikey",
    "authorization",
    "credential",
    "credentials",
    "password",
    "secret",
    "token",
}


class TrendsError(RuntimeError):
    """Base error for the Google Trends readiness integration."""


class TrendsDataError(TrendsError):
    """Raised when a query manifest or provider response is unsafe to use."""


class TrendsAccessUnavailable(TrendsError):
    """Raised when live alpha access has not been configured."""


class TrendsTransientError(TrendsError):
    """A retryable provider or transport failure."""


class TrendsRateLimitError(TrendsTransientError):
    """A retryable provider rate-limit response."""


def parse_bool(value: Any, field: str) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes", "y"}:
        return True
    if normalized in {"false", "0", "no", "n"}:
        return False
    raise TrendsDataError(f"Invalid boolean for {field}: {value!r}")


def parse_datetime(value: Any, field: str) -> datetime:
    try:
        parsed = pd.Timestamp(value)
    except Exception as exc:
        raise TrendsDataError(
            f"Invalid timestamp for {field}: {value!r}"
        ) from exc
    if parsed.tzinfo is None:
        raise TrendsDataError(f"{field} must include a timezone")
    return parsed.tz_convert("UTC").to_pydatetime()


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")


def sha256_value(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def redact_sensitive(value: Any) -> Any:
    """Recursively remove credential-like values before persistence."""
    if isinstance(value, Mapping):
        return {
            str(key): (
                "[REDACTED]"
                if str(key).lower() in SENSITIVE_KEYS
                else redact_sensitive(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact_sensitive(item) for item in value]
    return value


@dataclass(frozen=True)
class TrendsQuerySpec:
    manifest_version: str
    query_id: str
    query: str
    query_kind: str
    basket: str
    polarity: int
    active: bool
    required: bool
    rationale: str
    geography: str
    aggregation: str
    candidate_since: str
    freeze_date: str = ""

    @property
    def feature_id(self) -> str:
        return f"google_trends.{self.query_id}"


@dataclass(frozen=True)
class TrendsRequest:
    queries: tuple[TrendsQuerySpec, ...]
    start_date: date
    end_date: date
    geography: str
    aggregation: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "queries": [
                {
                    "query_id": query.query_id,
                    "query": query.query,
                    "query_kind": query.query_kind,
                }
                for query in self.queries
            ],
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "geography": self.geography,
            "aggregation": self.aggregation,
        }


@dataclass(frozen=True)
class TrendsObservation:
    query_id: str
    observation_date: date
    value: float | None
    status: str
    partial: bool = False


@dataclass(frozen=True)
class TrendsGatewayResponse:
    observations: tuple[TrendsObservation, ...]
    retrieved_at: datetime
    request_id: str
    api_version: str
    raw_payload: Mapping[str, Any]


class TrendsGateway(Protocol):
    """Stable boundary for the unpublished official API transport."""

    def fetch(self, request: TrendsRequest) -> TrendsGatewayResponse:
        """Fetch consistently scaled search-interest observations."""


@dataclass
class TrendsRunResult:
    output_dir: Path
    counts: dict[str, int]
    latest_usable_date: str | None
    query_manifest_sha256: str
    live_access_used: bool


__all__ = [
    "ALLOWED_AGGREGATIONS",
    "ALLOWED_BASKETS",
    "ALLOWED_QUERY_KINDS",
    "ALLOWED_STATUSES",
    "PROVIDER",
    "PUBLIC_CAPABILITY_VERSION",
    "QUERY_MANIFEST_COLUMNS",
    "QUERY_MANIFEST_VERSION",
    "SENSITIVE_KEYS",
    "SOURCE",
    "TrendsAccessUnavailable",
    "TrendsDataError",
    "TrendsError",
    "TrendsGateway",
    "TrendsGatewayResponse",
    "TrendsObservation",
    "TrendsQuerySpec",
    "TrendsRateLimitError",
    "TrendsRequest",
    "TrendsRunResult",
    "TrendsTransientError",
    "canonical_bytes",
    "parse_bool",
    "parse_datetime",
    "redact_sensitive",
    "sha256_value",
]
