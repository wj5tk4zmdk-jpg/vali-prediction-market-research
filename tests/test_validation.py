import unittest

import pandas as pd

from vali.io import DataValidationError, validate_frames


def valid_frames():
    events = pd.DataFrame(
        [{"event_id": "e1", "contract_id": "c1", "open_at": "2025-01-01T14:00:00Z", "meeting_at": "2025-02-01T19:00:00Z", "settlement_at": "2025-02-01T23:00:00Z", "yes_label": "lower", "outcome": 1}]
    )
    quotes = pd.DataFrame(
        [{"contract_id": "c1", "observed_at": "2025-01-02T20:55:00Z", "bid": 0.4, "ask": 0.5, "last": 0.45, "volume": 100, "bid_depth": 200, "ask_depth": 200}]
    )
    features = pd.DataFrame(
        [{"feature_id": "f1", "observation_at": "2025-01-02T13:00:00Z", "available_at": "2025-01-02T14:00:00Z", "vintage": "v1", "source": "test", "value": 1.0}]
    )
    manifest = pd.DataFrame(
        [{"feature_id": "f1", "rationale": "test", "transformation": "level", "polarity": 1, "availability_lag_days": 0, "missing_policy": "asof", "max_age_days": 2, "required": True, "source": "test"}]
    )
    return events, quotes, features, manifest


class ValidationTests(unittest.TestCase):
    def test_schema_validates(self):
        bundle = validate_frames(*valid_frames())
        self.assertEqual(bundle.validation.rows["events"], 1)

    def test_duplicate_quote_is_rejected(self):
        events, quotes, features, manifest = valid_frames()
        quotes = pd.concat([quotes, quotes], ignore_index=True)
        with self.assertRaises(DataValidationError):
            validate_frames(events, quotes, features, manifest)

    def test_post_settlement_quote_is_rejected(self):
        events, quotes, features, manifest = valid_frames()
        quotes.loc[0, "observed_at"] = "2025-02-02T00:00:00Z"
        with self.assertRaises(DataValidationError):
            validate_frames(events, quotes, features, manifest)

    def test_timezone_free_timestamp_is_rejected(self):
        events, quotes, features, manifest = valid_frames()
        quotes.loc[0, "observed_at"] = "2025-01-02 20:55:00"
        with self.assertRaises(DataValidationError):
            validate_frames(events, quotes, features, manifest)


if __name__ == "__main__":
    unittest.main()
