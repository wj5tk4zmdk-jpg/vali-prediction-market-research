"""External, read-only data providers."""

from .kalshi import (
    ArchiveStore,
    KalshiAdapter,
    KalshiClient,
    KalshiDataError,
    build_easing_mappings,
    normalize_candlesticks,
    normalize_orderbook_quote,
)
from .google_trends import (
    FixtureTrendsGateway,
    RetryingTrendsGateway,
    TrendsAdapter,
    TrendsDataError,
    TrendsGateway,
    TrendsQuerySpec,
    TrendsRequest,
    UnavailableOfficialTrendsGateway,
)

__all__ = [
    "ArchiveStore",
    "KalshiAdapter",
    "KalshiClient",
    "KalshiDataError",
    "build_easing_mappings",
    "normalize_candlesticks",
    "normalize_orderbook_quote",
    "FixtureTrendsGateway",
    "RetryingTrendsGateway",
    "TrendsAdapter",
    "TrendsDataError",
    "TrendsGateway",
    "TrendsQuerySpec",
    "TrendsRequest",
    "UnavailableOfficialTrendsGateway",
]
