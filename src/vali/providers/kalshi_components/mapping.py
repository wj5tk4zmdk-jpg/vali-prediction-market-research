"""KXFED threshold-ladder and internal EASING contract mapping."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path
import re
from typing import Any, Iterable

import pandas as pd

from .contracts import EasingMapping, KalshiDataError


STRIKE_PATTERN = re.compile(r"-T(-?\d+(?:\.\d+)?)$")


def decimal_value(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise KalshiDataError(
            f"Invalid fixed-point value: {value!r}"
        ) from exc


def timestamp_value(value: Any) -> pd.Timestamp:
    if isinstance(value, (int, float)) or (
        isinstance(value, str) and value.isdigit()
    ):
        timestamp = pd.to_datetime(int(value), unit="s", utc=True)
    else:
        timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize("UTC")
    return timestamp.tz_convert("UTC")


def parse_strike(ticker: str) -> Decimal:
    match = STRIKE_PATTERN.search(ticker)
    if not match:
        raise KalshiDataError(
            f"Cannot parse KXFED strike from ticker: {ticker}"
        )
    return decimal_value(match.group(1))


def realized_upper_bound(
    markets: Iterable[dict[str, Any]],
) -> Decimal:
    resolved: list[tuple[Decimal, str]] = []
    for market in markets:
        result = str(market.get("result", "")).lower()
        if result not in {"yes", "no"}:
            continue
        resolved.append((parse_strike(str(market["ticker"])), result))
    resolved.sort(key=lambda item: item[0])
    if len(resolved) < 2:
        raise KalshiDataError("Threshold ladder lacks resolved markets")
    seen_no = False
    for _, result in resolved:
        if result == "no":
            seen_no = True
        elif seen_no:
            raise KalshiDataError("Threshold results are not monotone")
    yes_strikes = [
        strike for strike, result in resolved if result == "yes"
    ]
    no_strikes = [strike for strike, result in resolved if result == "no"]
    if not yes_strikes or not no_strikes:
        raise KalshiDataError(
            "Threshold ladder does not bracket the settled rate"
        )
    highest_yes = max(yes_strikes)
    lowest_no = min(no_strikes)
    if lowest_no - highest_yes != Decimal("0.25"):
        raise KalshiDataError(
            "Threshold boundary is not a 25bp interval"
        )
    return lowest_no


def market_times(market: dict[str, Any]) -> tuple[str, str, str]:
    close = timestamp_value(market["close_time"])
    meeting = close + pd.Timedelta(minutes=5)
    return (
        timestamp_value(market["open_time"]).isoformat(),
        meeting.isoformat(),
        timestamp_value(
            market.get("expiration_time") or market["close_time"]
        ).isoformat(),
    )


def build_easing_mappings(
    events: Iterable[dict[str, Any]],
    markets_by_event: dict[str, list[dict[str, Any]]],
    upper_bounds: dict[str, Decimal] | None = None,
) -> tuple[list[EasingMapping], pd.DataFrame]:
    overrides = upper_bounds or {}
    enriched: list[
        tuple[
            pd.Timestamp,
            dict[str, Any],
            list[dict[str, Any]],
            Decimal | None,
        ]
    ] = []
    exclusions: list[dict[str, Any]] = []
    for event in events:
        event_ticker = str(event["event_ticker"])
        markets = markets_by_event.get(event_ticker, [])
        if not markets:
            exclusions.append(
                {
                    "event_ticker": event_ticker,
                    "stage": "mapping",
                    "reason": "no_markets",
                }
            )
            continue
        representative = min(
            markets,
            key=lambda market: timestamp_value(market["close_time"]),
        )
        try:
            realized = realized_upper_bound(markets)
        except KalshiDataError as exc:
            realized = None
            exclusions.append(
                {
                    "event_ticker": event_ticker,
                    "stage": "mapping",
                    "reason": str(exc),
                }
            )
        enriched.append(
            (
                timestamp_value(representative["close_time"]),
                event,
                markets,
                realized,
            )
        )
    enriched.sort(key=lambda item: item[0])

    mappings: list[EasingMapping] = []
    previous_realized: Decimal | None = None
    for _, event, markets, realized in enriched:
        event_ticker = str(event["event_ticker"])
        before = overrides.get(event_ticker, previous_realized)
        if before is None:
            exclusions.append(
                {
                    "event_ticker": event_ticker,
                    "stage": "mapping",
                    "reason": "missing_pre_meeting_upper_bound",
                }
            )
        elif before * 4 != (before * 4).to_integral_value():
            exclusions.append(
                {
                    "event_ticker": event_ticker,
                    "stage": "mapping",
                    "reason": "non_quarter_point_pre_meeting_rate",
                }
            )
        elif realized is not None:
            strike = before - Decimal("0.25")
            matches = [
                market
                for market in markets
                if parse_strike(str(market["ticker"])) == strike
            ]
            if len(matches) != 1:
                exclusions.append(
                    {
                        "event_ticker": event_ticker,
                        "stage": "mapping",
                        "reason": "missing_or_duplicate_easing_strike",
                    }
                )
            else:
                market = matches[0]
                result = str(market.get("result", "")).lower()
                if result not in {"yes", "no"}:
                    exclusions.append(
                        {
                            "event_ticker": event_ticker,
                            "stage": "mapping",
                            "reason": "ambiguous_settlement",
                        }
                    )
                else:
                    open_at, meeting_at, settlement_at = market_times(market)
                    mappings.append(
                        EasingMapping(
                            event_ticker=event_ticker,
                            source_ticker=str(market["ticker"]),
                            pre_meeting_upper_bound=before,
                            strike=strike,
                            outcome=1 if result == "no" else 0,
                            realized_upper_bound=realized,
                            open_at=open_at,
                            meeting_at=meeting_at,
                            settlement_at=settlement_at,
                        )
                    )
        if realized is not None:
            previous_realized = realized
    return mappings, pd.DataFrame(exclusions)


def load_upper_bounds(path: str | Path | None) -> dict[str, Decimal]:
    if path is None:
        return {}
    frame = pd.read_csv(path)
    required = {"event_ticker", "upper_bound"}
    if not required.issubset(frame.columns):
        raise KalshiDataError(
            "Upper-bound CSV requires event_ticker and upper_bound"
        )
    return {
        str(row.event_ticker): decimal_value(row.upper_bound)
        for row in frame.itertuples(index=False)
    }


__all__ = [
    "STRIKE_PATTERN",
    "build_easing_mappings",
    "decimal_value",
    "load_upper_bounds",
    "market_times",
    "parse_strike",
    "realized_upper_bound",
    "timestamp_value",
]
