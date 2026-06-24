import gzip
import json
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from urllib.error import HTTPError

from vali.providers.kalshi import (
    ArchiveStore,
    KalshiAdapter,
    EasingMapping,
    KalshiClient,
    KalshiDataError,
    build_easing_mappings,
    normalize_candlesticks,
    normalize_orderbook_quote,
    realized_upper_bound,
)


FIXTURES = Path(__file__).parents[1] / "fixtures" / "providers" / "kalshi"


def fixture(name):
    return json.loads((FIXTURES / name).read_text())


class KalshiMappingTests(unittest.TestCase):
    def test_threshold_ladders_map_to_easing_contracts(self):
        events = fixture("events.json")["events"]
        markets = fixture("markets.json")
        mappings, exclusions = build_easing_mappings(events, markets)
        self.assertEqual(len(mappings), 2)
        self.assertEqual(mappings[0].event_ticker, "KXFED-25MAR")
        self.assertEqual(mappings[0].source_ticker, "KXFED-25MAR-T4.25")
        self.assertEqual(mappings[0].outcome, 1)
        self.assertEqual(mappings[1].source_ticker, "KXFED-25MAY-T4.00")
        self.assertEqual(mappings[1].outcome, 0)
        self.assertIn("missing_pre_meeting_upper_bound", set(exclusions["reason"]))

    def test_non_monotone_ladder_is_rejected(self):
        markets = fixture("markets.json")["KXFED-25MAR"]
        broken = [dict(market) for market in markets]
        broken[-1]["result"] = "yes"
        with self.assertRaises(KalshiDataError):
            realized_upper_bound(broken)

    def test_candlestick_inverts_yes_quotes_without_faking_depth(self):
        mapping = build_easing_mappings(
            fixture("events.json")["events"], fixture("markets.json")
        )[0][-1]
        frame = normalize_candlesticks(mapping, fixture("candlesticks.json")["candlesticks"])
        self.assertAlmostEqual(frame.iloc[0]["bid"], 0.35)
        self.assertAlmostEqual(frame.iloc[0]["ask"], 0.40)
        self.assertAlmostEqual(frame.iloc[0]["last"], 0.38)
        self.assertFalse(frame.iloc[0]["depth_observed"])
        self.assertTrue(frame.iloc[0][["bid_depth", "ask_depth"]].isna().all())

    def test_legacy_historical_candlestick_schema_is_supported(self):
        mapping = build_easing_mappings(
            fixture("events.json")["events"], fixture("markets.json")
        )[0][-1]
        candle = {
            "end_period_ts": 1746460800,
            "yes_bid": {"close": "0.6000"},
            "yes_ask": {"close": "0.6500"},
            "price": {"close": "0.6200"},
            "volume": "125.50",
            "open_interest": "80.25",
        }
        frame = normalize_candlesticks(mapping, [candle])
        self.assertAlmostEqual(frame.iloc[0]["bid"], 0.35)
        self.assertAlmostEqual(frame.iloc[0]["ask"], 0.40)
        self.assertAlmostEqual(frame.iloc[0]["volume"], 125.5)

    def test_orderbook_inversion_and_depth(self):
        mapping = EasingMapping(
            event_ticker="KXFED-25MAY",
            source_ticker="KXFED-25MAY-T4.00",
            pre_meeting_upper_bound=Decimal("4.25"),
            strike=Decimal("4.00"),
            outcome=0,
            realized_upper_bound=Decimal("4.25"),
            open_at="2025-03-20T14:00:00+00:00",
            meeting_at="2025-05-07T18:00:00+00:00",
            settlement_at="2025-05-14T18:05:00+00:00",
        )
        market = fixture("markets.json")["KXFED-25MAY"][0]
        quote, levels = normalize_orderbook_quote(
            mapping, market, fixture("orderbook.json"), depth_band=Decimal("0.05")
        )
        self.assertAlmostEqual(quote["bid"], 0.35)
        self.assertAlmostEqual(quote["ask"], 0.40)
        self.assertAlmostEqual(quote["bid_depth"], 13.25)
        self.assertAlmostEqual(quote["ask_depth"], 8.0)
        self.assertTrue(quote["depth_observed"])
        self.assertEqual(len(levels), 4)


class KalshiClientTests(unittest.TestCase):
    def test_pagination_and_retry(self):
        calls = []
        sleeps = []

        def transport(url, timeout):
            calls.append(url)
            if len(calls) == 1:
                raise HTTPError(url, 429, "rate limit", {}, None)
            if "cursor=next" in url:
                return json.dumps({"events": [{"event_ticker": "e2"}], "cursor": ""}).encode()
            return json.dumps({"events": [{"event_ticker": "e1"}], "cursor": "next"}).encode()

        client = KalshiClient(
            "https://example.invalid/trade-api/v2",
            transport=transport,
            sleeper=sleeps.append,
            max_retries=2,
        )
        rows = client.paginate("events", collection="events", params={"series_ticker": "KXFED"})
        self.assertEqual([row["event_ticker"] for row in rows], ["e1", "e2"])
        self.assertEqual(len(sleeps), 1)

    def test_archive_is_content_addressed_and_idempotent(self):
        with TemporaryDirectory() as temporary:
            store = ArchiveStore(temporary)
            first = store.record(url="https://example.invalid/x", payload={"b": 2, "a": 1})
            second = store.record(url="https://example.invalid/x", payload={"a": 1, "b": 2})
            self.assertEqual(first, second)
            self.assertEqual(len(list(Path(temporary).rglob("*.json.gz"))), 1)
            with gzip.open(first, "rt", encoding="utf-8") as handle:
                envelope = json.load(handle)
            self.assertEqual(envelope["api_spec_version"], "3.22.0")
            self.assertEqual(envelope["payload"], {"a": 1, "b": 2})

    def test_long_candlestick_ranges_are_chunked_and_deduplicated(self):
        calls = []

        def transport(url, timeout):
            calls.append(url)
            timestamp = 100 if len(calls) == 1 else 200
            return json.dumps({"candlesticks": [{"end_period_ts": timestamp}]}).encode()

        client = KalshiClient("https://example.invalid", transport=transport)
        candles = client.candlesticks(
            ticker="KXFED-X-T4.00",
            start_ts=0,
            end_ts=60 * 60 * 4001,
            historical=True,
            period_interval=60,
        )
        self.assertEqual(len(calls), 2)
        self.assertEqual([candle["end_period_ts"] for candle in candles], [100, 200])


class KalshiAdapterTests(unittest.TestCase):
    def test_recorded_fixture_backfill_enforces_read_only_execution_state(self):
        class FixtureClient:
            base_url = "https://example.invalid/trade-api/v2"

            def historical_cutoff(self):
                return {"market_settled_ts": "2026-01-01T00:00:00Z"}

            def events(self, ticker, status):
                return fixture("events.json")["events"]

            def markets_for_event(self, event_ticker):
                return fixture("markets.json")[event_ticker]

            def candlesticks(self, **kwargs):
                self.last_candle_kwargs = kwargs
                return fixture("candlesticks.json")["candlesticks"]

            def trades(self, ticker, historical):
                return fixture("trades.json")["trades"]

        with TemporaryDirectory() as temporary:
            client = FixtureClient()
            result = KalshiAdapter(client, temporary).backfill(min_events=2)
            self.assertTrue(result.walk_forward_ready)
            self.assertEqual(result.mapped_events, 2)
            self.assertEqual(result.counts["quotes"], 2)
            self.assertEqual(result.counts["trades"], 2)
            manifest = json.loads((Path(temporary) / "kalshi_manifest.json").read_text())
            self.assertEqual(manifest["execution_validation"], "unvalidated_no_historical_depth")
            self.assertEqual(manifest["candle_interval_minutes"], 60)
            self.assertFalse(manifest["credentials_used"])
            self.assertFalse(manifest["order_endpoints_present"])
            self.assertTrue((Path(temporary) / "vali_config.template.toml").exists())
            self.assertTrue(
                (Path(temporary) / "behavior_feature_manifest.template.csv").exists()
            )


if __name__ == "__main__":
    unittest.main()
