"""Google Trends API alpha readiness components.

The public alpha documentation does not publish a wire protocol.  This module
therefore keeps the official HTTP transport behind a small gateway interface
and implements everything else: query contracts, fixture ingestion, immutable
archives, normalization, status reporting, and deterministic request plans.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, time as datetime_time, timedelta, timezone
import gzip
import hashlib
from importlib.resources import files
import json
import math
from pathlib import Path
import time
from typing import Any, Callable, Mapping, Protocol, Sequence

import pandas as pd

from ..reporting import write_dataframe


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


def _parse_bool(value: Any, field: str) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes", "y"}:
        return True
    if normalized in {"false", "0", "no", "n"}:
        return False
    raise TrendsDataError(f"Invalid boolean for {field}: {value!r}")


def _parse_datetime(value: Any, field: str) -> datetime:
    try:
        parsed = pd.Timestamp(value)
    except Exception as exc:
        raise TrendsDataError(f"Invalid timestamp for {field}: {value!r}") from exc
    if parsed.tzinfo is None:
        raise TrendsDataError(f"{field} must include a timezone")
    return parsed.tz_convert("UTC").to_pydatetime()


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def redact_sensitive(value: Any) -> Any:
    """Recursively remove credential-like values before persistence or logging."""
    if isinstance(value, Mapping):
        return {
            str(key): "[REDACTED]" if str(key).lower() in SENSITIVE_KEYS else redact_sensitive(item)
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
                {"query_id": query.query_id, "query": query.query, "query_kind": query.query_kind}
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


def default_query_manifest_path() -> Path:
    return Path(str(files("vali").joinpath("data/google_trends_query_manifest.v1.csv")))


def load_query_manifest(path: str | Path | None = None) -> tuple[TrendsQuerySpec, ...]:
    source = Path(path) if path is not None else default_query_manifest_path()
    if not source.exists():
        raise TrendsDataError(f"Google Trends query manifest does not exist: {source}")
    frame = pd.read_csv(source, dtype=str, keep_default_na=False)
    missing = sorted(QUERY_MANIFEST_COLUMNS.difference(frame.columns))
    if missing:
        raise TrendsDataError(f"Google Trends query manifest is missing columns: {', '.join(missing)}")
    specs: list[TrendsQuerySpec] = []
    for row in frame.itertuples(index=False):
        try:
            polarity = int(row.polarity)
        except (TypeError, ValueError) as exc:
            raise TrendsDataError(f"Invalid polarity for query {row.query_id!r}") from exc
        specs.append(
            TrendsQuerySpec(
                manifest_version=str(row.manifest_version).strip(),
                query_id=str(row.query_id).strip(),
                query=str(row.query).strip(),
                query_kind=str(row.query_kind).strip(),
                basket=str(row.basket).strip(),
                polarity=polarity,
                active=_parse_bool(row.active, f"{row.query_id}.active"),
                required=_parse_bool(row.required, f"{row.query_id}.required"),
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
        raise TrendsDataError("Query manifest must contain one non-empty version")
    if versions != {QUERY_MANIFEST_VERSION}:
        raise TrendsDataError(
            f"Unsupported Google Trends query manifest version: {sorted(versions)}"
        )
    identifiers = [spec.query_id for spec in specs]
    if any(not identifier for identifier in identifiers) or len(identifiers) != len(set(identifiers)):
        raise TrendsDataError("Query IDs must be non-empty and unique")
    normalized_queries = [spec.query.casefold() for spec in specs]
    if any(not spec.query for spec in specs) or len(normalized_queries) != len(set(normalized_queries)):
        raise TrendsDataError("Query text must be non-empty and unique")
    for spec in specs:
        if spec.query_kind not in ALLOWED_QUERY_KINDS:
            raise TrendsDataError(f"Unsupported query kind for {spec.query_id}: {spec.query_kind}")
        if spec.basket not in ALLOWED_BASKETS:
            raise TrendsDataError(f"Unsupported basket for {spec.query_id}: {spec.basket}")
        if spec.aggregation not in ALLOWED_AGGREGATIONS:
            raise TrendsDataError(f"Unsupported aggregation for {spec.query_id}: {spec.aggregation}")
        if not spec.geography or not spec.rationale or not spec.candidate_since:
            raise TrendsDataError(f"Query {spec.query_id} has incomplete metadata")
        expected = {"easing": 1, "tightening": -1, "control": 0, "stress": 1}[spec.basket]
        if spec.polarity != expected:
            raise TrendsDataError(
                f"Query {spec.query_id} in {spec.basket} basket must have polarity {expected}"
            )
        if spec.active and spec.basket not in {"easing", "tightening"}:
            raise TrendsDataError("Only easing and tightening queries may be active initially")
        if spec.active and not spec.required:
            raise TrendsDataError(f"Active query {spec.query_id} must be required")
    active_easing = sum(spec.active and spec.basket == "easing" for spec in specs)
    active_tightening = sum(spec.active and spec.basket == "tightening" for spec in specs)
    if active_easing == 0 or active_easing != active_tightening:
        raise TrendsDataError("Active easing and tightening baskets must be non-empty and balanced")


def query_manifest_sha256(specs: Sequence[TrendsQuerySpec]) -> str:
    return _sha256([asdict(spec) for spec in sorted(specs, key=lambda item: item.query_id)])


def query_manifest_frame(specs: Sequence[TrendsQuerySpec]) -> pd.DataFrame:
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
    return pd.DataFrame([asdict(spec) for spec in specs], columns=columns).sort_values("query_id")


def build_request_plan(
    specs: Sequence[TrendsQuerySpec], start_date: date, end_date: date
) -> tuple[TrendsRequest, ...]:
    validate_query_manifest(specs)
    if end_date < start_date:
        raise TrendsDataError("Google Trends request end date precedes start date")
    if (end_date - start_date).days + 1 > 1800:
        raise TrendsDataError("Google Trends public alpha is limited to a rolling 1,800-day window")
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
    query_manifest_frame(specs).to_csv(target / "query_manifest.csv", index=False)
    payload = {
        "provider": PROVIDER,
        "mode": "official_api_alpha_readiness",
        "public_capability_version": PUBLIC_CAPABILITY_VERSION,
        "as_of": as_of.isoformat(),
        "latest_requested_date": end_date.isoformat(),
        "days": days,
        "query_manifest_sha256": query_manifest_sha256(specs),
        "query_set_frozen": all(spec.freeze_date for spec in specs if spec.active),
        "requests": [request.as_dict() for request in requests],
        "live_access_required": True,
        "unofficial_fallbacks_allowed": False,
    }
    path = target / "request_plan.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


class FixtureTrendsGateway:
    """Offline provider used for contract tests and clean-environment exercises."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def fetch(self, request: TrendsRequest) -> TrendsGatewayResponse:
        if not self.path.exists():
            raise TrendsDataError(f"Google Trends fixture does not exist: {self.path}")
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            raise TrendsDataError(f"Invalid Google Trends fixture: {self.path}") from exc
        retrieved = _parse_datetime(payload.get("retrieved_at"), "fixture.retrieved_at")
        allowed_queries = {query.query_id for query in request.queries}
        observations: list[TrendsObservation] = []
        raw_rows: list[dict[str, Any]] = []
        for row in payload.get("observations", []):
            query_id = str(row.get("query_id", ""))
            try:
                observation_date = date.fromisoformat(str(row.get("date", "")))
            except ValueError as exc:
                raise TrendsDataError(f"Invalid fixture observation date: {row.get('date')!r}") from exc
            if (
                query_id not in allowed_queries
                or observation_date < request.start_date
                or observation_date > request.end_date
            ):
                continue
            status = str(row.get("status", "available"))
            if status not in ALLOWED_STATUSES:
                raise TrendsDataError(f"Unsupported fixture status: {status}")
            raw_value = row.get("value")
            value = None if raw_value in (None, "") else float(raw_value)
            if status == "available" and (
                value is None or not math.isfinite(value) or value < 0
            ):
                raise TrendsDataError("Available Trends observations require finite non-negative values")
            if status != "available" and value is not None:
                raise TrendsDataError("Suppressed, low-volume, or missing observations cannot carry a value")
            observation = TrendsObservation(
                query_id=query_id,
                observation_date=observation_date,
                value=value,
                status=status,
                partial=_parse_bool(row.get("partial", False), "observation.partial"),
            )
            observations.append(observation)
            raw_rows.append(dict(row))
        filtered_payload = {
            "fixture_schema": payload.get("fixture_schema", "vali-google-trends-fixture-v1"),
            "api_version": payload.get("api_version", "fixture-v1"),
            "retrieved_at": retrieved.isoformat(),
            "request_id": payload.get("request_id", _sha256(request.as_dict())[:16]),
            "observations": raw_rows,
        }
        return TrendsGatewayResponse(
            observations=tuple(observations),
            retrieved_at=retrieved,
            request_id=str(filtered_payload["request_id"]),
            api_version=str(filtered_payload["api_version"]),
            raw_payload=filtered_payload,
        )


class UnavailableOfficialTrendsGateway:
    """Explicit gate used until Google supplies the private alpha protocol."""

    def fetch(self, request: TrendsRequest) -> TrendsGatewayResponse:
        raise TrendsAccessUnavailable(
            "Official Google Trends API alpha access is not configured. "
            "Use --fixture for offline validation; no scraping fallback is permitted."
        )


class RetryingTrendsGateway:
    """Protocol-independent exponential retry wrapper for rate limits and 5xx failures."""

    def __init__(
        self,
        gateway: TrendsGateway,
        *,
        max_retries: int = 5,
        sleeper: Callable[[float], None] = time.sleep,
    ):
        if max_retries < 0:
            raise TrendsDataError("max_retries cannot be negative")
        self.gateway = gateway
        self.max_retries = max_retries
        self.sleeper = sleeper

    def fetch(self, request: TrendsRequest) -> TrendsGatewayResponse:
        for attempt in range(self.max_retries + 1):
            try:
                return self.gateway.fetch(request)
            except TrendsTransientError:
                if attempt >= self.max_retries:
                    raise
                self.sleeper(min(0.5 * (2**attempt), 8.0))
        raise AssertionError("unreachable")


class TrendsArchiveStore:
    """Content-addressed archive with mandatory request and credential redaction."""

    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()

    def record(
        self,
        *,
        request: TrendsRequest,
        response: TrendsGatewayResponse,
        manifest_hash: str,
    ) -> Path:
        safe_request = redact_sensitive(request.as_dict())
        safe_payload = redact_sensitive(response.raw_payload)
        archive_content = {
            "request": safe_request,
            "payload": safe_payload,
            "api_version": response.api_version,
        }
        digest = _sha256(archive_content)
        directory = self.root / "raw" / PROVIDER / response.retrieved_at.strftime("%Y/%m/%d")
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{digest}.json.gz"
        if path.exists():
            return path
        envelope = {
            "provider": PROVIDER,
            "api_version": response.api_version,
            "content_sha256": digest,
            "query_manifest_sha256": manifest_hash,
            "request_id": response.request_id,
            "retrieved_at": response.retrieved_at.isoformat(),
            "request": safe_request,
            "payload": safe_payload,
        }
        temporary = path.with_suffix(".tmp")
        with gzip.open(temporary, "wt", encoding="utf-8") as handle:
            json.dump(envelope, handle, sort_keys=True, separators=(",", ":"))
        temporary.replace(path)
        return path


def feature_manifest_frame(specs: Sequence[TrendsQuerySpec]) -> pd.DataFrame:
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
        observation_key = (observation.query_id, observation.observation_date)
        if observation_key in seen_observations:
            raise TrendsDataError(
                "Response contains duplicate query/date observations: "
                f"{observation.query_id} {observation.observation_date}"
            )
        seen_observations.add(observation_key)
        spec = spec_map.get(observation.query_id)
        if spec is None:
            raise TrendsDataError(f"Response contains an unknown query ID: {observation.query_id}")
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
                    "observation_date": observation.observation_date.isoformat(),
                    "reason": reason,
                    "retrieved_at": response.retrieved_at,
                }
            )
        if not usable or not spec.active:
            continue
        # The provider labels daily periods by date. Represent that label at
        # period start so the explicit two-day manifest lag and the actual
        # retrieval timestamp combine without adding an accidental third day.
        observation_at = datetime.combine(
            observation.observation_date, datetime_time.min, tzinfo=timezone.utc
        )
        vintage = _sha256(
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
    exclusion_columns = ["query_id", "observation_date", "reason", "retrieved_at"]
    features = pd.DataFrame(feature_rows, columns=feature_columns)
    observations = pd.DataFrame(observation_rows, columns=observation_columns)
    exclusions = pd.DataFrame(exclusion_rows, columns=exclusion_columns)
    return features, observations, exclusions


def _read_existing_csv(path: Path, columns: Sequence[str]) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame(columns=columns)
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame(columns=columns)


def _merge_features(existing: pd.DataFrame, new: pd.DataFrame) -> pd.DataFrame:
    combined = pd.concat([existing, new], ignore_index=True, sort=False)
    if combined.empty:
        return new.copy()
    combined["observation_at"] = pd.to_datetime(combined["observation_at"], utc=True)
    combined["available_at"] = pd.to_datetime(combined["available_at"], utc=True)
    combined["value"] = pd.to_numeric(combined["value"], errors="raise")
    combined = combined.sort_values(["feature_id", "observation_at", "available_at", "vintage"])
    return combined.drop_duplicates(
        ["feature_id", "observation_at", "value", "vintage"], keep="first"
    ).reset_index(drop=True)


def _merge_observations(existing: pd.DataFrame, new: pd.DataFrame) -> pd.DataFrame:
    combined = pd.concat([existing, new], ignore_index=True, sort=False)
    if combined.empty:
        return new.copy()
    combined["retrieved_at"] = pd.to_datetime(combined["retrieved_at"], utc=True)
    keys = ["query_id", "observation_date", "retrieved_at", "request_id", "status"]
    return combined.sort_values(keys).drop_duplicates(keys, keep="last").reset_index(drop=True)


class TrendsAdapter:
    """Offline-complete adapter around the official API gateway boundary."""

    def __init__(
        self,
        gateway: TrendsGateway,
        output_root: str | Path,
        *,
        archive: TrendsArchiveStore | None = None,
        live_access_used: bool = False,
    ):
        self.gateway = gateway
        self.output_root = Path(output_root).resolve()
        self.archive = archive or TrendsArchiveStore(self.output_root)
        self.live_access_used = live_access_used

    def backfill(
        self,
        specs: Sequence[TrendsQuerySpec],
        *,
        as_of: date,
        days: int = 1800,
    ) -> TrendsRunResult:
        return self._run("backfill", specs, as_of=as_of, days=days, append=False)

    def collect(
        self,
        specs: Sequence[TrendsQuerySpec],
        *,
        as_of: date,
        lookback_days: int = 7,
    ) -> TrendsRunResult:
        return self._run("collect", specs, as_of=as_of, days=lookback_days, append=True)

    def _run(
        self,
        command: str,
        specs: Sequence[TrendsQuerySpec],
        *,
        as_of: date,
        days: int,
        append: bool,
    ) -> TrendsRunResult:
        if not 1 <= days <= 1800:
            raise TrendsDataError("Google Trends request days must be in [1, 1800]")
        manifest_hash = query_manifest_sha256(specs)
        end_date = as_of - timedelta(days=2)
        start_date = end_date - timedelta(days=days - 1)
        requests = build_request_plan(specs, start_date, end_date)
        feature_frames: list[pd.DataFrame] = []
        observation_frames: list[pd.DataFrame] = []
        exclusion_frames: list[pd.DataFrame] = []
        archive_paths: list[str] = []
        api_versions: set[str] = set()
        retrieval_times: list[datetime] = []
        for request in requests:
            response = self.gateway.fetch(request)
            archived = self.archive.record(
                request=request, response=response, manifest_hash=manifest_hash
            )
            try:
                archive_paths.append(str(archived.relative_to(self.output_root)))
            except ValueError:
                archive_paths.append(str(archived))
            api_versions.add(response.api_version)
            retrieval_times.append(response.retrieved_at)
            features, observations, exclusions = normalize_response(response, specs)
            feature_frames.append(features)
            observation_frames.append(observations)
            exclusion_frames.append(exclusions)
        features = pd.concat(feature_frames, ignore_index=True) if feature_frames else pd.DataFrame()
        observations = (
            pd.concat(observation_frames, ignore_index=True) if observation_frames else pd.DataFrame()
        )
        exclusions = (
            pd.concat(exclusion_frames, ignore_index=True) if exclusion_frames else pd.DataFrame()
        )
        if append:
            features = _merge_features(
                _read_existing_csv(
                    self.output_root / "features.csv",
                    ["feature_id", "observation_at", "available_at", "vintage", "source", "value"],
                ),
                features,
            )
            observations = _merge_observations(
                _read_existing_csv(self.output_root / "trends_observations.csv", observations.columns),
                observations,
            )
            prior_exclusions = _read_existing_csv(
                self.output_root / "trends_exclusions.csv",
                ["query_id", "observation_date", "reason", "retrieved_at"],
            )
            exclusions = pd.concat([prior_exclusions, exclusions], ignore_index=True).drop_duplicates()
        if not features.empty:
            features = features.sort_values(
                ["feature_id", "observation_at", "available_at", "vintage"]
            ).reset_index(drop=True)
        if not observations.empty:
            observations = observations.sort_values(
                ["query_id", "observation_date", "retrieved_at", "request_id"]
            ).reset_index(drop=True)
        if not exclusions.empty:
            exclusions["retrieved_at"] = pd.to_datetime(
                exclusions["retrieved_at"], utc=True, errors="raise"
            )
            exclusions = exclusions.sort_values(
                ["query_id", "observation_date", "retrieved_at", "reason"]
            ).reset_index(drop=True)
        self.output_root.mkdir(parents=True, exist_ok=True)
        outputs = {
            "features": write_dataframe(features, "features", self.output_root),
            "feature_manifest": write_dataframe(
                feature_manifest_frame(specs), "feature_manifest", self.output_root
            ),
            "trends_observations": write_dataframe(
                observations, "trends_observations", self.output_root
            ),
            "trends_exclusions": write_dataframe(
                exclusions, "trends_exclusions", self.output_root
            ),
            "query_manifest": write_dataframe(
                query_manifest_frame(specs), "query_manifest", self.output_root
            ),
        }
        usable_dates = pd.to_datetime(
            observations.loc[observations.get("usable", False) == True, "observation_date"],
            errors="coerce",
        ) if not observations.empty else pd.Series(dtype="datetime64[ns]")
        latest_usable = (
            usable_dates.max().date().isoformat() if len(usable_dates.dropna()) else None
        )
        counts = {
            "features": len(features),
            "observations": len(observations),
            "exclusions": len(exclusions),
            "active_queries": sum(spec.active for spec in specs),
            "candidate_queries": len(specs),
        }
        run_manifest = {
            "provider": PROVIDER,
            "mode": "official_api_alpha_readiness",
            "command": command,
            "created_at": max(retrieval_times).isoformat() if retrieval_times else None,
            "query_manifest_sha256": manifest_hash,
            "query_set_frozen": all(spec.freeze_date for spec in specs if spec.active),
            "api_versions": sorted(api_versions),
            "request_range": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "latest_usable_date": latest_usable,
            "counts": counts,
            "outputs": outputs,
            "raw_archives": sorted(archive_paths),
            "live_access_used": self.live_access_used,
            "unofficial_fallbacks_used": False,
            "historical_point_in_time_claims_enabled": False,
            "credentials_persisted": False,
        }
        (self.output_root / "trends_run_manifest.json").write_text(
            json.dumps(run_manifest, indent=2, sort_keys=True), encoding="utf-8"
        )
        return TrendsRunResult(
            output_dir=self.output_root,
            counts=counts,
            latest_usable_date=latest_usable,
            query_manifest_sha256=manifest_hash,
            live_access_used=self.live_access_used,
        )


def trends_status(
    output_root: str | Path,
    specs: Sequence[TrendsQuerySpec],
) -> dict[str, Any]:
    root = Path(output_root).resolve()
    observations = _read_existing_csv(
        root / "trends_observations.csv",
        ["query_id", "observation_date", "status", "usable", "retrieved_at"],
    )
    active = {spec.query_id for spec in specs if spec.active}
    if observations.empty:
        return {
            "provider": PROVIDER,
            "query_manifest_sha256": query_manifest_sha256(specs),
            "query_set_frozen": all(spec.freeze_date for spec in specs if spec.active),
            "observation_rows": 0,
            "latest_usable_date": None,
            "missing_active_queries": sorted(active),
            "suppressed_observations": 0,
            "low_volume_observations": 0,
            "coverage": {},
        }
    observations["usable"] = observations["usable"].map(
        lambda value: _parse_bool(value, "observations.usable")
    )
    usable = observations.loc[observations["usable"]]
    latest = pd.to_datetime(usable["observation_date"], errors="coerce").max()
    present = set(usable["query_id"].astype(str))
    all_dates = sorted(observations["observation_date"].astype(str).unique())
    denominator = len(all_dates)
    coverage = {
        query_id: (
            float((usable["query_id"].astype(str) == query_id).sum() / denominator)
            if denominator
            else 0.0
        )
        for query_id in sorted(active)
    }
    return {
        "provider": PROVIDER,
        "query_manifest_sha256": query_manifest_sha256(specs),
        "query_set_frozen": all(spec.freeze_date for spec in specs if spec.active),
        "observation_rows": len(observations),
        "latest_usable_date": latest.date().isoformat() if not pd.isna(latest) else None,
        "missing_active_queries": sorted(active.difference(present)),
        "suppressed_observations": int((observations["status"] == "suppressed").sum()),
        "low_volume_observations": int((observations["status"] == "low_volume").sum()),
        "coverage": coverage,
    }
