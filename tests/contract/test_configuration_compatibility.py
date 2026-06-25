import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from vali.config import (
    BacktestConfig as LegacyBacktestConfig,
    ConfigError as LegacyConfigError,
    DataConfig as LegacyDataConfig,
    FeatureConfig as LegacyFeatureConfig,
    MarketConfig as LegacyMarketConfig,
    RegimeConfig as LegacyRegimeConfig,
    SignalConfig as LegacySignalConfig,
    ValiConfig as LegacyValiConfig,
)
from vali.configuration.contracts import (
    BacktestConfig,
    ConfigError,
    DataConfig,
    FeatureConfig,
    MarketConfig,
    RegimeConfig,
    SignalConfig,
    ValiConfig,
)
from vali.configuration.loading import load_config, load_toml, resolve_config_path
from vali.configuration.validation import (
    validate_market_config,
    validate_public_research_config,
)
from vali.sample import make_synthetic_dataset


class ConfigurationCompatibilityTests(unittest.TestCase):
    def test_legacy_and_new_configuration_contracts_are_identical(self):
        pairs = (
            (LegacyConfigError, ConfigError),
            (LegacyDataConfig, DataConfig),
            (LegacyMarketConfig, MarketConfig),
            (LegacyFeatureConfig, FeatureConfig),
            (LegacySignalConfig, SignalConfig),
            (LegacyRegimeConfig, RegimeConfig),
            (LegacyBacktestConfig, BacktestConfig),
            (LegacyValiConfig, ValiConfig),
        )
        for legacy, extracted in pairs:
            self.assertIs(legacy, extracted)

    def test_same_toml_produces_same_config_and_resolved_paths(self):
        with TemporaryDirectory() as temporary:
            config_path = make_synthetic_dataset(Path(temporary), event_count=3)

            legacy = LegacyValiConfig.from_toml(config_path)
            extracted = load_config(config_path)
            source, raw = load_toml(config_path)

            self.assertEqual(legacy, extracted)
            self.assertEqual(source, config_path.resolve())
            self.assertEqual(raw["run"]["methodology_version"], "1.0.1")
            self.assertEqual(
                extracted.data.events,
                resolve_config_path("events.csv", config_path.parent),
            )
            self.assertEqual(extracted.features.optional_feature_policy, "reject")
            self.assertEqual(extracted.signal.sensitivity_windows, (3, 14, 30))
            self.assertEqual(extracted.backtest.entry_regime_confirmation_periods, 1)
            self.assertEqual(extracted.backtest.exit_regime_confirmation_periods, 1)

    def test_invalid_config_validation_has_same_exception_and_message(self):
        invalid = MarketConfig(0.0, 100, 30, 120, 5)
        with self.assertRaises(ConfigError) as method_error:
            invalid.validate()
        with self.assertRaises(ConfigError) as boundary_error:
            validate_market_config(invalid)
        self.assertEqual(str(method_error.exception), str(boundary_error.exception))

    def test_unknown_toml_key_failure_is_preserved(self):
        with TemporaryDirectory() as temporary:
            config_path = make_synthetic_dataset(Path(temporary), event_count=3)
            config_path.write_text(
                config_path.read_text(encoding="utf-8") + "\nunknown_setting = 3\n",
                encoding="utf-8",
            )

            messages = []
            for loader in (LegacyValiConfig.from_toml, load_config):
                with self.assertRaises(TypeError) as error:
                    loader(config_path)
                messages.append(str(error.exception))
            self.assertEqual(messages[0], messages[1])
            self.assertIn("unknown_setting", messages[0])

    def test_forbidden_config_failure_is_preserved(self):
        raw = {
            "execution_api": {
                "order_submission_endpoint": "https://venue.example/orders"
            }
        }
        with self.assertRaisesRegex(ConfigError, "public-input boundary"):
            validate_public_research_config(raw)

        with TemporaryDirectory() as temporary:
            config_path = make_synthetic_dataset(Path(temporary), event_count=3)
            config_path.write_text(
                config_path.read_text(encoding="utf-8")
                + '\n[execution_api]\norder_submission_endpoint = "https://venue.example/orders"\n',
                encoding="utf-8",
            )
            messages = []
            for loader in (LegacyValiConfig.from_toml, load_config):
                with self.assertRaises(ConfigError) as error:
                    loader(config_path)
                messages.append(str(error.exception))
            self.assertEqual(messages[0], messages[1])


if __name__ == "__main__":
    unittest.main()
