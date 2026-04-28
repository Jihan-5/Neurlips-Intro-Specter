"""Calibration metrics: Expected Calibration Error and Brier score."""

from __future__ import annotations

import numpy as np


def expected_calibration_error(
    probs: list[float], labels: list[int], n_bins: int = 10
) -> float:
    if not probs:
        return float("nan")
    p = np.asarray(probs, dtype=float)
    y = np.asarray(labels, dtype=float)
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    n = len(p)
    for i in range(n_bins):
        lo, hi = bins[i], bins[i + 1]
        mask = (p > lo) & (p <= hi) if i > 0 else (p >= lo) & (p <= hi)
        if not mask.any():
            continue
        acc = y[mask].mean()
        conf = p[mask].mean()
        ece += (mask.sum() / n) * abs(acc - conf)
    return float(ece)


def brier_score(probs: list[float], labels: list[int]) -> float:
    if not probs:
        return float("nan")
    p = np.asarray(probs, dtype=float)
    y = np.asarray(labels, dtype=float)
    return float(np.mean((p - y) ** 2))
