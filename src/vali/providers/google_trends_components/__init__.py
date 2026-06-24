"""Internal components for offline Google Trends alpha readiness."""

from .audit import trends_status
from .client import RetryingTrendsGateway, UnavailableOfficialTrendsGateway
from .contracts import (
    PROVIDER,
    PUBLIC_CAPABILITY_VERSION,
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
    redact_sensitive,
)
from .fixtures import FixtureTrendsGateway
from .manifest import (
    build_request_plan,
    default_query_manifest_path,
    load_query_manifest,
    query_manifest_frame,
    query_manifest_sha256,
    validate_query_manifest,
    write_request_plan,
)
from .normalization import (
    feature_manifest_frame,
    merge_features,
    merge_observations,
    normalize_response,
    read_existing_csv,
)

__all__ = [
    "PROVIDER",
    "PUBLIC_CAPABILITY_VERSION",
    "SOURCE",
    "FixtureTrendsGateway",
    "RetryingTrendsGateway",
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
    "UnavailableOfficialTrendsGateway",
    "build_request_plan",
    "default_query_manifest_path",
    "feature_manifest_frame",
    "load_query_manifest",
    "merge_features",
    "merge_observations",
    "normalize_response",
    "query_manifest_frame",
    "query_manifest_sha256",
    "read_existing_csv",
    "redact_sensitive",
    "trends_status",
    "validate_query_manifest",
    "write_request_plan",
]
