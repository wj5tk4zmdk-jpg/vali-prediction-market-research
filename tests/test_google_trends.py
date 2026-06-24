from dataclasses import replace
from contextlib import redirect_stdout
from datetime import date, datetime, time, timedelta, timezone
import gzip
from io import StringIO
import json
import math
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import pandas as pd

from vali.config import FeatureConfig, ValiConfig
from vali.cli import main as cli_main
from vali.features import build_attention_index
from vali.pipeline import run_backtest_pipeline
from vali.providers.google_trends import (
    FixtureTrendsGateway,
    RetryingTrendsGateway,
    TrendsAdapter,
    TrendsArchiveStore,
    TrendsDataError,
    TrendsGatewayResponse,
    TrendsObservation,
    TrendsRateLimitError,
    UnavailableOfficialTrendsGateway,
    build_request_plan,
    feature_manifest_frame,
    load_query_manifest,
    normalize_response,
    redact_sensitive,
    trends_status,
    validate_query_manifest,
    write_request_plan,
)


FIXTURE = Path(__file__).parent / "fixtures" / "google_trends" / "interest.json"


class GoogleTrendsManifestTests(unittest.TestCase):
    def test_packaged_manifest_is_balanced_and_controls_are_inactive(self):
        specs = load_query_manifest()
        active = [spec for spec in specs if spec.active]
        self.assertEqual(len(active), 6)
        self.assertEqual(sum(spec.basket == "easing" for spec in active), 3)
        self.assertEqual(sum(spec.basket == "tightening" for spec in active), 3)
        self.assertTrue(all(not spec.active for spec in specs if spec.basket == "control"))

    def test_unbalanced_active_manifest_is_rejected(self):
        specs = list(load_query_manifest())
        specs[0] = replace(specs[0], active=False, required=False)
        with self.assertRaisesRegex(TrendsDataError, "balanced"):
            validate_query_manifest(specs)

    def test_request_plan_is_deterministic_and_ends_at_t_minus_2(self):
        specs = load_query_manifest()
        with TemporaryDirectory() as temporary:
            first = write_request_plan(temporary, specs, as_of=date(2026, 6, 23), days=30)
            content = first.read_bytes()
            second = write_request_plan(temporary, specs, as_of=date(2026, 6, 23), days=30)
            self.assertEqual(content, second.read_bytes())
            payload = json.loads(content)
            self.assertEqual(payload["latest_requested_date"], "2026-06-21")
            self.assertFalse(payload["unofficial_fallbacks_allowed"])

    def test_cli_plan_runs_without_credentials_and_live_backfill_fails_closed(self):
        with TemporaryDirectory() as temporary:
            output = StringIO()
            with redirect_stdout(output):
                cli_main(
                    [
                        "trends",
                        "plan",
                        "--out",
                        temporary,
                        "--as-of",
                        "2026-06-23",
                        "--days",
                        "30",
                    ]
                )
            self.assertTrue((Path(temporary) / "request_plan.json").exists())
            self.assertFalse(json.loads(output.getvalue())["live_access_used"])
            with self.assertRaisesRegex(SystemExit, "Official Google Trends API alpha access"):
                cli_main(
                    [
                        "trends",
                        "backfill",
                        "--out",
                        temporary,
                        "--as-of",
                        "2026-06-23",
                        "--days",
                        "7",
                    ]
                )


class GoogleTrendsGatewayTests(unittest.TestCase):
    def test_fixture_backfill_emits_only_active_features_and_complete_audit(self):
        specs = load_query_manifest()
        with TemporaryDirectory() as temporary:
            adapter = TrendsAdapter(FixtureTrendsGateway(FIXTURE), temporary)
            result = adapter.backfill(specs, as_of=date(2026, 6, 23), days=7)
            self.assertEqual(result.counts["features"], 18)
            features = pd.read_csv(Path(temporary) / "features.csv")
            manifest = pd.read_csv(Path(temporary) / "feature_manifest.csv")
            observations = pd.read_csv(Path(temporary) / "trends_observations.csv")
            self.assertEqual(features["feature_id"].nunique(), 6)
            self.assertTrue((manifest["transformation"] == "log1p").all())
            self.assertEqual(len(observations), 24)
            status = trends_status(temporary, specs)
            self.assertEqual(status["latest_usable_date"], "2026-06-21")
            self.assertEqual(status["low_volume_observations"], 1)
            self.assertEqual(status["suppressed_observations"], 1)
            baseline = (Path(temporary) / "features.csv").read_bytes()
            adapter.backfill(specs, as_of=date(2026, 6, 23), days=7)
            self.assertEqual(baseline, (Path(temporary) / "features.csv").read_bytes())
            collected = adapter.collect(
                specs, as_of=date(2026, 6, 23), lookback_days=7
            )
            self.assertEqual(collected.counts["features"], 18)
            self.assertEqual(collected.counts["observations"], 24)
            serialized_exclusions = pd.read_parquet(
                Path(temporary) / "trends_exclusions.parquet"
            )
            self.assertTrue(
                pd.api.types.is_datetime64_any_dtype(
                    serialized_exclusions["retrieved_at"].dtype
                )
            )
            self.assertEqual(len(list((Path(temporary) / "raw").rglob("*.json.gz"))), 1)

    def test_partial_and_newer_than_t_minus_2_rows_are_rejected(self):
        specs = load_query_manifest()
        response = TrendsGatewayResponse(
            observations=(
                TrendsObservation("rate_cut", date(2026, 6, 22), 10.0, "available"),
                TrendsObservation("rate_hike", date(2026, 6, 21), 4.0, "available", True),
                TrendsObservation("interest_rates_down", date(2026, 6, 20), None, "suppressed"),
            ),
            retrieved_at=datetime(2026, 6, 23, 15, tzinfo=timezone.utc),
            request_id="t2-test",
            api_version="fixture-v1",
            raw_payload={},
        )
        features, _, exclusions = normalize_response(response, specs)
        self.assertTrue(features.empty)
        self.assertEqual(
            set(exclusions["reason"]),
            {"newer_than_t_minus_2", "partial_period", "suppressed"},
        )

    def test_retry_wrapper_retries_only_transient_failures(self):
        specs = load_query_manifest()
        request = build_request_plan(specs, date(2026, 6, 1), date(2026, 6, 2))[0]
        response = TrendsGatewayResponse(
            observations=(),
            retrieved_at=datetime(2026, 6, 4, tzinfo=timezone.utc),
            request_id="retry",
            api_version="fixture-v1",
            raw_payload={},
        )

        class FlakyGateway:
            def __init__(self):
                self.calls = 0

            def fetch(self, _request):
                self.calls += 1
                if self.calls == 1:
                    raise TrendsRateLimitError("429")
                return response

        sleeps = []
        flaky = FlakyGateway()
        returned = RetryingTrendsGateway(flaky, max_retries=2, sleeper=sleeps.append).fetch(request)
        self.assertIs(returned, response)
        self.assertEqual(flaky.calls, 2)
        self.assertEqual(sleeps, [0.5])
        with self.assertRaisesRegex(Exception, "not configured"):
            RetryingTrendsGateway(UnavailableOfficialTrendsGateway()).fetch(request)

    def test_archive_redacts_credentials(self):
        specs = load_query_manifest()
        request = build_request_plan(specs, date(2026, 6, 1), date(2026, 6, 2))[0]
        response = TrendsGatewayResponse(
            observations=(),
            retrieved_at=datetime(2026, 6, 4, tzinfo=timezone.utc),
            request_id="secret-test",
            api_version="fixture-v1",
            raw_payload={"authorization": "Bearer SUPERSECRET", "nested": {"token": "SUPERSECRET"}},
        )
        with TemporaryDirectory() as temporary:
            path = TrendsArchiveStore(temporary).record(
                request=request, response=response, manifest_hash="manifest"
            )
            with gzip.open(path, "rt", encoding="utf-8") as handle:
                archived = handle.read()
            self.assertNotIn("SUPERSECRET", archived)
            self.assertIn("[REDACTED]", archived)
        self.assertEqual(redact_sensitive({"api_key": "x"}), {"api_key": "[REDACTED]"})


class GoogleTrendsLeakageTests(unittest.TestCase):
    def test_future_revision_cannot_change_earlier_attention(self):
        specs = load_query_manifest()
        active = [spec for spec in specs if spec.active]
        start = date(2025, 1, 1)
        feature_frames = []
        cutoffs = []
        for index in range(45):
            observation_date = start + timedelta(days=index)
            retrieved_at = datetime.combine(
                observation_date + timedelta(days=2), time(15), tzinfo=timezone.utc
            )
            observations = []
            for offset, spec in enumerate(active):
                direction = 1 if spec.polarity == 1 else -1
                value = 30 + direction * 5 * math.sin(index / 6) + offset
                observations.append(
                    TrendsObservation(spec.query_id, observation_date, value, "available")
                )
            response = TrendsGatewayResponse(
                observations=tuple(observations),
                retrieved_at=retrieved_at,
                request_id=f"daily-{index}",
                api_version="fixture-v1",
                raw_payload={},
            )
            features, _, _ = normalize_response(response, specs)
            feature_frames.append(features)
            cutoffs.append(retrieved_at + timedelta(hours=5))
        feature_frame = pd.concat(feature_frames, ignore_index=True)
        manifest = feature_manifest_frame(specs)
        baseline, _ = build_attention_index(
            feature_frame,
            manifest,
            pd.DatetimeIndex(cutoffs),
            FeatureConfig(standardization_window=20, min_periods=5),
        )
        revision = TrendsGatewayResponse(
            observations=(TrendsObservation("rate_cut", start + timedelta(days=40), 999.0, "available"),),
            retrieved_at=cutoffs[-1] + timedelta(days=1),
            request_id="future-revision",
            api_version="fixture-v1",
            raw_payload={},
        )
        revised_features, _, _ = normalize_response(revision, specs)
        revised, _ = build_attention_index(
            pd.concat([feature_frame, revised_features], ignore_index=True),
            manifest,
            pd.DatetimeIndex(cutoffs),
            FeatureConfig(standardization_window=20, min_periods=5),
        )
        pd.testing.assert_series_equal(
            baseline["attention"], revised["attention"], check_names=False
        )


class GoogleTrendsPipelineTests(unittest.TestCase):
    def test_normalized_trends_features_run_through_backtest_pipeline(self):
        specs = load_query_manifest()
        active = [spec for spec in specs if spec.active]
        with TemporaryDirectory() as temporary:
            root = Path(temporary) / "dataset"
            root.mkdir()
            first_meeting = datetime(2025, 5, 1, 18, tzinfo=timezone.utc)
            meetings = [first_meeting + timedelta(days=5 * index) for index in range(18)]
            event_rows = []
            quote_rows = []
            for index, meeting in enumerate(meetings):
                contract_id = f"ease-{index:02d}"
                open_at = meeting - timedelta(days=60)
                event_rows.append(
                    {
                        "event_id": f"fomc-{index:02d}",
                        "contract_id": contract_id,
                        "open_at": open_at.isoformat(),
                        "meeting_at": meeting.isoformat(),
                        "settlement_at": (meeting + timedelta(hours=4)).isoformat(),
                        "yes_label": "Fed target range lower after scheduled meeting",
                        "outcome": index % 2,
                    }
                )
                for quote_day in pd.date_range(open_at.date(), meeting.date(), freq="D"):
                    center = 0.50 + 0.10 * math.sin((quote_day.dayofyear + index) / 11)
                    quote_rows.append(
                        {
                            "contract_id": contract_id,
                            "observed_at": datetime.combine(
                                quote_day.date(), time(19, 55), tzinfo=timezone.utc
                            ).isoformat(),
                            "bid": center - 0.02,
                            "ask": center + 0.02,
                            "last": center,
                            "volume": 1000,
                            "bid_depth": 500,
                            "ask_depth": 500,
                        }
                    )
            pd.DataFrame(event_rows).to_csv(root / "events.csv", index=False)
            pd.DataFrame(quote_rows).to_csv(root / "quotes.csv", index=False)
            quote_dates = pd.to_datetime(
                pd.DataFrame(quote_rows)["observed_at"], utc=True
            ).dt.date
            start = min(quote_dates)
            end = max(quote_dates)
            rows = []
            for index, retrieval_date in enumerate(
                pd.date_range(start, end, freq="D").date
            ):
                observation_date = retrieval_date - timedelta(days=2)
                retrieved_at = datetime.combine(retrieval_date, time(15), tzinfo=timezone.utc)
                observations = []
                for offset, spec in enumerate(active):
                    directional = 1 if spec.polarity == 1 else -1
                    value = 45 + directional * 12 * math.sin(index / 17) + offset
                    observations.append(
                        TrendsObservation(spec.query_id, observation_date, value, "available")
                    )
                response = TrendsGatewayResponse(
                    observations=tuple(observations),
                    retrieved_at=retrieved_at,
                    request_id=f"forward-{index}",
                    api_version="fixture-v1",
                    raw_payload={},
                )
                features, _, _ = normalize_response(response, specs)
                rows.append(features)
            pd.concat(rows, ignore_index=True).to_csv(root / "features.csv", index=False)
            feature_manifest_frame(specs).to_csv(root / "feature_manifest.csv", index=False)
            config_path = root / "config.toml"
            config_path.write_text(
                '''[run]
parameter_freeze_date = "2026-06-23"
methodology_version = "1.0.1"

[data]
events = "events.csv"
quotes = "quotes.csv"
features = "features.csv"
feature_manifest = "feature_manifest.csv"

[market]
max_spread = 0.10
min_depth = 100.0
max_quote_age_minutes = 30
fallback_trade_window_minutes = 120
fee_bps = 5.0

[features]
standardization_window = 30
min_periods = 10

[signal]
velocity_window = 7
normalization_window = 30
min_periods = 10
entry_threshold = 2.0
exit_threshold = 0.5
sensitivity_windows = [3, 14, 30]

[regime]
window = 30
min_periods = 10
max_lag = 3
min_abs_correlation = 0.20
tie_margin = 0.05

[backtest]
min_train_events = 16
notional = 100.0
stop_loss_fraction = 0.25
max_holding_days = 14
days_before_settlement = 1
calibration_l2 = 1.0
''',
                encoding="utf-8",
            )
            config = ValiConfig.from_toml(config_path)
            result = run_backtest_pipeline(config, Path(temporary) / "run")
            self.assertGreater(len(result.signals), 0)
            self.assertGreater(len(result.forecasts), 0)
            self.assertTrue((Path(temporary) / "run" / "report.html").exists())


if __name__ == "__main__":
    unittest.main()
