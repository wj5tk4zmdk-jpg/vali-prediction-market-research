from datetime import date, datetime, timezone
import gzip
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import pandas as pd

from vali.providers import google_trends as legacy
from vali.providers.google_trends_components import client as client_module
from vali.providers.google_trends_components.audit import (
    trends_status as component_trends_status,
)
from vali.providers.google_trends_components.client import (
    RetryingTrendsGateway,
    UnavailableOfficialTrendsGateway,
)
from vali.providers.google_trends_components.contracts import (
    TrendsAccessUnavailable,
    TrendsDataError,
    TrendsGatewayResponse,
    TrendsObservation,
    TrendsQuerySpec,
    TrendsRequest,
    sha256_value,
)
from vali.providers.google_trends_components.fixtures import (
    FixtureTrendsGateway,
)
from vali.providers.google_trends_components.manifest import (
    build_request_plan,
    load_query_manifest,
    query_manifest_frame,
    query_manifest_sha256,
    write_request_plan,
)
from vali.providers.google_trends_components.normalization import (
    feature_manifest_frame,
    normalize_response,
)


FIXTURE = (
    Path(__file__).parents[1]
    / "fixtures"
    / "providers"
    / "google_trends"
    / "interest.json"
)


class GoogleTrendsProviderDecompositionTests(unittest.TestCase):
    def test_legacy_and_component_imports_are_available(self):
        self.assertIs(legacy.TrendsQuerySpec, TrendsQuerySpec)
        self.assertIs(legacy.TrendsRequest, TrendsRequest)
        self.assertIs(legacy.TrendsObservation, TrendsObservation)
        self.assertIs(legacy.TrendsGatewayResponse, TrendsGatewayResponse)
        self.assertIs(legacy.TrendsDataError, TrendsDataError)
        self.assertIs(legacy.FixtureTrendsGateway, FixtureTrendsGateway)
        self.assertIs(
            legacy.RetryingTrendsGateway, RetryingTrendsGateway
        )
        for function in (
            legacy.load_query_manifest,
            load_query_manifest,
            legacy.build_request_plan,
            build_request_plan,
            legacy.normalize_response,
            normalize_response,
            legacy.trends_status,
            component_trends_status,
        ):
            self.assertTrue(callable(function))

    def test_query_manifest_hash_frame_and_active_selection_are_unchanged(self):
        legacy_specs = legacy.load_query_manifest()
        specs = load_query_manifest()

        self.assertEqual(legacy_specs, specs)
        self.assertEqual(
            legacy.query_manifest_sha256(legacy_specs),
            query_manifest_sha256(specs),
        )
        pd.testing.assert_frame_equal(
            legacy.query_manifest_frame(legacy_specs),
            query_manifest_frame(specs),
        )
        self.assertEqual(sum(spec.active for spec in specs), 6)
        self.assertEqual(
            {spec.basket for spec in specs if spec.active},
            {"easing", "tightening"},
        )
        self.assertTrue(
            all(not spec.active for spec in specs if spec.basket == "control")
        )

    def test_request_plan_bytes_and_t_minus_2_boundary_are_unchanged(self):
        specs = load_query_manifest()
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            legacy_path = legacy.write_request_plan(
                root / "legacy",
                specs,
                as_of=date(2026, 6, 23),
                days=30,
            )
            component_path = write_request_plan(
                root / "component",
                specs,
                as_of=date(2026, 6, 23),
                days=30,
            )

            self.assertEqual(
                legacy_path.read_bytes(), component_path.read_bytes()
            )
            payload = json.loads(component_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["latest_requested_date"], "2026-06-21")
            self.assertFalse(payload["unofficial_fallbacks_allowed"])

    def test_fixture_gateway_and_normalized_frames_are_identical(self):
        specs = load_query_manifest()
        request = build_request_plan(
            specs, date(2026, 6, 17), date(2026, 6, 21)
        )[0]
        legacy_response = legacy.FixtureTrendsGateway(FIXTURE).fetch(request)
        response = FixtureTrendsGateway(FIXTURE).fetch(request)

        self.assertEqual(legacy_response, response)
        legacy_frames = legacy.normalize_response(legacy_response, specs)
        frames = normalize_response(response, specs)
        for legacy_frame, frame in zip(legacy_frames, frames):
            pd.testing.assert_frame_equal(legacy_frame, frame)
            self.assertEqual(
                legacy_frame.dtypes.tolist(), frame.dtypes.tolist()
            )
        features, observations, exclusions = frames
        self.assertEqual(features["feature_id"].nunique(), 6)
        self.assertTrue(
            set(features["feature_id"]).isdisjoint(
                {
                    spec.feature_id
                    for spec in specs
                    if not spec.active
                }
            )
        )
        self.assertTrue(
            pd.api.types.is_datetime64_any_dtype(
                observations["retrieved_at"].dtype
            )
        )
        self.assertIsNotNone(observations["retrieved_at"].dt.tz)
        self.assertEqual(set(exclusions["reason"]), {"low_volume", "suppressed"})

    def test_exclusion_audit_and_retrieved_at_utc_are_unchanged(self):
        specs = load_query_manifest()
        response = TrendsGatewayResponse(
            observations=(
                TrendsObservation(
                    "rate_cut", date(2026, 6, 22), 10.0, "available"
                ),
                TrendsObservation(
                    "rate_hike",
                    date(2026, 6, 21),
                    4.0,
                    "available",
                    True,
                ),
                TrendsObservation(
                    "interest_rates_down",
                    date(2026, 6, 20),
                    None,
                    "suppressed",
                ),
            ),
            retrieved_at=datetime(
                2026, 6, 23, 15, tzinfo=timezone.utc
            ),
            request_id="audit-test",
            api_version="fixture-v1",
            raw_payload={},
        )

        legacy_frames = legacy.normalize_response(response, specs)
        frames = normalize_response(response, specs)
        for legacy_frame, frame in zip(legacy_frames, frames):
            pd.testing.assert_frame_equal(legacy_frame, frame)
        exclusions = frames[2]
        self.assertEqual(
            set(exclusions["reason"]),
            {"newer_than_t_minus_2", "partial_period", "suppressed"},
        )
        self.assertTrue(
            pd.api.types.is_datetime64_any_dtype(
                exclusions["retrieved_at"].dtype
            )
        )
        self.assertEqual(str(exclusions["retrieved_at"].dt.tz), "UTC")

    def test_fixture_backfill_artifacts_and_status_are_unchanged(self):
        specs = load_query_manifest()
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = legacy.TrendsAdapter(
                FixtureTrendsGateway(FIXTURE), root
            ).backfill(specs, as_of=date(2026, 6, 23), days=7)

            self.assertEqual(result.counts["features"], 18)
            self.assertEqual(result.counts["observations"], 24)
            self.assertEqual(result.counts["exclusions"], 2)
            expected_names = {
                "features.csv",
                "features.parquet",
                "feature_manifest.csv",
                "feature_manifest.parquet",
                "trends_observations.csv",
                "trends_observations.parquet",
                "trends_exclusions.csv",
                "trends_exclusions.parquet",
                "query_manifest.csv",
                "query_manifest.parquet",
                "trends_run_manifest.json",
                "raw",
            }
            self.assertEqual(
                {path.name for path in root.iterdir()}, expected_names
            )
            self.assertEqual(
                legacy.trends_status(root, specs),
                component_trends_status(root, specs),
            )
            serialized = pd.read_parquet(root / "trends_exclusions.parquet")
            self.assertTrue(
                pd.api.types.is_datetime64_any_dtype(
                    serialized["retrieved_at"].dtype
                )
            )

    def test_archive_hash_and_credential_redaction_are_unchanged(self):
        specs = load_query_manifest()
        request = build_request_plan(
            specs, date(2026, 6, 1), date(2026, 6, 2)
        )[0]
        response = TrendsGatewayResponse(
            observations=(),
            retrieved_at=datetime(2026, 6, 4, tzinfo=timezone.utc),
            request_id="secret-test",
            api_version="fixture-v1",
            raw_payload={"authorization": "secret", "token": "secret"},
        )
        safe_request = legacy.redact_sensitive(request.as_dict())
        safe_payload = legacy.redact_sensitive(response.raw_payload)
        expected_hash = sha256_value(
            {
                "request": safe_request,
                "payload": safe_payload,
                "api_version": response.api_version,
            }
        )

        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = legacy.TrendsArchiveStore(root).record(
                request=request,
                response=response,
                manifest_hash=query_manifest_sha256(specs),
            )
            self.assertEqual(path.name, f"{expected_hash}.json.gz")
            with gzip.open(path, "rt", encoding="utf-8") as handle:
                envelope = json.load(handle)
            self.assertEqual(envelope["content_sha256"], expected_hash)
            serialized = json.dumps(envelope)
            self.assertNotIn('"authorization": "secret"', serialized)
            self.assertNotIn('"token": "secret"', serialized)
            self.assertIn("[REDACTED]", serialized)

    def test_client_module_has_no_live_network_or_credentials(self):
        self.assertTrue(
            {"requests", "urlopen", "urllib", "httpx"}.isdisjoint(
                set(vars(client_module))
            )
        )
        gateway = UnavailableOfficialTrendsGateway()
        specs = load_query_manifest()
        request = build_request_plan(
            specs, date(2026, 6, 1), date(2026, 6, 2)
        )[0]
        with self.assertRaises(TrendsAccessUnavailable):
            gateway.fetch(request)
        self.assertTrue(
            {"api_key", "credentials", "token"}.isdisjoint(
                set(vars(gateway))
            )
        )


if __name__ == "__main__":
    unittest.main()
