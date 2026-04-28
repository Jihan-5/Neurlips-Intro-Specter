"""Detection metrics: precision/recall/F1, AUROC, AUPRC, false-commit rate."""

from __future__ import annotations

import numpy as np


def detection_f1(predicted: list[bool], gold: list[bool]) -> tuple[float, float, float]:
    p = np.asarray(predicted, dtype=int)
    g = np.asarray(gold, dtype=int)
    tp = int(((p == 1) & (g == 1)).sum())
    fp = int(((p == 1) & (g == 0)).sum())
    fn = int(((p == 0) & (g == 1)).sum())
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return prec, rec, f1


def auroc(scores: list[float], labels: list[int]) -> float:
    """Area under ROC; computed via the rank-sum identity."""
    s = np.asarray(scores, dtype=float)
    y = np.asarray(labels, dtype=int)
    pos = y == 1
    neg = y == 0
    n_pos, n_neg = int(pos.sum()), int(neg.sum())
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    order = np.argsort(s)
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(1, len(s) + 1)
    sum_ranks_pos = ranks[pos].sum()
    return float((sum_ranks_pos - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


def auprc(scores: list[float], labels: list[int]) -> float:
    s = np.asarray(scores, dtype=float)
    y = np.asarray(labels, dtype=int)
    if y.sum() == 0:
        return float("nan")
    order = np.argsort(-s)
    y_sorted = y[order]
    cum_tp = np.cumsum(y_sorted)
    precision = cum_tp / np.arange(1, len(y_sorted) + 1)
    recall = cum_tp / y.sum()
    # Step-wise AP.
    return float(np.sum(precision * y_sorted) / y.sum())


def false_commit_rate(predicted_pass: list[bool], gold_pass: list[bool]) -> float:
    """Fraction of cases where the system declared pass but the gold says fail."""
    if not predicted_pass:
        return float("nan")
    n_false_commit = sum(1 for p, g in zip(predicted_pass, gold_pass, strict=True) if p and not g)
    return n_false_commit / len(predicted_pass)
