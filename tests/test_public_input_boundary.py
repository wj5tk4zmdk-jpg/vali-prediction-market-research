import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from vali.config import ConfigError, DataConfig, MarketConfig, ValiConfig
from vali.io import DataValidationError, validate_frames
from vali.sample import make_synthetic_dataset


def public_frames():
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
                "rationale": "public behavioral attention",
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


class PublicInputBoundaryTests(unittest.TestCase):
    def test_forbidden_source_classifications_are_rejected(self):
        forbidden = (
            "private",
            "proprietary",
            "client_data",
            "order_flow",
            "pending_order",
            "product_launch",
            "credentialed_trading",
            "execution_api",
            "P_flow",
        )
        for classification in forbidden:
            with self.subTest(classification=classification):
                events, quotes, features, manifest = public_frames()
                manifest["source_classification"] = classification
                with self.assertRaisesRegex(DataValidationError, "public-input boundary"):
                    validate_frames(events, quotes, features, manifest)

    def test_disguised_flow_and_non_public_metadata_are_rejected(self):
        events, quotes, features, manifest = public_frames()
        quotes["FlowProbability"] = 0.55
        with self.assertRaisesRegex(DataValidationError, "FlowProbability"):
            validate_frames(events, quotes, features, manifest)

        events, quotes, features, manifest = public_frames()
        quotes["provider_metadata"] = '{"visibility": "non-public"}'
        with self.assertRaisesRegex(DataValidationError, "provider_metadata"):
            validate_frames(events, quotes, features, manifest)

        events, quotes, features, manifest = public_frames()
        features["source"] = "p-flow"
        manifest["source"] = "p-flow"
        with self.assertRaisesRegex(DataValidationError, "public-input boundary"):
            validate_frames(events, quotes, features, manifest)

    def test_public_research_sources_and_unauthenticated_snapshots_are_allowed(self):
        allowed = (
            "public_behavioral_data",
            "public_search_data",
            "public_filings",
            "public_market_quotes",
            "public_executable_prices",
        )
        for classification in allowed:
            with self.subTest(classification=classification):
                events, quotes, features, manifest = public_frames()
                manifest["source_classification"] = classification
                quotes["provider_metadata"] = "public unauthenticated venue snapshot"
                bundle = validate_frames(events, quotes, features, manifest)
                self.assertEqual(bundle.validation.rows["events"], 1)

    def test_credentialed_execution_configuration_is_rejected(self):
        with TemporaryDirectory() as temporary:
            config_path = make_synthetic_dataset(Path(temporary), event_count=3)
            config_path.write_text(
                config_path.read_text(encoding="utf-8")
                + '\n[execution_api]\norder_submission_endpoint = "https://venue.example/orders"\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ConfigError, "public-input boundary"):
                ValiConfig.from_toml(config_path)

    def test_direct_core_config_rejects_forbidden_data_path(self):
        config = ValiConfig(
            data=DataConfig(
                Path("events.csv"),
                Path("quotes.csv"),
                Path("P_flow.csv"),
                Path("feature_manifest.csv"),
            ),
            market=MarketConfig(0.10, 100, 30, 120, 5),
            parameter_freeze_date="2026-06-23",
        )

        with self.assertRaisesRegex(ConfigError, "public-input boundary"):
            config.validate()


if __name__ == "__main__":
    unittest.main()
