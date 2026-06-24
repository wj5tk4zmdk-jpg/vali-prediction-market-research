"""Public read-only Kalshi REST transport, retries, and pagination."""

from __future__ import annotations

import json
import time
from typing import Any, Callable
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .archive import ArchiveStore
from .contracts import (
    PRODUCTION_BASE_URL,
    SERIES_TICKER,
    KalshiDataError,
    Transport,
)


def default_transport(url: str, timeout: float) -> bytes:
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "vali-research/0.2",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        return response.read()


class KalshiClient:
    """Minimal public REST client; it intentionally has no write methods."""

    def __init__(
        self,
        base_url: str = PRODUCTION_BASE_URL,
        *,
        timeout: float = 30.0,
        max_retries: int = 5,
        archive: ArchiveStore | None = None,
        transport: Transport | None = None,
        sleeper: Callable[[float], None] = time.sleep,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.archive = archive
        self.transport = transport or default_transport
        self.sleeper = sleeper

    def get(
        self, path: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        query = urlencode(
            [
                (key, value)
                for key, value in (params or {}).items()
                if value is not None
            ],
            doseq=True,
        )
        url = f"{self.base_url}/{path.lstrip('/')}" + (
            f"?{query}" if query else ""
        )
        for attempt in range(self.max_retries + 1):
            try:
                payload = json.loads(
                    self.transport(url, self.timeout).decode("utf-8")
                )
                if self.archive:
                    self.archive.record(url=url, payload=payload)
                return payload
            except HTTPError as exc:
                if exc.code != 429 and exc.code < 500:
                    raise KalshiDataError(
                        f"Kalshi request failed ({exc.code}): {url}"
                    ) from exc
                if attempt >= self.max_retries:
                    raise KalshiDataError(
                        f"Kalshi retry budget exhausted: {url}"
                    ) from exc
                self.sleeper(min(0.5 * (2**attempt), 8.0))
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                if attempt >= self.max_retries:
                    raise KalshiDataError(
                        f"Kalshi request failed: {url}"
                    ) from exc
                self.sleeper(min(0.5 * (2**attempt), 8.0))
        raise AssertionError("unreachable")

    def paginate(
        self,
        path: str,
        *,
        collection: str,
        params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        query = dict(params or {})
        query.setdefault("limit", 200)
        rows: list[dict[str, Any]] = []
        seen_cursors: set[str] = set()
        while True:
            response = self.get(path, query)
            rows.extend(response.get(collection, []))
            cursor = str(response.get("cursor") or "")
            if not cursor:
                return rows
            if cursor in seen_cursors:
                raise KalshiDataError(
                    f"Repeated pagination cursor from {path}: {cursor}"
                )
            seen_cursors.add(cursor)
            query["cursor"] = cursor

    def series(self, ticker: str = SERIES_TICKER) -> dict[str, Any]:
        return self.get(f"series/{ticker}").get("series", {})

    def events(
        self, ticker: str = SERIES_TICKER, status: str | None = None
    ) -> list[dict[str, Any]]:
        return self.paginate(
            "events",
            collection="events",
            params={"series_ticker": ticker, "status": status},
        )

    def markets(
        self,
        *,
        event_ticker: str | None = None,
        series_ticker: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        return self.paginate(
            "markets",
            collection="markets",
            params={
                "event_ticker": event_ticker,
                "series_ticker": series_ticker,
                "status": status,
            },
        )

    def historical_markets(
        self, event_ticker: str
    ) -> list[dict[str, Any]]:
        return self.paginate(
            "historical/markets",
            collection="markets",
            params={"event_ticker": event_ticker},
        )

    def markets_for_event(
        self, event_ticker: str
    ) -> list[dict[str, Any]]:
        live = self.markets(event_ticker=event_ticker)
        return live or self.historical_markets(event_ticker)

    def historical_cutoff(self) -> dict[str, Any]:
        return self.get("historical/cutoff")

    def candlesticks(
        self,
        *,
        ticker: str,
        start_ts: int,
        end_ts: int,
        historical: bool,
        series_ticker: str = SERIES_TICKER,
        period_interval: int = 60,
    ) -> list[dict[str, Any]]:
        path = (
            f"historical/markets/{ticker}/candlesticks"
            if historical
            else f"series/{series_ticker}/markets/{ticker}/candlesticks"
        )
        max_periods = 4000
        chunk_seconds = period_interval * 60 * max_periods
        by_timestamp: dict[int, dict[str, Any]] = {}
        chunk_start = start_ts
        while chunk_start <= end_ts:
            chunk_end = min(end_ts, chunk_start + chunk_seconds)
            response = self.get(
                path,
                {
                    "start_ts": chunk_start,
                    "end_ts": chunk_end,
                    "period_interval": period_interval,
                },
            )
            for candle in response.get("candlesticks", []):
                by_timestamp[int(candle["end_period_ts"])] = candle
            if chunk_end >= end_ts:
                break
            chunk_start = chunk_end + 1
        return [by_timestamp[key] for key in sorted(by_timestamp)]

    def trades(
        self, ticker: str, *, historical: bool
    ) -> list[dict[str, Any]]:
        return self.paginate(
            "historical/trades" if historical else "markets/trades",
            collection="trades",
            params={"ticker": ticker},
        )

    def orderbook(self, ticker: str) -> dict[str, Any]:
        return self.get(f"markets/{ticker}/orderbook")


__all__ = ["KalshiClient", "default_transport"]
