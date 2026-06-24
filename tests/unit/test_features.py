import unittest

import numpy as np
import pandas as pd

from vali.config import FeatureConfig
from vali.features import build_attention_index, rolling_prior_zscore


class FeatureTests(unittest.TestCase):
    def test_log1p_transformation_accepts_zero_and_rejects_negative_values(self):
        cutoffs = pd.date_range("2025-01-01 21:00", periods=6, freq="D", tz="UTC")
        features = pd.DataFrame(
            [
                {
                    "feature_id": "search",
                    "observation_at": cutoff - pd.Timedelta(hours=2),
                    "available_at": cutoff - pd.Timedelta(hours=1),
                    "vintage": "v1",
                    "source": "test",
                    "value": float(index),
                }
                for index, cutoff in enumerate(cutoffs)
            ]
        )
        manifest = pd.DataFrame(
            [
                {
                    "feature_id": "search",
                    "rationale": "test",
                    "transformation": "log1p",
                    "polarity": 1,
                    "availability_lag_days": 0,
                    "missing_policy": "asof",
                    "max_age_days": 1,
                    "required": True,
                    "source": "test",
                }
            ]
        )
        attention, audit = build_attention_index(
            features, manifest, cutoffs, FeatureConfig(standardization_window=3, min_periods=3)
        )
        self.assertAlmostEqual(audit.loc[0, "transformed_value"], 0.0)
        self.assertTrue(attention.loc[3:, "attention"].notna().all())
        features.loc[0, "value"] = -1.0
        with self.assertRaisesRegex(ValueError, "non-negative"):
            build_attention_index(
                features, manifest, cutoffs, FeatureConfig(standardization_window=3, min_periods=3)
            )

    def test_prior_zscore_excludes_current_and_future(self):
        original = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
        changed = original.copy()
        changed.iloc[-1] = 10_000
        first = rolling_prior_zscore(original, window=3, min_periods=3)
        second = rolling_prior_zscore(changed, window=3, min_periods=3)
        pd.testing.assert_series_equal(first.iloc[:-1], second.iloc[:-1])
        expected = (4.0 - 2.0) / np.std([1.0, 2.0, 3.0], ddof=0)
        self.assertAlmostEqual(first.iloc[3], expected)

    def test_attention_applies_polarity_and_rejects_required_missing(self):
        cutoffs = pd.date_range("2025-01-01 21:00", periods=8, freq="D", tz="UTC")
        rows = []
        for feature_id, sign in (("positive", 1), ("inverse", -1)):
            for index, cutoff in enumerate(cutoffs):
                rows.append(
                    {
                        "feature_id": feature_id,
                        "observation_at": cutoff - pd.Timedelta(hours=2),
                        "available_at": cutoff - pd.Timedelta(hours=1),
                        "vintage": "v1",
                        "source": "test",
                        "value": index if sign == 1 else -index,
                    }
                )
        features = pd.DataFrame(rows)
        manifest = pd.DataFrame(
            [
                {"feature_id": "positive", "rationale": "test", "transformation": "level", "polarity": 1, "availability_lag_days": 0, "missing_policy": "asof", "max_age_days": 1, "required": True, "source": "test"},
                {"feature_id": "inverse", "rationale": "test", "transformation": "level", "polarity": -1, "availability_lag_days": 0, "missing_policy": "asof", "max_age_days": 1, "required": True, "source": "test"},
            ]
        )
        config = FeatureConfig(standardization_window=3, min_periods=3)
        attention, audit = build_attention_index(features, manifest, cutoffs, config)
        self.assertTrue(attention.loc[3:, "required_complete"].all())
        self.assertTrue((attention.loc[3:, "attention"] > 0).all())
        self.assertEqual(set(audit["feature_id"]), {"positive", "inverse"})

    def test_future_revision_cannot_change_earlier_attention(self):
        cutoffs = pd.date_range("2025-01-01 21:00", periods=8, freq="D", tz="UTC")
        features = pd.DataFrame(
            [
                {"feature_id": "f", "observation_at": cutoff - pd.Timedelta(hours=2), "available_at": cutoff - pd.Timedelta(hours=1), "vintage": "initial", "source": "test", "value": float(index)}
                for index, cutoff in enumerate(cutoffs)
            ]
        )
        manifest = pd.DataFrame(
            [{"feature_id": "f", "rationale": "test", "transformation": "level", "polarity": 1, "availability_lag_days": 0, "missing_policy": "asof", "max_age_days": 1, "required": True, "source": "test"}]
        )
        config = FeatureConfig(standardization_window=3, min_periods=3)
        baseline, _ = build_attention_index(features, manifest, cutoffs, config)
        revision = features.iloc[[2]].copy()
        revision["available_at"] = cutoffs[-1] - pd.Timedelta(minutes=30)
        revision["vintage"] = "revised"
        revision["value"] = 10000.0
        revised, _ = build_attention_index(pd.concat([features, revision]), manifest, cutoffs, config)
        pd.testing.assert_series_equal(
            baseline.loc[:6, "attention"], revised.loc[:6, "attention"], check_names=False
        )

    def test_missing_required_feature_produces_no_attention(self):
        cutoffs = pd.date_range("2025-01-01 21:00", periods=6, freq="D", tz="UTC")
        features = pd.DataFrame(
            [{"feature_id": "f", "observation_at": cutoffs[0] - pd.Timedelta(hours=2), "available_at": cutoffs[0] - pd.Timedelta(hours=1), "vintage": "v1", "source": "test", "value": 1.0}]
        )
        manifest = pd.DataFrame(
            [{"feature_id": "f", "rationale": "test", "transformation": "level", "polarity": 1, "availability_lag_days": 0, "missing_policy": "asof", "max_age_days": 0, "required": True, "source": "test"}]
        )
        attention, _ = build_attention_index(
            features, manifest, cutoffs, FeatureConfig(standardization_window=3, min_periods=2)
        )
        self.assertTrue(attention.loc[1:, "attention"].isna().all())
        self.assertTrue((attention.loc[1:, "attention_rejection_reason"] == "missing_required_feature").all())


if __name__ == "__main__":
    unittest.main()
