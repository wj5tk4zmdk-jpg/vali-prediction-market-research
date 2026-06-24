import unittest

import pandas as pd

from vali.config import (
    ConfigError,
    forbidden_public_input_marker as old_forbidden_marker,
    validate_public_research_config as old_validate_config,
)
from vali.data.contracts import (
    EVENT_COLUMNS,
    FEATURE_COLUMNS,
    MANIFEST_COLUMNS,
    QUOTE_COLUMNS,
    DataValidationError,
    InputBundle,
)
from vali.data.point_in_time import (
    asof_feature_values,
    strictly_prior_rows,
    validate_label_isolation,
)
from vali.data.provenance import (
    forbidden_public_input_marker,
    validate_public_input_boundary,
    validate_public_research_config,
)
from vali.data.validation import (
    validate_event_identity,
    validate_frames as data_validate_frames,
)
from vali.features import _asof_values
from vali.io import (
    DataValidationError as LegacyDataValidationError,
    InputBundle as LegacyInputBundle,
    validate_event_identity as legacy_validate_event_identity,
    validate_frames as legacy_validate_frames,
    validate_public_input_boundary as legacy_validate_public_input_boundary,
)


def valid_frames():
    events = pd.DataFrame(
        [
            {
                "event_id": "event-1",
                "contract_id": "contract-1",
                "open_at": "2025-01-01T14:00:00Z",
                "meeting_at": "2025-02-01T19:00:00Z",
                "settlement_at": "2025-02-01T23:00:00Z",
                "yes_label": "lower",
                "outcome": 1,
            }
        ]
    )
    quotes = pd.DataFrame(
        [
            {
                "contract_id": "contract-1",
                "observed_at": "2025-01-02T20:55:00Z",
                "bid": 0.40,
                "ask": 0.50,
                "last": 0.45,
                "volume": 100,
                "bid_depth": 200,
                "ask_depth": 200,
            }
        ]
    )
    features = pd.DataFrame(
        [
            {
                "feature_id": "public-search",
                "observation_at": "2025-01-02T13:00:00Z",
                "available_at": "2025-01-02T14:00:00Z",
                "vintage": "v1",
                "source": "public_search",
                "value": 1.0,
            }
        ]
    )
    manifest = pd.DataFrame(
        [
            {
                "feature_id": "public-search",
                "rationale": "public attention",
                "transformation": "level",
                "polarity": 1,
                "availability_lag_days": 0,
                "missing_policy": "asof",
                "max_age_days": 2,
                "required": True,
                "source": "public_search",
            }
        ]
    )
    return events, quotes, features, manifest


class DataBoundaryCompatibilityTests(unittest.TestCase):
    def test_contracts_and_legacy_types_are_compatible(self):
        self.assertIn("event_id", EVENT_COLUMNS)
        self.assertIn("bid", QUOTE_COLUMNS)
        self.assertIn("available_at", FEATURE_COLUMNS)
        self.assertIn("missing_policy", MANIFEST_COLUMNS)
        self.assertIs(LegacyDataValidationError, DataValidationError)
        self.assertIs(LegacyInputBundle, InputBundle)

    def test_legacy_and_new_frame_validation_return_identical_bundles(self):
        legacy = legacy_validate_frames(*valid_frames())
        extracted = data_validate_frames(*valid_frames())

        self.assertIsInstance(legacy, InputBundle)
        self.assertEqual(legacy.validation.as_dict(), extracted.validation.as_dict())
        for name in ("events", "quotes", "features", "manifest"):
            pd.testing.assert_frame_equal(getattr(legacy, name), getattr(extracted, name))

    def test_forbidden_input_validation_has_identical_behavior(self):
        self.assertEqual(old_forbidden_marker("PFlow"), forbidden_public_input_marker("PFlow"))
        raw = {"execution_api": {"order_submission_endpoint": "https://example/orders"}}
        with self.assertRaises(ConfigError) as old_error:
            old_validate_config(raw)
        with self.assertRaises(ConfigError) as new_error:
            validate_public_research_config(raw, error_type=ConfigError)
        self.assertEqual(str(old_error.exception), str(new_error.exception))

        frame = pd.DataFrame({"source_classification": ["client_data"]})
        for validator in (
            legacy_validate_public_input_boundary,
            validate_public_input_boundary,
        ):
            with self.assertRaisesRegex(DataValidationError, "client_data"):
                validator(features=frame)

    def test_feature_manifest_failures_are_identical(self):
        events, quotes, features, manifest = valid_frames()
        features.loc[0, "feature_id"] = "post-freeze-feature"
        messages = []
        for validator in (legacy_validate_frames, data_validate_frames):
            with self.assertRaises(DataValidationError) as error:
                validator(events, quotes, features, manifest)
            messages.append(str(error.exception))
        self.assertEqual(messages[0], messages[1])
        self.assertIn("absent from the manifest", messages[0])

    def test_event_identity_failures_are_identical(self):
        events, _, _, _ = valid_frames()
        duplicate = events.copy()
        duplicate["event_id"] = "event-2"
        duplicate["contract_id"] = "contract-2"
        invalid = pd.concat([events, duplicate], ignore_index=True)
        messages = []
        for validator in (legacy_validate_event_identity, validate_event_identity):
            with self.assertRaises(DataValidationError) as error:
                validator(invalid)
            messages.append(str(error.exception))
        self.assertEqual(messages[0], messages[1])
        self.assertIn("duplicate internal EASING", messages[0])

    def test_point_in_time_wrapper_and_new_helpers_match(self):
        cutoffs = pd.Series(pd.date_range("2025-01-03 21:00", periods=3, freq="D", tz="UTC"))
        rows = pd.DataFrame(
            [
                {
                    "observation_at": cutoff - pd.Timedelta(hours=2),
                    "available_at": cutoff - pd.Timedelta(hours=1),
                    "vintage": "initial",
                    "value": float(index),
                }
                for index, cutoff in enumerate(cutoffs)
            ]
        )
        pd.testing.assert_series_equal(
            _asof_values(rows, cutoffs, 0, "asof", 1),
            asof_feature_values(rows, cutoffs, 0, "asof", 1),
        )

        timeline = pd.DataFrame({"meeting_at": cutoffs})
        prior = strictly_prior_rows(timeline, "meeting_at", cutoffs.iloc[2])
        self.assertEqual(len(prior), 2)
        validate_label_isolation(pd.DataFrame({"signal": [1.0]}))
        with self.assertRaisesRegex(DataValidationError, "evaluation labels"):
            validate_label_isolation(pd.DataFrame({"outcome": [1]}))


if __name__ == "__main__":
    unittest.main()
