"""Paired statistical tests required by the plan PDF.

* paired bootstrap CIs for success-rate deltas
* McNemar's test for paired binary success/failure
* Wilcoxon signed-rank for paired cost / latency
* Holm-Bonferroni correction across multiple metrics
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
from scipy import stats as _stats


@dataclass
class CI:
    point: float
    low: float
    high: float
    level: float


def paired_bootstrap_ci(
    a: list[float],
    b: list[float],
    *,
    n_resamples: int = 10_000,
    level: float = 0.95,
    seed: int = 0,
) -> CI:
    """CI for the mean(b - a) on paired data."""
    rng = np.random.default_rng(seed)
    a_arr = np.asarray(a, dtype=float)
    b_arr = np.asarray(b, dtype=float)
    n = len(a_arr)
    if n == 0:
        return CI(float("nan"), float("nan"), float("nan"), level)
    diffs = b_arr - a_arr
    point = float(diffs.mean())
    idx = rng.integers(0, n, size=(n_resamples, n))
    boots = diffs[idx].mean(axis=1)
    alpha = (1 - level) / 2
    low, high = float(np.quantile(boots, alpha)), float(np.quantile(boots, 1 - alpha))
    return CI(point, low, high, level)


@dataclass
class TestResult:
    statistic: float
    pvalue: float


def mcnemar(success_a: list[bool], success_b: list[bool]) -> TestResult:
    """Exact McNemar's test on paired success/failure pairs (b vs. a)."""
    a = np.asarray(success_a, dtype=int)
    b = np.asarray(success_b, dtype=int)
    b01 = int(((a == 0) & (b == 1)).sum())
    b10 = int(((a == 1) & (b == 0)).sum())
    if b01 + b10 == 0:
        return TestResult(0.0, 1.0)
    res = _stats.binomtest(min(b01, b10), n=b01 + b10, p=0.5, alternative="two-sided")
    return TestResult(float(min(b01, b10)), float(res.pvalue))


def wilcoxon_signed_rank(a: list[float], b: list[float]) -> TestResult:
    diffs = np.asarray(b, dtype=float) - np.asarray(a, dtype=float)
    nz = diffs[diffs != 0]
    if len(nz) == 0:
        return TestResult(0.0, 1.0)
    res = _stats.wilcoxon(nz, alternative="two-sided", zero_method="pratt")
    return TestResult(float(res.statistic), float(res.pvalue))


def holm_bonferroni(
    pvalues: list[float], alpha: float = 0.05
) -> tuple[list[bool], list[float]]:
    """Holm-Bonferroni correction. Returns (rejected, adjusted_pvalues)."""
    p = np.asarray(pvalues, dtype=float)
    n = len(p)
    order = np.argsort(p)
    adj = np.empty(n)
    rej = np.zeros(n, dtype=bool)
    for rank, idx in enumerate(order):
        adj[idx] = min(1.0, p[idx] * (n - rank))
    # Enforce monotonicity along sorted order.
    cur = 0.0
    for idx in order:
        cur = max(cur, adj[idx])
        adj[idx] = cur
        rej[idx] = adj[idx] < alpha
    return list(map(bool, rej)), list(map(float, adj))


def aggregate_summary(
    *,
    metric_a: list[float],
    metric_b: list[float],
    kind: Literal["success", "cost"],
) -> dict[str, float]:
    """Convenience: bootstrap CI + appropriate paired test in one call."""
    ci = paired_bootstrap_ci(metric_a, metric_b)
    if kind == "success":
        bool_a = [bool(x) for x in metric_a]
        bool_b = [bool(x) for x in metric_b]
        test = mcnemar(bool_a, bool_b)
    else:
        test = wilcoxon_signed_rank(metric_a, metric_b)
    return {
        "delta": ci.point,
        "ci_low": ci.low,
        "ci_high": ci.high,
        "pvalue": test.pvalue,
        "statistic": test.statistic,
    }
