"""Kalshi fixture/API response normalization into VALI tables."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Iterable

import numpy as np
import pandas as pd

from .contracts import EasingMapping, KalshiDataError, utc_now
from .mapping import decimal_value, timestamp_value


def normalize_candlesticks(
    mapping: EasingMapping, candlesticks: Iterable[dict[str, Any]]
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for candle in candlesticks:
        yes_bid_distribution = candle.get("yes_bid", {})
        yes_ask_distribution = candle.get("yes_ask", {})
        price_distribution = candle.get("price", {})
        yes_bid = yes_bid_distribution.get(
            "close_dollars", yes_bid_distribution.get("close")
        )
        yes_ask = yes_ask_distribution.get(
            "close_dollars", yes_ask_distribution.get("close")
        )
        if yes_bid is None or yes_ask is None:
            continue
        internal_bid = Decimal("1") - decimal_value(yes_ask)
        internal_ask = Decimal("1") - decimal_value(yes_bid)
        source_last = price_distribution.get(
            "close_dollars", price_distribution.get("close")
        )
        internal_last = (
            Decimal("1") - decimal_value(source_last)
            if source_last is not None
            else (internal_bid + internal_ask) / 2
        )
        rows.append(
            {
                "contract_id": mapping.contract_id,
                "observed_at": pd.to_datetime(
                    int(candle["end_period_ts"]), unit="s", utc=True
                ),
                "bid": float(internal_bid),
                "ask": float(internal_ask),
                "last": float(internal_last),
                "volume": float(
                    decimal_value(
                        candle.get("volume_fp", candle.get("volume", "0"))
                    )
                ),
                "bid_depth": np.nan,
                "ask_depth": np.nan,
                "depth_observed": False,
                "venue": "kalshi",
                "source_ticker": mapping.source_ticker,
                "source_side": "no",
                "source_event": mapping.event_ticker,
                "strike": float(mapping.strike),
                "open_interest": float(
                    decimal_value(
                        candle.get(
                            "open_interest_fp",
                            candle.get("open_interest", "0"),
                        )
                    )
                ),
                "mapping_rationale": mapping.mapping_rationale,
            }
        )
    return pd.DataFrame(rows)


def orderbook_levels(
    orderbook: dict[str, Any], side: str
) -> list[tuple[Decimal, Decimal]]:
    raw = orderbook.get("orderbook_fp", {}).get(
        f"{side}_dollars", []
    )
    return sorted(
        [
            (decimal_value(price), decimal_value(count))
            for price, count in raw
        ],
        key=lambda item: item[0],
    )


def depth(
    levels: list[tuple[Decimal, Decimal]],
    band: Decimal,
    *,
    complement: bool,
) -> Decimal:
    if not levels:
        return Decimal("0")
    best = levels[-1][0]
    total = Decimal("0")
    for price, count in reversed(levels):
        if best - price > band:
            break
        internal_price = Decimal("1") - price if complement else price
        total += internal_price * count
    return total


def normalize_orderbook_quote(
    mapping: EasingMapping,
    market: dict[str, Any],
    orderbook: dict[str, Any],
    *,
    observed_at: datetime | None = None,
    depth_band: Decimal = Decimal("0.05"),
) -> tuple[dict[str, Any], pd.DataFrame]:
    yes_levels = orderbook_levels(orderbook, "yes")
    no_levels = orderbook_levels(orderbook, "no")
    if not yes_levels or not no_levels:
        raise KalshiDataError(
            f"Two-sided order book unavailable for {mapping.source_ticker}"
        )
    best_yes = yes_levels[-1][0]
    best_no = no_levels[-1][0]
    internal_bid = best_no
    internal_ask = Decimal("1") - best_yes
    timestamp = observed_at or utc_now()
    quote = {
        "contract_id": mapping.contract_id,
        "observed_at": timestamp.isoformat(),
        "bid": float(internal_bid),
        "ask": float(internal_ask),
        "last": float(
            Decimal("1")
            - decimal_value(market.get("last_price_dollars", best_yes))
        ),
        "volume": float(decimal_value(market.get("volume_fp", "0"))),
        "bid_depth": float(
            depth(no_levels, depth_band, complement=False)
        ),
        "ask_depth": float(
            depth(yes_levels, depth_band, complement=True)
        ),
        "depth_observed": True,
        "venue": "kalshi",
        "source_ticker": mapping.source_ticker,
        "source_side": "no",
        "source_event": mapping.event_ticker,
        "strike": float(mapping.strike),
        "mapping_rationale": mapping.mapping_rationale,
    }
    level_rows: list[dict[str, Any]] = []
    for source_side, levels in (("yes", yes_levels), ("no", no_levels)):
        for price, count in levels:
            internal_side = "ask" if source_side == "yes" else "bid"
            internal_price = (
                Decimal("1") - price if source_side == "yes" else price
            )
            level_rows.append(
                {
                    "observed_at": timestamp.isoformat(),
                    "event_ticker": mapping.event_ticker,
                    "market_ticker": mapping.source_ticker,
                    "strike": float(mapping.strike),
                    "source_side": source_side,
                    "source_price": float(price),
                    "count": float(count),
                    "internal_side": internal_side,
                    "internal_price": float(internal_price),
                    "dollar_depth": float(internal_price * count),
                }
            )
    return quote, pd.DataFrame(level_rows)


def normalized_events(mappings: Iterable[EasingMapping]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "event_id": mapping.event_ticker,
                "contract_id": mapping.contract_id,
                "open_at": mapping.open_at,
                "meeting_at": mapping.meeting_at,
                "settlement_at": mapping.settlement_at,
                "yes_label": (
                    "Fed target-range upper bound lower after scheduled meeting"
                ),
                "outcome": mapping.outcome,
                "venue": "kalshi",
                "source_ticker": mapping.source_ticker,
                "source_side": "no",
                "strike": float(mapping.strike),
                "pre_meeting_upper_bound": float(
                    mapping.pre_meeting_upper_bound
                ),
                "realized_upper_bound": float(mapping.realized_upper_bound),
                "mapping_rationale": mapping.mapping_rationale,
            }
            for mapping in mappings
        ]
    )


def normalize_trades(
    mapping: EasingMapping, trades: Iterable[dict[str, Any]]
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for index, trade in enumerate(trades):
        source_price = trade.get(
            "yes_price_dollars", trade.get("yes_price")
        )
        if source_price is None:
            continue
        observed = trade.get("created_time", trade.get("created_ts"))
        if observed is None:
            continue
        size = decimal_value(trade.get("count_fp", trade.get("count", "0")))
        if size <= 0:
            continue
        rows.append(
            {
                "trade_id": str(
                    trade.get(
                        "trade_id", f"{mapping.source_ticker}-{index}"
                    )
                ),
                "contract_id": mapping.contract_id,
                "observed_at": timestamp_value(observed).isoformat(),
                "price": float(Decimal("1") - decimal_value(source_price)),
                "size": float(size),
                "venue": "kalshi",
                "source_ticker": mapping.source_ticker,
                "source_side": "no",
            }
        )
    return pd.DataFrame(rows)


__all__ = [
    "depth",
    "normalize_candlesticks",
    "normalize_orderbook_quote",
    "normalize_trades",
    "normalized_events",
    "orderbook_levels",
]
