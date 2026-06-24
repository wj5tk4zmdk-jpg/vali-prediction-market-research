import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from vali.config import DataConfig, FeatureConfig, MarketConfig, SignalConfig, ValiConfig
from vali.features import build_attention_index
from vali.market import select_daily_market
from vali.regimes import classify_correlation_vector
from vali.signals import compute_vali_signals


def characterization_config() -> ValiConfig:
    return ValiConfig(
        data=DataConfig(Path("events"), Path("quotes"), Path("features"), Path("manifest")),
        market=MarketConfig(
            max_spread=0.10,
            min_depth=100,
            max_quote_age_minutes=30,
            fallback_trade_window_minutes=120,
            fee_bps=5,
        ),
        features=FeatureConfig(
            timezone="UTC", daily_cutoff="16:00", standardization_window=3, min_periods=3
        ),
        signal=SignalConfig(
            velocity_window=3,
            normalization_window=3,
            min_periods=3,
            entry_threshold=2.0,
            exit_threshold=0.5,
            sensitivity_windows=(3, 14, 30),
        ),
        parameter_freeze_date="2026-06-23",
    )


class MethodologyCharacterizationTests(unittest.TestCase):
    def test_behavioral_attention_equal_weight_polarity_and_prior_normalization(self):
        cutoffs = pd.date_range("2025-01-01 16:00", periods=8, freq="D", tz="UTC")
        feature_rows = []
        for feature_id, polarity in (("easing_attention", 1), ("tightening_attention", -1)):
            for index, cutoff in enumerate(cutoffs):
                feature_rows.append(
                    {
                        "feature_id": feature_id,
                        "observation_at": cutoff - pd.Timedelta(hours=2),
                        "available_at": cutoff - pd.Timedelta(hours=1),
                        "vintage": "initial",
                        "source": "public_fixture",
                        "value": float(index if polarity == 1 else -index),
                    }
                )
        manifest = pd.DataFrame(
            [
                {
                    "feature_id": feature_id,
                    "rationale": "deterministic characterization fixture",
                    "transformation": "level",
                    "polarity": polarity,
                    "availability_lag_days": 0,
                    "missing_policy": "asof",
                    "max_age_days": 1,
                    "required": True,
                    "source": "public_fixture",
                }
                for feature_id, polarity in
                (("easing_attention", 1), ("tightening_attention", -1))
            ]
        )

        attention, audit = build_attention_index(
            pd.DataFrame(feature_rows), manifest, cutoffs, characterization_config().features
        )

        self.assertTrue(attention.loc[:2, "attention"].isna().all())
        np.testing.assert_allclose(
            attention.loc[3:, "attention"],
            np.repeat(2.449489742783178, 5),
            rtol=0,
            atol=1e-12,
        )
        self.assertTrue((attention.loc[3:, "active_features"] == 2).all())
        self.assertTrue(attention.loc[3:, "required_complete"].all())
        aligned = audit.pivot(index="cutoff_at", columns="feature_id", values="z_value")
        np.testing.assert_allclose(
            aligned["easing_attention"], aligned["tightening_attention"], equal_nan=True
        )

    def test_priced_conviction_velocities_signed_divergence_and_magnitude(self):
        logits = np.array([0.0, 0.0, 0.2, 0.1, 0.3, 0.4, 0.2, 0.5, 0.4, 0.6, 0.5, 0.7])
        prices = 1.0 / (1.0 + np.exp(-logits))
        cutoffs = pd.date_range("2025-01-01 16:00", periods=len(logits), freq="D", tz="UTC")
        market = pd.DataFrame(
            {"contract_id": "contract-1", "cutoff_at": cutoffs, "price": prices}
        )
        attention = pd.DataFrame(
            {
                "cutoff_at": cutoffs,
                "attention": [0, 0, 1, 1, 3, 2, 5, 4, 8, 7, 11, 9],
            }
        )

        result = compute_vali_signals(market, attention, characterization_config())

        np.testing.assert_allclose(result["logit_price"], logits, atol=1e-12, rtol=0)
        np.testing.assert_allclose(
            result.loc[2:, "attention_velocity"],
            [0.5, 0.5, 1.0, 0.5, 1.0, 1.0, 1.5, 1.5, 1.5, 1.0],
            atol=1e-12,
            rtol=0,
        )
        np.testing.assert_allclose(
            result.loc[2:, "price_velocity"],
            [0.10, 0.05, 0.05, 0.15, -0.05, 0.05, 0.10, 0.05, 0.05, 0.05],
            atol=1e-12,
            rtol=0,
        )
        np.testing.assert_allclose(
            result.loc[5:10, "signed_divergence"],
            [-4.242640687119, 4.242640687119, 0.707106781187,
             2.216054689051, 1.146952320461, 1.414213562373],
            atol=1e-11,
            rtol=0,
        )
        np.testing.assert_allclose(
            result.loc[5:10, "divergence_magnitude"],
            np.abs(result.loc[5:10, "signed_divergence"]),
            atol=0,
            rtol=0,
        )

    def test_price_quality_and_execution_liquidity_are_separate(self):
        events = pd.DataFrame(
            [
                {
                    "event_id": f"event-{index}",
                    "contract_id": f"contract-{index}",
                    "open_at": pd.Timestamp("2025-01-01 09:00", tz="UTC"),
                    "meeting_at": pd.Timestamp("2025-01-02 19:00", tz="UTC"),
                    "settlement_at": pd.Timestamp("2025-01-02 22:00", tz="UTC"),
                    "outcome": index,
                }
                for index in (0, 1)
            ]
        )
        quotes = pd.DataFrame(
            [
                {
                    "contract_id": "contract-0",
                    "observed_at": pd.Timestamp("2025-01-01 15:55", tz="UTC"),
                    "bid": 0.40,
                    "ask": 0.46,
                    "last": 0.43,
                    "volume": 100,
                    "bid_depth": 200,
                    "ask_depth": 150,
                },
                {
                    "contract_id": "contract-1",
                    "observed_at": pd.Timestamp("2025-01-01 15:55", tz="UTC"),
                    "bid": 0.40,
                    "ask": 0.46,
                    "last": 0.43,
                    "volume": 100,
                    "bid_depth": 99,
                    "ask_depth": 500,
                },
            ]
        )

        market = select_daily_market(events, quotes, None, characterization_config())
        first = market.groupby("contract_id", sort=True).head(1).set_index("contract_id")

        self.assertAlmostEqual(first.loc["contract-0", "price"], 0.43)
        self.assertTrue(first.loc["contract-0", "price_quality_pass"])
        self.assertTrue(first.loc["contract-0", "execution_liquidity_pass"])
        self.assertTrue(first.loc["contract-1", "price_quality_pass"])
        self.assertFalse(first.loc["contract-1", "execution_liquidity_pass"])
        self.assertEqual(first.loc["contract-1", "rejection_reason"], "thin_depth")

    def test_regime_characterization_uses_current_lag_sign_and_tie_rules(self):
        regime, lag, correlation = classify_correlation_vector(
            {-2: 0.30, 0: 0.40, 3: 0.82}, min_abs_correlation=0.20, tie_margin=0.05
        )
        self.assertEqual((regime, lag, correlation), ("attention_leading", 3.0, 0.82))
        tied, _, _ = classify_correlation_vector(
            {-2: 0.79, 3: 0.82}, min_abs_correlation=0.20, tie_margin=0.05
        )
        self.assertEqual(tied, "unstable")


if __name__ == "__main__":
    unittest.main()
