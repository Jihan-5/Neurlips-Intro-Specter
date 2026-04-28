"""Repair metrics: corrected success, delta success, degradation rate."""

from __future__ import annotations

from collections.abc import Iterable


def delta_success_rate(
    initial_success: Iterable[bool], post_repair_success: Iterable[bool]
) -> float:
    a = list(initial_success)
    b = list(post_repair_success)
    if not a:
        return float("nan")
    deltas = [int(y) - int(x) for x, y in zip(a, b, strict=True)]
    return sum(deltas) / len(deltas)


def degradation_rate(
    initial_success: Iterable[bool], post_repair_success: Iterable[bool]
) -> float:
    """Fraction of already-correct trajectories that became incorrect after repair.

    The plan PDF's "Negative control" target is degradation rate < 3-5%.
    """
    a = list(initial_success)
    b = list(post_repair_success)
    if not a:
        return float("nan")
    n_were_correct = sum(1 for x in a if x)
    if n_were_correct == 0:
        return 0.0
    n_broken = sum(1 for x, y in zip(a, b, strict=True) if x and not y)
    return n_broken / n_were_correct
