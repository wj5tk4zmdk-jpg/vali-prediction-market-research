"""Compatibility facade for offline Google Trends API alpha readiness."""

from __future__ import annotations

from datetime import date, datetime, timedelta
import gzip
import json
from pathlib import Path
from typing import Any, Sequence

import pandas as pd

from ..reporting import write_dataframe
from .google_trends_components.audit import trends_status
from .google_trends_components.client import (
    RetryingTrendsGateway,
    UnavailableOfficialTrendsGateway,
)
from .google_trends_components.contracts import (
    ALLOWED_AGGREGATIONS,
    ALLOWED_BASKETS,
    ALLOWED_QUERY_KINDS,
    ALLOWED_STATUSES,
    PROVIDER,
    PUBLIC_CAPABILITY_VERSION,
    QUERY_MANIFEST_COLUMNS,
    QUERY_MANIFEST_VERSION,
    SENSITIVE_KEYS,
    SOURCE,
    TrendsAccessUnavailable,
    TrendsDataError,
    TrendsError,
    TrendsGateway,
    TrendsGatewayResponse,
    TrendsObservation,
    TrendsQuerySpec,
    TrendsRateLimitError,
    TrendsRequest,
    TrendsRunResult,
    TrendsTransientError,
    canonical_bytes,
    parse_bool,
    parse_datetime,
    redact_sensitive,
    sha256_value,
)
from .google_trends_components.fixtures import FixtureTrendsGateway
from .google_trends_components.manifest import (
    build_request_plan,
    default_query_manifest_path,
    load_query_manifest,
    query_manifest_frame,
    query_manifest_sha256,
    validate_query_manifest,
    write_request_plan,
)
from .google_trends_components.normalization import (
    feature_manifest_frame,
    merge_features,
    merge_observations,
    normalize_response,
    read_existing_csv,
)


_parse_bool = parse_bool
_parse_datetime = parse_datetime
_canonical_bytes = canonical_bytes
_sha256 = sha256_value
_read_existing_csv = read_existing_csv
_merge_features = merge_features
_merge_observations = merge_observations


class TrendsArchiveStore:
    """Content-addressed archive with mandatory credential redaction."""

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
        directory = (
            self.root
            / "raw"
            / PROVIDER
            / response.retrieved_at.strftime("%Y/%m/%d")
        )
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
            json.dump(
                envelope,
                handle,
                sort_keys=True,
                separators=(",", ":"),
            )
        temporary.replace(path)
        return path


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
        return self._run(
            "backfill", specs, as_of=as_of, days=days, append=False
        )

    def collect(
        self,
        specs: Sequence[TrendsQuerySpec],
        *,
        as_of: date,
        lookback_days: int = 7,
    ) -> TrendsRunResult:
        return self._run(
            "collect",
            specs,
            as_of=as_of,
            days=lookback_days,
            append=True,
        )

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
            raise TrendsDataError(
                "Google Trends request days must be in [1, 1800]"
            )
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
                request=request,
                response=response,
                manifest_hash=manifest_hash,
            )
            try:
                archive_paths.append(
                    str(archived.relative_to(self.output_root))
                )
            except ValueError:
                archive_paths.append(str(archived))
            api_versions.add(response.api_version)
            retrieval_times.append(response.retrieved_at)
            features, observations, exclusions = normalize_response(
                response, specs
            )
            feature_frames.append(features)
            observation_frames.append(observations)
            exclusion_frames.append(exclusions)
        features = (
            pd.concat(feature_frames, ignore_index=True)
            if feature_frames
            else pd.DataFrame()
        )
        observations = (
            pd.concat(observation_frames, ignore_index=True)
            if observation_frames
            else pd.DataFrame()
        )
        exclusions = (
            pd.concat(exclusion_frames, ignore_index=True)
            if exclusion_frames
            else pd.DataFrame()
        )
        if append:
            features = _merge_features(
                _read_existing_csv(
                    self.output_root / "features.csv",
                    [
                        "feature_id",
                        "observation_at",
                        "available_at",
                        "vintage",
                        "source",
                        "value",
                    ],
                ),
                features,
            )
            observations = _merge_observations(
                _read_existing_csv(
                    self.output_root / "trends_observations.csv",
                    observations.columns,
                ),
                observations,
            )
            prior_exclusions = _read_existing_csv(
                self.output_root / "trends_exclusions.csv",
                [
                    "query_id",
                    "observation_date",
                    "reason",
                    "retrieved_at",
                ],
            )
            exclusions = pd.concat(
                [prior_exclusions, exclusions], ignore_index=True
            ).drop_duplicates()
        if not features.empty:
            features = features.sort_values(
                ["feature_id", "observation_at", "available_at", "vintage"]
            ).reset_index(drop=True)
        if not observations.empty:
            observations = observations.sort_values(
                [
                    "query_id",
                    "observation_date",
                    "retrieved_at",
                    "request_id",
                ]
            ).reset_index(drop=True)
        if not exclusions.empty:
            exclusions["retrieved_at"] = pd.to_datetime(
                exclusions["retrieved_at"], utc=True, errors="raise"
            )
            exclusions = exclusions.sort_values(
                [
                    "query_id",
                    "observation_date",
                    "retrieved_at",
                    "reason",
                ]
            ).reset_index(drop=True)
        self.output_root.mkdir(parents=True, exist_ok=True)
        outputs = {
            "features": write_dataframe(
                features, "features", self.output_root
            ),
            "feature_manifest": write_dataframe(
                feature_manifest_frame(specs),
                "feature_manifest",
                self.output_root,
            ),
            "trends_observations": write_dataframe(
                observations, "trends_observations", self.output_root
            ),
            "trends_exclusions": write_dataframe(
                exclusions, "trends_exclusions", self.output_root
            ),
            "query_manifest": write_dataframe(
                query_manifest_frame(specs),
                "query_manifest",
                self.output_root,
            ),
        }
        usable_dates = (
            pd.to_datetime(
                observations.loc[
                    observations.get("usable", False) == True,
                    "observation_date",
                ],
                errors="coerce",
            )
            if not observations.empty
            else pd.Series(dtype="datetime64[ns]")
        )
        latest_usable = (
            usable_dates.max().date().isoformat()
            if len(usable_dates.dropna())
            else None
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
            "created_at": (
                max(retrieval_times).isoformat() if retrieval_times else None
            ),
            "query_manifest_sha256": manifest_hash,
            "query_set_frozen": all(
                spec.freeze_date for spec in specs if spec.active
            ),
            "api_versions": sorted(api_versions),
            "request_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
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
            json.dumps(run_manifest, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return TrendsRunResult(
            output_dir=self.output_root,
            counts=counts,
            latest_usable_date=latest_usable,
            query_manifest_sha256=manifest_hash,
            live_access_used=self.live_access_used,
        )


__all__ = [
    "FixtureTrendsGateway",
    "RetryingTrendsGateway",
    "TrendsAccessUnavailable",
    "TrendsAdapter",
    "TrendsArchiveStore",
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
    "UnavailableOfficialTrendsGateway",
    "build_request_plan",
    "default_query_manifest_path",
    "feature_manifest_frame",
    "load_query_manifest",
    "normalize_response",
    "query_manifest_frame",
    "query_manifest_sha256",
    "redact_sensitive",
    "trends_status",
    "validate_query_manifest",
    "write_request_plan",
]
