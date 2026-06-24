from datetime import datetime, timezone
from decimal import Decimal
import gzip
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from urllib.error import HTTPError

import pandas as pd

from vali.providers import kalshi as legacy
from vali.providers.kalshi_components.archive import (
    ArchiveStore,
    canonical_bytes,
)
from vali.providers.kalshi_components.contracts import (
    API_SPEC_VERSION,
    EasingMapping,
    KalshiDataError,
    KalshiRunResult,
)
from vali.providers.kalshi_components.mapping import (
    build_easing_mappings,
    parse_strike,
    realized_upper_bound,
)
from vali.providers.kalshi_components.normalization import (
    normalize_candlesticks,
    normalize_orderbook_quote,
    normalize_trades,
    normalized_events,
)
from vali.providers.kalshi_components.transport import KalshiClient


FIXTURES = Path(__file__).parents[1] / "fixtures" / "providers" / "kalshi"


def fixture(name: str):
    return json.loads((FIXTURES / name).read_text())


def fixture_mapping() -> EasingMapping:
    return build_easing_mappings(
        fixture("events.json")["events"], fixture("markets.json")
    )[0][-1]


class KalshiProviderDecompositionTests(unittest.TestCase):
    def test_legacy_and_component_imports_are_available(self):
        self.assertIs(legacy.ArchiveStore, ArchiveStore)
        self.assertIs(legacy.EasingMapping, EasingMapping)
        self.assertIs(legacy.KalshiClient, KalshiClient)
        self.assertIs(legacy.KalshiDataError, KalshiDataError)
        self.assertIs(legacy.KalshiRunResult, KalshiRunResult)
        self.assertEqual(legacy.API_SPEC_VERSION, API_SPEC_VERSION)
        for function in (
            legacy.build_easing_mappings,
            build_easing_mappings,
            legacy.normalize_candlesticks,
            normalize_candlesticks,
            legacy.normalize_orderbook_quote,
            normalize_orderbook_quote,
            legacy.realized_upper_bound,
            realized_upper_bound,
            legacy.parse_strike,
            parse_strike,
        ):
            self.assertTrue(callable(function))

    def test_mapping_facade_and_component_outputs_are_identical(self):
        events = fixture("events.json")["events"]
        markets = fixture("markets.json")

        legacy_mappings, legacy_exclusions = legacy.build_easing_mappings(
            events, markets
        )
        mappings, exclusions = build_easing_mappings(events, markets)

        self.assertEqual(legacy_mappings, mappings)
        pd.testing.assert_frame_equal(legacy_exclusions, exclusions)
        self.assertEqual(
            legacy.realized_upper_bound(markets["KXFED-25MAY"]),
            realized_upper_bound(markets["KXFED-25MAY"]),
        )
        self.assertEqual(
            legacy.parse_strike("KXFED-25MAY-T4.00"), Decimal("4.00")
        )

    def test_normalized_quote_frames_and_dtypes_are_identical(self):
        mapping = fixture_mapping()
        candles = fixture("candlesticks.json")["candlesticks"]

        legacy_quotes = legacy.normalize_candlesticks(mapping, candles)
        quotes = normalize_candlesticks(mapping, candles)

        pd.testing.assert_frame_equal(legacy_quotes, quotes)
        self.assertEqual(legacy_quotes.dtypes.tolist(), quotes.dtypes.tolist())
        self.assertFalse(quotes["depth_observed"].any())
        self.assertTrue(quotes[["bid_depth", "ask_depth"]].isna().all().all())

    def test_normalized_orderbook_and_depth_are_identical(self):
        mapping = fixture_mapping()
        market = fixture("markets.json")[mapping.event_ticker][0]
        observed_at = datetime(2026, 6, 23, 20, 0, tzinfo=timezone.utc)

        legacy_quote, legacy_levels = legacy.normalize_orderbook_quote(
            mapping,
            market,
            fixture("orderbook.json"),
            observed_at=observed_at,
            depth_band=Decimal("0.05"),
        )
        quote, levels = normalize_orderbook_quote(
            mapping,
            market,
            fixture("orderbook.json"),
            observed_at=observed_at,
            depth_band=Decimal("0.05"),
        )

        self.assertEqual(legacy_quote, quote)
        pd.testing.assert_frame_equal(legacy_levels, levels)
        self.assertEqual(quote["bid_depth"], 13.25)
        self.assertEqual(quote["ask_depth"], 8.0)

    def test_event_and_trade_normalization_are_identical(self):
        mappings = build_easing_mappings(
            fixture("events.json")["events"], fixture("markets.json")
        )[0]
        mapping = mappings[-1]

        pd.testing.assert_frame_equal(
            legacy._normalized_events(mappings), normalized_events(mappings)
        )
        pd.testing.assert_frame_equal(
            legacy._normalize_trades(
                mapping, fixture("trades.json")["trades"]
            ),
            normalize_trades(mapping, fixture("trades.json")["trades"]),
        )

    def test_archive_path_name_hash_and_envelope_are_unchanged(self):
        payload = {"b": 2, "a": 1}
        retrieved_at = datetime(
            2026, 6, 23, 20, 15, 30, tzinfo=timezone.utc
        )
        digest = hashlib.sha256(canonical_bytes(payload)).hexdigest()

        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            legacy_path = legacy.ArchiveStore(root / "legacy").record(
                url="https://example.invalid/x",
                payload=payload,
                retrieved_at=retrieved_at,
            )
            component_path = ArchiveStore(root / "component").record(
                url="https://example.invalid/x",
                payload=payload,
                retrieved_at=retrieved_at,
            )

            self.assertEqual(
                legacy_path.relative_to(root / "legacy"),
                component_path.relative_to(root / "component"),
            )
            self.assertEqual(
                component_path.relative_to(root / "component").as_posix(),
                f"raw/kalshi/2026/06/23/{digest}.json.gz",
            )
            with gzip.open(legacy_path, "rt", encoding="utf-8") as handle:
                legacy_envelope = json.load(handle)
            with gzip.open(component_path, "rt", encoding="utf-8") as handle:
                component_envelope = json.load(handle)
            self.assertEqual(legacy_envelope, component_envelope)
            self.assertEqual(component_envelope["content_sha256"], digest)

    def test_pagination_retry_behavior_is_unchanged(self):
        def exercise(client_class):
            calls = []
            sleeps = []

            def transport(url, timeout):
                calls.append((url, timeout))
                if len(calls) == 1:
                    raise HTTPError(url, 429, "rate limit", {}, None)
                if "cursor=next" in url:
                    return json.dumps(
                        {"events": [{"event_ticker": "e2"}], "cursor": ""}
                    ).encode()
                return json.dumps(
                    {
                        "events": [{"event_ticker": "e1"}],
                        "cursor": "next",
                    }
                ).encode()

            client = client_class(
                "https://example.invalid/trade-api/v2",
                transport=transport,
                sleeper=sleeps.append,
                max_retries=2,
            )
            rows = client.paginate(
                "events",
                collection="events",
                params={"series_ticker": "KXFED"},
            )
            return rows, calls, sleeps

        legacy_result = exercise(legacy.KalshiClient)
        component_result = exercise(KalshiClient)
        self.assertEqual(legacy_result, component_result)
        self.assertEqual(len(component_result[2]), 1)

    def test_client_has_no_credentials_or_order_submission_interface(self):
        forbidden = {
            "api_key",
            "cancel_order",
            "create_order",
            "place_order",
            "submit_order",
        }
        self.assertTrue(forbidden.isdisjoint(set(dir(KalshiClient))))
        client = KalshiClient(
            "https://example.invalid",
            transport=lambda url, timeout: b"{}",
        )
        self.assertTrue(forbidden.isdisjoint(set(vars(client))))


if __name__ == "__main__":
    unittest.main()
