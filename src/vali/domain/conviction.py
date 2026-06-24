"""Pure public priced-conviction transformations."""

from __future__ import annotations

import numpy as np
import pandas as pd


def logit_clip(values: pd.Series | np.ndarray, epsilon: float = 1e-4):
    """Clip a public probability before applying the logit transform."""
    clipped = np.clip(values, epsilon, 1 - epsilon)
    return np.log(clipped / (1 - clipped))
