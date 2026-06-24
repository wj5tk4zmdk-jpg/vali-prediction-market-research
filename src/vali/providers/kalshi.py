"""Read-only Kalshi REST ingestion and KXFED easing normalization."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import gzip
import hashlib
import json
from pathlib import Path
import re
import time
from typing import Any, Callable, Iterable
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd

from ..reporting import write_dataframe


PRODUCTION_BASE_URL = "https://external-api.kalshi.com/trade-api/v2"
API_SPEC_VERSION = "3.22.0"
SERIES_TICKER = "KXFED"
STRIKE_PATTERN = re.compile(r"-T(-?\d+(?:\.\d+)?)$")


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
    mapping_rationale: str = "NO on KXFED threshold above prior upper bound minus 25bp"

    @property
    def contract_id(self) -> str:
        return f"{self.event_ticker}:EASING"


@dataclass
class KalshiRunResult:
    output_dir: Path
    counts: dict[str, int]
    mapped_events: int
    walk_forward_ready: bool


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _canonical_bytes(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError) as exc:
        raise KalshiDataError(f"Invalid fixed-point value: {value!r}") from exc


def _timestamp(value: Any) -> pd.Timestamp:
    if isinstance(value, (int, float)) or (isinstance(value, str) and value.isdigit()):
        timestamp = pd.to_datetime(int(value), unit="s", utc=True)
    else:
        timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize("UTC")
    return timestamp.tz_convert("UTC")


def parse_strike(ticker: str) -> Decimal:
    match = STRIKE_PATTERN.search(ticker)
    if not match:
        raise KalshiDataError(f"Cannot parse KXFED strike from ticker: {ticker}")
    return _decimal(match.group(1))


class ArchiveStore:
    """Content-addressed immutable gzip archive for source API responses."""

    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()

    def record(
        self,
        *,
        url: str,
        payload: Any,
        retrieved_at: datetime | None = None,
    ) -> Path:
        retrieved = retrieved_at or _utc_now()
        content = _canonical_bytes(payload)
        digest = hashlib.sha256(content).hexdigest()
        directory = self.root / "raw" / "kalshi" / retrieved.strftime("%Y/%m/%d")
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{digest}.json.gz"
        if path.exists():
            return path
        envelope = {
            "api_spec_version": API_SPEC_VERSION,
            "content_sha256": digest,
            "retrieved_at": retrieved.isoformat(),
            "source_url": url,
            "payload": payload,
        }
        temporary = path.with_suffix(".tmp")
        with gzip.open(temporary, "wt", encoding="utf-8") as handle:
            json.dump(envelope, handle, sort_keys=True, separators=(",", ":"))
        temporary.replace(path)
        return path


Transport = Callable[[str, float], bytes]


def _default_transport(url: str, timeout: float) -> bytes:
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "vali-research/0.2"})
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
        self.transport = transport or _default_transport
        self.sleeper = sleeper

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        query = urlencode(
            [(key, value) for key, value in (params or {}).items() if value is not None],
            doseq=True,
        )
        url = f"{self.base_url}/{path.lstrip('/')}" + (f"?{query}" if query else "")
        for attempt in range(self.max_retries + 1):
            try:
                payload = json.loads(self.transport(url, self.timeout).decode("utf-8"))
                if self.archive:
                    self.archive.record(url=url, payload=payload)
                return payload
            except HTTPError as exc:
                if exc.code != 429 and exc.code < 500:
                    raise KalshiDataError(f"Kalshi request failed ({exc.code}): {url}") from exc
                if attempt >= self.max_retries:
                    raise KalshiDataError(f"Kalshi retry budget exhausted: {url}") from exc
                self.sleeper(min(0.5 * (2**attempt), 8.0))
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                if attempt >= self.max_retries:
                    raise KalshiDataError(f"Kalshi request failed: {url}") from exc
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
        # 200 is accepted across events, markets, and trades; individual
        # endpoints expose different larger maxima, so use the common bound.
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
                raise KalshiDataError(f"Repeated pagination cursor from {path}: {cursor}")
            seen_cursors.add(cursor)
            query["cursor"] = cursor

    def series(self, ticker: str = SERIES_TICKER) -> dict[str, Any]:
        return self.get(f"series/{ticker}").get("series", {})

    def events(self, ticker: str = SERIES_TICKER, status: str | None = None) -> list[dict[str, Any]]:
        return self.paginate(
            "events",
            collection="events",
            params={"series_ticker": ticker, "status": status},
        )

    def markets(self, *, event_ticker: str | None = None, series_ticker: str | None = None, status: str | None = None) -> list[dict[str, Any]]:
        return self.paginate(
            "markets",
            collection="markets",
            params={"event_ticker": event_ticker, "series_ticker": series_ticker, "status": status},
        )

    def historical_markets(self, event_ticker: str) -> list[dict[str, Any]]:
        return self.paginate(
            "historical/markets",
            collection="markets",
            params={"event_ticker": event_ticker},
        )

    def markets_for_event(self, event_ticker: str) -> list[dict[str, Any]]:
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
        # Keep each request below Kalshi's candle-count ceiling. Boundaries may
        # overlap, so de-duplicate by end_period_ts after collecting chunks.
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

    def trades(self, ticker: str, *, historical: bool) -> list[dict[str, Any]]:
        return self.paginate(
            "historical/trades" if historical else "markets/trades",
            collection="trades",
            params={"ticker": ticker},
        )

    def orderbook(self, ticker: str) -> dict[str, Any]:
        return self.get(f"markets/{ticker}/orderbook")


def realized_upper_bound(markets: Iterable[dict[str, Any]]) -> Decimal:
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
    yes_strikes = [strike for strike, result in resolved if result == "yes"]
    no_strikes = [strike for strike, result in resolved if result == "no"]
    if not yes_strikes or not no_strikes:
        raise KalshiDataError("Threshold ladder does not bracket the settled rate")
    highest_yes = max(yes_strikes)
    lowest_no = min(no_strikes)
    if lowest_no - highest_yes != Decimal("0.25"):
        raise KalshiDataError("Threshold boundary is not a 25bp interval")
    return lowest_no


def _market_times(market: dict[str, Any]) -> tuple[str, str, str]:
    close = _timestamp(market["close_time"])
    meeting = close + pd.Timedelta(minutes=5)
    return (
        _timestamp(market["open_time"]).isoformat(),
        meeting.isoformat(),
        _timestamp(market.get("expiration_time") or market["close_time"]).isoformat(),
    )


def build_easing_mappings(
    events: Iterable[dict[str, Any]],
    markets_by_event: dict[str, list[dict[str, Any]]],
    upper_bounds: dict[str, Decimal] | None = None,
) -> tuple[list[EasingMapping], pd.DataFrame]:
    overrides = upper_bounds or {}
    enriched: list[tuple[pd.Timestamp, dict[str, Any], list[dict[str, Any]], Decimal | None]] = []
    exclusions: list[dict[str, Any]] = []
    for event in events:
        event_ticker = str(event["event_ticker"])
        markets = markets_by_event.get(event_ticker, [])
        if not markets:
            exclusions.append({"event_ticker": event_ticker, "stage": "mapping", "reason": "no_markets"})
            continue
        representative = min(markets, key=lambda market: _timestamp(market["close_time"]))
        try:
            realized = realized_upper_bound(markets)
        except KalshiDataError as exc:
            realized = None
            exclusions.append({"event_ticker": event_ticker, "stage": "mapping", "reason": str(exc)})
        enriched.append((_timestamp(representative["close_time"]), event, markets, realized))
    enriched.sort(key=lambda item: item[0])

    mappings: list[EasingMapping] = []
    previous_realized: Decimal | None = None
    for _, event, markets, realized in enriched:
        event_ticker = str(event["event_ticker"])
        before = overrides.get(event_ticker, previous_realized)
        if before is None:
            exclusions.append({"event_ticker": event_ticker, "stage": "mapping", "reason": "missing_pre_meeting_upper_bound"})
        elif before * 4 != (before * 4).to_integral_value():
            exclusions.append({"event_ticker": event_ticker, "stage": "mapping", "reason": "non_quarter_point_pre_meeting_rate"})
        elif realized is not None:
            strike = before - Decimal("0.25")
            matches = [market for market in markets if parse_strike(str(market["ticker"])) == strike]
            if len(matches) != 1:
                exclusions.append({"event_ticker": event_ticker, "stage": "mapping", "reason": "missing_or_duplicate_easing_strike"})
            else:
                market = matches[0]
                result = str(market.get("result", "")).lower()
                if result not in {"yes", "no"}:
                    exclusions.append({"event_ticker": event_ticker, "stage": "mapping", "reason": "ambiguous_settlement"})
                else:
                    open_at, meeting_at, settlement_at = _market_times(market)
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


def normalize_candlesticks(
    mapping: EasingMapping, candlesticks: Iterable[dict[str, Any]]
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for candle in candlesticks:
        yes_bid_distribution = candle.get("yes_bid", {})
        yes_ask_distribution = candle.get("yes_ask", {})
        price_distribution = candle.get("price", {})
        yes_bid = yes_bid_distribution.get("close_dollars", yes_bid_distribution.get("close"))
        yes_ask = yes_ask_distribution.get("close_dollars", yes_ask_distribution.get("close"))
        if yes_bid is None or yes_ask is None:
            continue
        internal_bid = Decimal("1") - _decimal(yes_ask)
        internal_ask = Decimal("1") - _decimal(yes_bid)
        source_last = price_distribution.get("close_dollars", price_distribution.get("close"))
        internal_last = (
            Decimal("1") - _decimal(source_last)
            if source_last is not None
            else (internal_bid + internal_ask) / 2
        )
        rows.append(
            {
                "contract_id": mapping.contract_id,
                "observed_at": pd.to_datetime(int(candle["end_period_ts"]), unit="s", utc=True),
                "bid": float(internal_bid),
                "ask": float(internal_ask),
                "last": float(internal_last),
                "volume": float(_decimal(candle.get("volume_fp", candle.get("volume", "0")))),
                "bid_depth": np.nan,
                "ask_depth": np.nan,
                "depth_observed": False,
                "venue": "kalshi",
                "source_ticker": mapping.source_ticker,
                "source_side": "no",
                "source_event": mapping.event_ticker,
                "strike": float(mapping.strike),
                "open_interest": float(
                    _decimal(candle.get("open_interest_fp", candle.get("open_interest", "0")))
                ),
                "mapping_rationale": mapping.mapping_rationale,
            }
        )
    return pd.DataFrame(rows)


def _levels(orderbook: dict[str, Any], side: str) -> list[tuple[Decimal, Decimal]]:
    raw = orderbook.get("orderbook_fp", {}).get(f"{side}_dollars", [])
    return sorted([(_decimal(price), _decimal(count)) for price, count in raw], key=lambda item: item[0])


def _depth(levels: list[tuple[Decimal, Decimal]], band: Decimal, *, complement: bool) -> Decimal:
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
    yes_levels = _levels(orderbook, "yes")
    no_levels = _levels(orderbook, "no")
    if not yes_levels or not no_levels:
        raise KalshiDataError(f"Two-sided order book unavailable for {mapping.source_ticker}")
    best_yes = yes_levels[-1][0]
    best_no = no_levels[-1][0]
    internal_bid = best_no
    internal_ask = Decimal("1") - best_yes
    timestamp = observed_at or _utc_now()
    quote = {
        "contract_id": mapping.contract_id,
        "observed_at": timestamp.isoformat(),
        "bid": float(internal_bid),
        "ask": float(internal_ask),
        "last": float(Decimal("1") - _decimal(market.get("last_price_dollars", best_yes))),
        "volume": float(_decimal(market.get("volume_fp", "0"))),
        "bid_depth": float(_depth(no_levels, depth_band, complement=False)),
        "ask_depth": float(_depth(yes_levels, depth_band, complement=True)),
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
            internal_price = Decimal("1") - price if source_side == "yes" else price
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


def _normalized_events(mappings: Iterable[EasingMapping]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "event_id": mapping.event_ticker,
                "contract_id": mapping.contract_id,
                "open_at": mapping.open_at,
                "meeting_at": mapping.meeting_at,
                "settlement_at": mapping.settlement_at,
                "yes_label": "Fed target-range upper bound lower after scheduled meeting",
                "outcome": mapping.outcome,
                "venue": "kalshi",
                "source_ticker": mapping.source_ticker,
                "source_side": "no",
                "strike": float(mapping.strike),
                "pre_meeting_upper_bound": float(mapping.pre_meeting_upper_bound),
                "realized_upper_bound": float(mapping.realized_upper_bound),
                "mapping_rationale": mapping.mapping_rationale,
            }
            for mapping in mappings
        ]
    )


def _normalize_trades(mapping: EasingMapping, trades: Iterable[dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for index, trade in enumerate(trades):
        source_price = trade.get("yes_price_dollars", trade.get("yes_price"))
        if source_price is None:
            continue
        observed = trade.get("created_time", trade.get("created_ts"))
        if observed is None:
            continue
        size = _decimal(trade.get("count_fp", trade.get("count", "0")))
        if size <= 0:
            continue
        rows.append(
            {
                "trade_id": str(trade.get("trade_id", f"{mapping.source_ticker}-{index}")),
                "contract_id": mapping.contract_id,
                "observed_at": _timestamp(observed).isoformat(),
                "price": float(Decimal("1") - _decimal(source_price)),
                "size": float(size),
                "venue": "kalshi",
                "source_ticker": mapping.source_ticker,
                "source_side": "no",
            }
        )
    return pd.DataFrame(rows)


class KalshiAdapter:
    def __init__(self, client: KalshiClient, output_root: str | Path, series_ticker: str = SERIES_TICKER):
        self.client = client
        self.output_root = Path(output_root).resolve()
        self.series_ticker = series_ticker

    def discover(self) -> KalshiRunResult:
        self.output_root.mkdir(parents=True, exist_ok=True)
        series = self.client.series(self.series_ticker)
        settled = self.client.events(self.series_ticker, "settled")
        open_events = self.client.events(self.series_ticker, "open")
        open_markets = self.client.markets(series_ticker=self.series_ticker, status="open")
        frames = {
            "series": pd.DataFrame([series]),
            "settled_events": pd.DataFrame(settled),
            "open_events": pd.DataFrame(open_events),
            "open_markets": pd.DataFrame(open_markets),
        }
        outputs = {name: write_dataframe(frame, name, self.output_root) for name, frame in frames.items()}
        manifest = self._write_manifest("discover", outputs, {name: len(frame) for name, frame in frames.items()})
        return KalshiRunResult(self.output_root, manifest["counts"], 0, False)

    def _load_markets(self, events: Iterable[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        return {
            str(event["event_ticker"]): self.client.markets_for_event(str(event["event_ticker"]))
            for event in events
        }

    def backfill(
        self,
        *,
        min_events: int = 16,
        upper_bounds: dict[str, Decimal] | None = None,
        include_trades: bool = True,
        candle_interval_minutes: int = 60,
    ) -> KalshiRunResult:
        if candle_interval_minutes not in {1, 60, 1440}:
            raise KalshiDataError("Kalshi candle interval must be 1, 60, or 1440 minutes")
        self.output_root.mkdir(parents=True, exist_ok=True)
        cutoff = self.client.historical_cutoff()
        events = self.client.events(self.series_ticker, "settled")
        markets_by_event = self._load_markets(events)
        mappings, exclusions = build_easing_mappings(events, markets_by_event, upper_bounds)
        cutoff_value = cutoff.get("market_settled_ts") or cutoff.get("cutoff", {}).get("market_settled_ts")
        market_cutoff = _timestamp(cutoff_value) if cutoff_value else pd.Timestamp.max.tz_localize("UTC")
        quote_frames: list[pd.DataFrame] = []
        trade_frames: list[pd.DataFrame] = []
        for mapping in mappings:
            source_market = next(
                market
                for market in markets_by_event[mapping.event_ticker]
                if market["ticker"] == mapping.source_ticker
            )
            historical = _timestamp(mapping.settlement_at) < market_cutoff
            start = int(_timestamp(mapping.open_at).timestamp())
            end = int(_timestamp(mapping.meeting_at).timestamp())
            candles = self.client.candlesticks(
                ticker=mapping.source_ticker,
                start_ts=start,
                end_ts=end,
                historical=historical,
                series_ticker=self.series_ticker,
                period_interval=candle_interval_minutes,
            )
            quote_frames.append(normalize_candlesticks(mapping, candles))
            if include_trades:
                trade_frames.append(
                    _normalize_trades(
                        mapping, self.client.trades(mapping.source_ticker, historical=historical)
                    )
                )
        normalized_events = _normalized_events(mappings)
        quotes = pd.concat(quote_frames, ignore_index=True) if quote_frames else pd.DataFrame()
        trades = pd.concat(trade_frames, ignore_index=True) if trade_frames else pd.DataFrame()
        mapping_frame = pd.DataFrame([mapping.__dict__ | {"contract_id": mapping.contract_id} for mapping in mappings])
        frames = {
            "events": normalized_events,
            "quotes": quotes,
            "trades": trades,
            "easing_mappings": mapping_frame,
            "kalshi_exclusions": exclusions,
        }
        outputs = {name: write_dataframe(frame, name, self.output_root) for name, frame in frames.items()}
        self._write_vali_templates()
        counts = {name: len(frame) for name, frame in frames.items()}
        events_with_quotes = int(quotes["contract_id"].nunique()) if not quotes.empty else 0
        ready = events_with_quotes >= min_events
        extra = {
            "mapped_events": len(mappings),
            "mapped_events_with_quotes": events_with_quotes,
            "minimum_walk_forward_events": min_events,
            "walk_forward_ready": ready,
            "historical_cutoff": cutoff,
            "execution_validation": "unvalidated_no_historical_depth",
            "candle_interval_minutes": candle_interval_minutes,
        }
        self._write_manifest("backfill", outputs, counts, extra)
        return KalshiRunResult(self.output_root, counts, len(mappings), ready)

    def _write_vali_templates(self) -> None:
        manifest_columns = [
            "feature_id",
            "rationale",
            "transformation",
            "polarity",
            "availability_lag_days",
            "missing_policy",
            "max_age_days",
            "required",
            "source",
        ]
        pd.DataFrame(columns=manifest_columns).to_csv(
            self.output_root / "behavior_feature_manifest.template.csv", index=False
        )
        template = '''# Replace the behavioral paths only after the feature universe is frozen.
[run]
parameter_freeze_date = "YYYY-MM-DD"
methodology_version = "1.0.1"

[data]
events = "events.parquet"
quotes = "quotes.parquet"
trades = "trades.parquet"
features = "../behavior/features.parquet"
feature_manifest = "../behavior/feature_manifest.csv"

[market]
max_spread = 0.10
min_depth = 100.0
max_quote_age_minutes = 30
fallback_trade_window_minutes = 120
fee_bps = 0.0 # Execution is disabled until observed depth and Kalshi fees are implemented.
probability_epsilon = 0.0001

[features]
timezone = "America/New_York"
daily_cutoff = "16:00"
standardization_window = 90
min_periods = 30

[signal]
velocity_window = 7
normalization_window = 90
min_periods = 30
entry_threshold = 2.0
exit_threshold = 0.5
sensitivity_windows = [3, 14, 30]

[regime]
window = 90
min_periods = 30
max_lag = 7
min_abs_correlation = 0.20
tie_margin = 0.05

[backtest]
min_train_events = 16
notional = 100.0
stop_loss_fraction = 0.25
max_holding_days = 14
days_before_settlement = 1
calibration_l2 = 1.0
'''
        (self.output_root / "vali_config.template.toml").write_text(
            template, encoding="utf-8"
        )

    def snapshot(self, *, depth_band: Decimal = Decimal("0.05")) -> KalshiRunResult:
        self.output_root.mkdir(parents=True, exist_ok=True)
        settled = self.client.events(self.series_ticker, "settled")
        settled_markets = self._load_markets(settled[:3])
        latest_candidates: list[tuple[pd.Timestamp, Decimal]] = []
        for event in settled[:3]:
            markets = settled_markets.get(str(event["event_ticker"]), [])
            if markets:
                try:
                    latest_candidates.append(
                        (max(_timestamp(m["close_time"]) for m in markets), realized_upper_bound(markets))
                    )
                except KalshiDataError:
                    pass
        if not latest_candidates:
            raise KalshiDataError("Cannot determine current target upper bound from settled KXFED ladders")
        current_upper = max(latest_candidates, key=lambda item: item[0])[1]
        open_markets = self.client.markets(series_ticker=self.series_ticker, status="open")
        if not open_markets:
            raise KalshiDataError("No open KXFED markets")
        next_event = min(open_markets, key=lambda market: _timestamp(market["close_time"]))["event_ticker"]
        ladder = [market for market in open_markets if market["event_ticker"] == next_event]
        strike = current_upper - Decimal("0.25")
        selected = [market for market in ladder if parse_strike(str(market["ticker"])) == strike]
        if len(selected) != 1:
            raise KalshiDataError("Next KXFED ladder lacks the required easing strike")
        source = selected[0]
        open_at, meeting_at, settlement_at = _market_times(source)
        provisional = EasingMapping(
            event_ticker=str(next_event),
            source_ticker=str(source["ticker"]),
            pre_meeting_upper_bound=current_upper,
            strike=strike,
            outcome=0,
            realized_upper_bound=current_upper,
            open_at=open_at,
            meeting_at=meeting_at,
            settlement_at=settlement_at,
        )
        observed = _utc_now()
        run_dir = (
            self.output_root
            / "snapshots"
            / observed.strftime("%Y-%m-%d")
            / observed.strftime("%H%M%SZ")
        )
        run_dir.mkdir(parents=True, exist_ok=True)
        level_frames: list[pd.DataFrame] = []
        normalized_quote: dict[str, Any] | None = None
        for market in ladder:
            book = self.client.orderbook(str(market["ticker"]))
            market_strike = parse_strike(str(market["ticker"]))
            ladder_mapping = EasingMapping(
                event_ticker=str(next_event),
                source_ticker=str(market["ticker"]),
                pre_meeting_upper_bound=current_upper,
                strike=market_strike,
                outcome=0,
                realized_upper_bound=current_upper,
                open_at=open_at,
                meeting_at=meeting_at,
                settlement_at=settlement_at,
            )
            try:
                quote, levels = normalize_orderbook_quote(
                    ladder_mapping, market, book, observed_at=observed, depth_band=depth_band
                )
                level_frames.append(levels)
                if market["ticker"] == source["ticker"]:
                    normalized_quote = quote
            except KalshiDataError:
                continue
        if normalized_quote is None:
            raise KalshiDataError("Required easing market does not have a two-sided order book")
        frames = {
            "quotes": pd.DataFrame([normalized_quote]),
            "orderbook_levels": pd.concat(level_frames, ignore_index=True)
            if level_frames
            else pd.DataFrame(),
            "open_ladder": pd.DataFrame(ladder),
        }
        outputs = {name: write_dataframe(frame, name, run_dir) for name, frame in frames.items()}
        counts = {name: len(frame) for name, frame in frames.items()}
        self._write_manifest(
            "snapshot",
            outputs,
            counts,
            {
                "observed_at": observed.isoformat(),
                "event_ticker": next_event,
                "source_ticker": provisional.source_ticker,
                "pre_meeting_upper_bound": str(current_upper),
                "depth_band": str(depth_band),
            },
            output_dir=run_dir,
        )
        return KalshiRunResult(run_dir, counts, 1, False)

    def _write_manifest(
        self,
        command: str,
        outputs: dict[str, Any],
        counts: dict[str, int],
        extra: dict[str, Any] | None = None,
        output_dir: Path | None = None,
    ) -> dict[str, Any]:
        manifest = {
            "provider": "kalshi",
            "mode": "public_read_only",
            "series_ticker": self.series_ticker,
            "api_spec_version": API_SPEC_VERSION,
            "base_url": self.client.base_url,
            "command": command,
            "created_at": _utc_now().isoformat(),
            "counts": counts,
            "outputs": outputs,
            "credentials_used": False,
            "order_endpoints_present": False,
        }
        manifest.update(extra or {})
        target = output_dir or self.output_root
        target.mkdir(parents=True, exist_ok=True)
        (target / "kalshi_manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True, default=str), encoding="utf-8"
        )
        return manifest


def load_upper_bounds(path: str | Path | None) -> dict[str, Decimal]:
    if path is None:
        return {}
    frame = pd.read_csv(path)
    required = {"event_ticker", "upper_bound"}
    if not required.issubset(frame.columns):
        raise KalshiDataError("Upper-bound CSV requires event_ticker and upper_bound")
    return {str(row.event_ticker): _decimal(row.upper_bound) for row in frame.itertuples(index=False)}
