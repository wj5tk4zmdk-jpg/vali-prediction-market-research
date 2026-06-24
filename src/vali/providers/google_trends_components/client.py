"""No-network official API gate and protocol-independent retry wrapper.

The official Google Trends alpha wire protocol is not available to this
package. This module intentionally adds no HTTP client, credentials, or live
network behavior.
"""

from __future__ import annotations

import time
from typing import Callable

from .contracts import (
    TrendsAccessUnavailable,
    TrendsDataError,
    TrendsGateway,
    TrendsGatewayResponse,
    TrendsRequest,
    TrendsTransientError,
)


class UnavailableOfficialTrendsGateway:
    """Explicit gate used until Google supplies the private alpha protocol."""

    def fetch(self, request: TrendsRequest) -> TrendsGatewayResponse:
        raise TrendsAccessUnavailable(
            "Official Google Trends API alpha access is not configured. "
            "Use --fixture for offline validation; no scraping fallback is "
            "permitted."
        )


class RetryingTrendsGateway:
    """Protocol-independent exponential retry wrapper."""

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


__all__ = ["RetryingTrendsGateway", "UnavailableOfficialTrendsGateway"]
