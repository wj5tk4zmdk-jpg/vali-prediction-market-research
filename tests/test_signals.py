import unittest

import numpy as np
import pandas as pd

from vali.signals import logit_clip, rolling_ols_slope


class SignalMathTests(unittest.TestCase):
    def test_linear_rolling_slope(self):
        series = pd.Series([1.0, 3.0, 5.0, 7.0, 9.0])
        result = rolling_ols_slope(series, 3)
        self.assertTrue(result.iloc[:2].isna().all())
        np.testing.assert_allclose(result.iloc[2:], 2.0)

    def test_logit_clips_endpoints(self):
        result = logit_clip(np.array([0.0, 0.5, 1.0]), epsilon=1e-4)
        self.assertTrue(np.isfinite(result).all())
        self.assertAlmostEqual(result[1], 0.0)
        self.assertAlmostEqual(result[0], -result[2])


if __name__ == "__main__":
    unittest.main()

