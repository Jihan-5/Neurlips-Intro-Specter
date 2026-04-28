"""Attribution metrics: top-k, MRR, ancestor-hit-rate, earliest-fault distance."""

from __future__ import annotations

from collections.abc import Iterable

from ..dag import build_networkx
from ..schemas import AssumptionDAG


def topk_accuracy(predictions: list[list[str]], gold: list[str], k: int) -> float:
    """Fraction of examples where the gold node appears in the top-k of the
    posterior ranking.

    `predictions[i]` must be the ranked list of node ids (highest posterior first).
    """
    if not predictions:
        return 0.0
    n_correct = 0
    for ranked, g in zip(predictions, gold, strict=True):
        if g in ranked[:k]:
            n_correct += 1
    return n_correct / len(predictions)


def mrr(predictions: list[list[str]], gold: list[str]) -> float:
    """Mean Reciprocal Rank of the gold node in each predicted ranking."""
    if not predictions:
        return 0.0
    total = 0.0
    for ranked, g in zip(predictions, gold, strict=True):
        try:
            r = ranked.index(g) + 1
            total += 1.0 / r
        except ValueError:
            continue
    return total / len(predictions)


def ancestor_hit_rate(
    predictions: list[list[str]],
    gold: list[str],
    dags: list[AssumptionDAG],
    k: int = 1,
) -> float:
    """Fraction of examples where the top-k contains *any* ancestor of the gold
    fault (including the gold node itself). A weaker but useful credit metric.
    """
    if not predictions:
        return 0.0
    n_hit = 0
    for ranked, g, dag in zip(predictions, gold, dags, strict=True):
        g_set = {g}
        graph = build_networkx(dag)
        if g in graph:
            for n in graph.predecessors(g):
                g_set.add(n)
        if any(p in g_set for p in ranked[:k]):
            n_hit += 1
    return n_hit / len(predictions)


def earliest_fault_distance(
    predicted_step_ids: Iterable[int], gold_step_ids: Iterable[int]
) -> float:
    """Mean absolute step-id distance between the predicted earliest fault step
    and the gold earliest fault step. Lower is better.
    """
    pred = list(predicted_step_ids)
    gold = list(gold_step_ids)
    if not pred:
        return float("nan")
    diffs = [abs(p - g) for p, g in zip(pred, gold, strict=True)]
    return sum(diffs) / len(diffs)
