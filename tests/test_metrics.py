"""Sanity checks for attribution metrics, calibration, and paired stats."""

from __future__ import annotations

import math

from intro_specter.metrics import (
    brier_score,
    detection_f1,
    expected_calibration_error,
    holm_bonferroni,
    mrr,
    paired_bootstrap_ci,
    topk_accuracy,
)


def test_topk_and_mrr_basic() -> None:
    preds = [["a", "b", "c"], ["b", "a", "c"], ["c", "b", "a"]]
    gold = ["a", "a", "a"]
    assert topk_accuracy(preds, gold, k=1) == 1 / 3
    assert topk_accuracy(preds, gold, k=2) == 2 / 3
    assert topk_accuracy(preds, gold, k=3) == 1.0
    assert math.isclose(mrr(preds, gold), (1 + 0.5 + 1 / 3) / 3)


def test_detection_f1_and_calibration() -> None:
    pred = [True, True, False, False, True]
    gold = [True, False, False, True, True]
    prec, rec, f1 = detection_f1(pred, gold)
    assert prec == 2 / 3
    assert rec == 2 / 3
    assert math.isclose(f1, 2 / 3)
    # ECE on a tiny perfectly-calibrated set: probs match labels.
    assert expected_calibration_error([1.0, 0.0, 1.0, 0.0], [1, 0, 1, 0]) == 0.0
    assert brier_score([0.5, 0.5], [1, 0]) == 0.25


def test_paired_bootstrap_ci_includes_truth_for_zero_delta() -> None:
    a = [0.5] * 100
    b = [0.5] * 100
    ci = paired_bootstrap_ci(a, b, n_resamples=500)
    assert ci.point == 0.0
    assert ci.low <= 0 <= ci.high


def test_holm_bonferroni_rejects_smallest() -> None:
    rej, adj = holm_bonferroni([0.001, 0.04, 0.5], alpha=0.05)
    assert rej[0]
    assert not rej[2]
    # Adjusted values must be monotone non-decreasing along the sorted order.
    assert adj[0] <= adj[1] <= adj[2]
