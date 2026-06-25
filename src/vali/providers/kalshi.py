"""Compatibility facade for read-only Kalshi ingestion and normalization."""

from __future__ import annotations

from decimal import Decimal
import json
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from ..reporting import write_dataframe
from .kalshi_components.archive import ArchiveStore, canonical_bytes
from .kalshi_components.contracts import (
    API_SPEC_VERSION,
    PRODUCTION_BASE_URL,
    SERIES_TICKER,
    EasingMapping,
    KalshiDataError,
    KalshiRunResult,
    Transport,
    utc_now,
)
from .kalshi_components.mapping import (
    STRIKE_PATTERN,
    build_easing_mappings,
    decimal_value,
    load_upper_bounds,
    market_times,
    parse_strike,
    realized_upper_bound,
    timestamp_value,
)
from .kalshi_components.normalization import (
    depth,
    normalize_candlesticks,
    normalize_orderbook_quote,
    normalize_trades,
    normalized_events,
    orderbook_levels,
)
from .kalshi_components.transport import KalshiClient, default_transport


_utc_now = utc_now
_canonical_bytes = canonical_bytes
_decimal = decimal_value
_timestamp = timestamp_value
_default_transport = default_transport
_market_times = market_times
_levels = orderbook_levels
_depth = depth
_normalized_events = normalized_events
_normalize_trades = normalize_trades


class KalshiAdapter:
    def __init__(
        self,
        client: KalshiClient,
        output_root: str | Path,
        series_ticker: str = SERIES_TICKER,
    ):
        self.client = client
        self.output_root = Path(output_root).resolve()
        self.series_ticker = series_ticker

    def discover(self) -> KalshiRunResult:
        self.output_root.mkdir(parents=True, exist_ok=True)
        series = self.client.series(self.series_ticker)
        settled = self.client.events(self.series_ticker, "settled")
        open_events = self.client.events(self.series_ticker, "open")
        open_markets = self.client.markets(
            series_ticker=self.series_ticker, status="open"
        )
        frames = {
            "series": pd.DataFrame([series]),
            "settled_events": pd.DataFrame(settled),
            "open_events": pd.DataFrame(open_events),
            "open_markets": pd.DataFrame(open_markets),
        }
        outputs = {
            name: write_dataframe(frame, name, self.output_root)
            for name, frame in frames.items()
        }
        manifest = self._write_manifest(
            "discover",
            outputs,
            {name: len(frame) for name, frame in frames.items()},
        )
        return KalshiRunResult(
            self.output_root, manifest["counts"], 0, False
        )

    def _load_markets(
        self, events: Iterable[dict[str, Any]]
    ) -> dict[str, list[dict[str, Any]]]:
        return {
            str(event["event_ticker"]): self.client.markets_for_event(
                str(event["event_ticker"])
            )
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
            raise KalshiDataError(
                "Kalshi candle interval must be 1, 60, or 1440 minutes"
            )
        self.output_root.mkdir(parents=True, exist_ok=True)
        cutoff = self.client.historical_cutoff()
        events = self.client.events(self.series_ticker, "settled")
        markets_by_event = self._load_markets(events)
        mappings, exclusions = build_easing_mappings(
            events, markets_by_event, upper_bounds
        )
        cutoff_value = cutoff.get("market_settled_ts") or cutoff.get(
            "cutoff", {}
        ).get("market_settled_ts")
        market_cutoff = (
            _timestamp(cutoff_value)
            if cutoff_value
            else pd.Timestamp.max.tz_localize("UTC")
        )
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
                        mapping,
                        self.client.trades(
                            mapping.source_ticker, historical=historical
                        ),
                    )
                )
        normalized_events_frame = _normalized_events(mappings)
        quotes = (
            pd.concat(quote_frames, ignore_index=True)
            if quote_frames
            else pd.DataFrame()
        )
        trades = (
            pd.concat(trade_frames, ignore_index=True)
            if trade_frames
            else pd.DataFrame()
        )
        mapping_frame = pd.DataFrame(
            [
                mapping.__dict__ | {"contract_id": mapping.contract_id}
                for mapping in mappings
            ]
        )
        frames = {
            "events": normalized_events_frame,
            "quotes": quotes,
            "trades": trades,
            "easing_mappings": mapping_frame,
            "kalshi_exclusions": exclusions,
        }
        outputs = {
            name: write_dataframe(frame, name, self.output_root)
            for name, frame in frames.items()
        }
        self._write_vali_templates()
        counts = {name: len(frame) for name, frame in frames.items()}
        events_with_quotes = (
            int(quotes["contract_id"].nunique()) if not quotes.empty else 0
        )
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
        return KalshiRunResult(
            self.output_root, counts, len(mappings), ready
        )

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
            self.output_root / "behavior_feature_manifest.template.csv",
            index=False,
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
entry_regime_confirmation_periods = 1
exit_regime_confirmation_periods = 1
'''
        (self.output_root / "vali_config.template.toml").write_text(
            template, encoding="utf-8"
        )

    def snapshot(
        self, *, depth_band: Decimal = Decimal("0.05")
    ) -> KalshiRunResult:
        self.output_root.mkdir(parents=True, exist_ok=True)
        settled = self.client.events(self.series_ticker, "settled")
        settled_markets = self._load_markets(settled[:3])
        latest_candidates: list[tuple[pd.Timestamp, Decimal]] = []
        for event in settled[:3]:
            markets = settled_markets.get(str(event["event_ticker"]), [])
            if markets:
                try:
                    latest_candidates.append(
                        (
                            max(
                                _timestamp(market["close_time"])
                                for market in markets
                            ),
                            realized_upper_bound(markets),
                        )
                    )
                except KalshiDataError:
                    pass
        if not latest_candidates:
            raise KalshiDataError(
                "Cannot determine current target upper bound from settled "
                "KXFED ladders"
            )
        current_upper = max(latest_candidates, key=lambda item: item[0])[1]
        open_markets = self.client.markets(
            series_ticker=self.series_ticker, status="open"
        )
        if not open_markets:
            raise KalshiDataError("No open KXFED markets")
        next_event = min(
            open_markets,
            key=lambda market: _timestamp(market["close_time"]),
        )["event_ticker"]
        ladder = [
            market
            for market in open_markets
            if market["event_ticker"] == next_event
        ]
        strike = current_upper - Decimal("0.25")
        selected = [
            market
            for market in ladder
            if parse_strike(str(market["ticker"])) == strike
        ]
        if len(selected) != 1:
            raise KalshiDataError(
                "Next KXFED ladder lacks the required easing strike"
            )
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
                    ladder_mapping,
                    market,
                    book,
                    observed_at=observed,
                    depth_band=depth_band,
                )
                level_frames.append(levels)
                if market["ticker"] == source["ticker"]:
                    normalized_quote = quote
            except KalshiDataError:
                continue
        if normalized_quote is None:
            raise KalshiDataError(
                "Required easing market does not have a two-sided order book"
            )
        frames = {
            "quotes": pd.DataFrame([normalized_quote]),
            "orderbook_levels": (
                pd.concat(level_frames, ignore_index=True)
                if level_frames
                else pd.DataFrame()
            ),
            "open_ladder": pd.DataFrame(ladder),
        }
        outputs = {
            name: write_dataframe(frame, name, run_dir)
            for name, frame in frames.items()
        }
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
            json.dumps(manifest, indent=2, sort_keys=True, default=str),
            encoding="utf-8",
        )
        return manifest


__all__ = [
    "API_SPEC_VERSION",
    "ArchiveStore",
    "EasingMapping",
    "KalshiAdapter",
    "KalshiClient",
    "KalshiDataError",
    "KalshiRunResult",
    "PRODUCTION_BASE_URL",
    "SERIES_TICKER",
    "Transport",
    "build_easing_mappings",
    "load_upper_bounds",
    "normalize_candlesticks",
    "normalize_orderbook_quote",
    "parse_strike",
    "realized_upper_bound",
]
