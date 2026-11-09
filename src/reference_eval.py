"""Reference evaluator: clean image is used only here."""

from __future__ import annotations

import numpy as np


def risk(f: np.ndarray, x: np.ndarray) -> float:
    """Sum of squared errors between output f and clean image x."""
    f64 = np.asarray(f, dtype=np.float64)
    x64 = np.asarray(x, dtype=np.float64)
    return float(np.sum((f64 - x64) ** 2))
