"""Typed contracts and constants for public read-only Kalshi ingestion."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Callable


PRODUCTION_BASE_URL = "https://external-api.kalshi.com/trade-api/v2"
API_SPEC_VERSION = "3.22.0"
SERIES_TICKER = "KXFED"


class KalshiDataError(RuntimeError):
    """Raised when Kalshi data cannot be mapped without an unsafe assumption."""


@dataclass(frozen=True)
class EasingMapping:
    event_ticker: str
    source_ticker: str
    pre_meeting_upper_bound: Decimal
    strike: Decimal
    outcome: int
    realized_upper_bound: Decimal
    open_at: str
    meeting_at: str
    settlement_at: str
    mapping_rationale: str = (
        "NO on KXFED threshold above prior upper bound minus 25bp"
    )

    @property
    def contract_id(self) -> str:
        return f"{self.event_ticker}:EASING"


@dataclass
class KalshiRunResult:
    output_dir: Path
    counts: dict[str, int]
    mapped_events: int
    walk_forward_ready: bool


Transport = Callable[[str, float], bytes]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


__all__ = [
    "API_SPEC_VERSION",
    "EasingMapping",
    "KalshiDataError",
    "KalshiRunResult",
    "PRODUCTION_BASE_URL",
    "SERIES_TICKER",
    "Transport",
    "utc_now",
]
