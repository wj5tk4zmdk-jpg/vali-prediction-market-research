import unittest

import numpy as np

from vali.regimes import classify_correlation_vector, lagged_correlations


class RegimeTests(unittest.TestCase):
    def test_attention_leading_sign_convention(self):
        rng = np.random.default_rng(7)
        attention = rng.normal(size=200)
        price = np.concatenate([np.zeros(3), attention[:-3]])
        correlations = lagged_correlations(attention, price, max_lag=7, min_periods=30)
        regime, lag, _ = classify_correlation_vector(correlations, 0.2, 0.01)
        self.assertEqual(regime, "attention_leading")
        self.assertEqual(lag, 3.0)

    def test_all_regime_labels(self):
        self.assertEqual(classify_correlation_vector({2: 0.8, 0: 0.1}, 0.2, 0.05)[0], "attention_leading")
        self.assertEqual(classify_correlation_vector({-2: 0.8, 0: 0.1}, 0.2, 0.05)[0], "market_leading")
        self.assertEqual(classify_correlation_vector({0: 0.8, 2: 0.1}, 0.2, 0.05)[0], "coupled")
        self.assertEqual(classify_correlation_vector({0: 0.1, 2: 0.15}, 0.2, 0.05)[0], "unstable")
        self.assertEqual(classify_correlation_vector({2: 0.80, -2: 0.78}, 0.2, 0.05)[0], "unstable")


if __name__ == "__main__":
    unittest.main()

