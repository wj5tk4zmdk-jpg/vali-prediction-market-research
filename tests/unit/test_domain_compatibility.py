import unittest

import numpy as np
import pandas as pd

from vali.domain.attention import compose_attention, transform_feature
from vali.domain.conviction import logit_clip as domain_logit_clip
from vali.domain.divergence import (
    divergence_magnitude,
    rolling_ols_slope as domain_rolling_ols_slope,
    rolling_prior_zscore as domain_rolling_prior_zscore,
    signed_divergence,
)
from vali.domain.regimes import (
    classify_correlation_vector as domain_classify_correlation_vector,
    lagged_correlations as domain_lagged_correlations,
)
from vali.features import _transform, build_attention_index, rolling_prior_zscore
from vali.regimes import classify_correlation_vector, classify_regimes, lagged_correlations
from vali.signals import compute_vali_signals, logit_clip, rolling_ols_slope


class DomainCompatibilityTests(unittest.TestCase):
    def test_old_and_new_public_boundaries_import(self):
        for function in (
            build_attention_index,
            rolling_prior_zscore,
            compute_vali_signals,
            logit_clip,
            rolling_ols_slope,
            classify_regimes,
            classify_correlation_vector,
            transform_feature,
            compose_attention,
            domain_logit_clip,
            signed_divergence,
            divergence_magnitude,
            domain_classify_correlation_vector,
        ):
            self.assertTrue(callable(function))

    def test_attention_and_divergence_wrappers_match_domain_math(self):
        values = pd.Series([1.0, 2.0, 4.0, 8.0, 16.0, 32.0])
        pd.testing.assert_series_equal(
            _transform(values, "log1p"), transform_feature(values, "log1p")
        )
        pd.testing.assert_series_equal(
            rolling_prior_zscore(values, 3, 3),
            domain_rolling_prior_zscore(values, 3, 3),
        )
        pd.testing.assert_series_equal(
            rolling_ols_slope(values, 3), domain_rolling_ols_slope(values, 3)
        )

        z_attention = pd.Series([1.0, -2.0, 0.5])
        z_price = pd.Series([0.25, -1.0, 1.5])
        divergence = signed_divergence(z_attention, z_price)
        pd.testing.assert_series_equal(
            divergence, pd.Series([0.75, -1.0, -1.0])
        )
        pd.testing.assert_series_equal(
            divergence_magnitude(divergence), pd.Series([0.75, 1.0, 1.0])
        )

    def test_conviction_and_regime_wrappers_match_domain_math(self):
        probabilities = pd.Series([0.0, 0.2, 0.8, 1.0])
        pd.testing.assert_series_equal(
            logit_clip(probabilities), domain_logit_clip(probabilities)
        )

        attention = np.array([0.0, 1.0, 0.0, -1.0, 0.0, 1.0])
        price = np.array([-1.0, 0.0, 1.0, 0.0, -1.0, 0.0])
        old = lagged_correlations(attention, price, max_lag=2, min_periods=3)
        new = domain_lagged_correlations(attention, price, max_lag=2, min_periods=3)
        self.assertEqual(old.keys(), new.keys())
        for lag in old:
            if np.isnan(old[lag]):
                self.assertTrue(np.isnan(new[lag]))
            else:
                self.assertAlmostEqual(old[lag], new[lag])
        self.assertEqual(
            classify_correlation_vector(old, 0.20, 0.05),
            domain_classify_correlation_vector(new, 0.20, 0.05),
        )

    def test_domain_attention_composition_preserves_frozen_policy(self):
        zframe = pd.DataFrame(
            {"required": [1.0, 2.0], "optional": [3.0, np.nan]}
        )
        rejected = compose_attention(zframe, ["required"], "reject")
        dynamic = compose_attention(zframe, ["required"], "dynamic_reweight")

        self.assertAlmostEqual(rejected[0].iloc[0], 2.0)
        self.assertTrue(pd.isna(rejected[0].iloc[1]))
        self.assertEqual(rejected[4].tolist(), ["", "missing_optional_feature"])
        self.assertAlmostEqual(dynamic[0].iloc[1], 2.0)


if __name__ == "__main__":
    unittest.main()
