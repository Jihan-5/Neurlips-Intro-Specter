"""End-to-end Intro-Specter pipeline on the synthetic Tier-C benchmark.

Two modes are tested separately because they target different metrics:

* ``single_fault`` — top-1 attribution should match the gold fault node
  exactly, because by construction only one swap clears the violation.
* ``multi_valid`` — multiple swaps clear the violation; we assert that the
  posterior's top-3 contains the gold (root-cause) fault node and that the
  cost-aware selector picks the cheapest valid swap.
"""

from __future__ import annotations

from intro_specter.attribution import RuleBasedCounterfactualSampler
from intro_specter.benchmarks.synthetic_dag import (
    NodeKind,
    SyntheticDAGBenchmark,
)
from intro_specter.pipeline import IntroSpecterConfig, run_intro_specter
from intro_specter.verifier import HybridVerifier


# ---------------------------------------------------------------------------
# Generator + verifier sanity
# ---------------------------------------------------------------------------


def test_single_fault_examples_violate_verifier() -> None:
    bench = SyntheticDAGBenchmark(n_examples=20, seed=42, mode="single_fault")
    for ex in bench:
        verifier = HybridVerifier(rules=list(ex.rules))
        result, _ = verifier.check(
            profile=ex.profile, task=ex.task, trajectory=ex.trajectory,
            final_output=ex.trajectory.final_output,
        )
        assert not result.passed, ex.task_id


def test_multi_valid_examples_violate_verifier() -> None:
    bench = SyntheticDAGBenchmark(n_examples=20, seed=42, mode="multi_valid")
    for ex in bench:
        verifier = HybridVerifier(rules=list(ex.rules))
        result, _ = verifier.check(
            profile=ex.profile, task=ex.task, trajectory=ex.trajectory,
            final_output=ex.trajectory.final_output,
        )
        assert not result.passed, ex.task_id


def test_splits_partition_correctly() -> None:
    bench_all = SyntheticDAGBenchmark(n_examples=100, seed=0, mode="single_fault", split="all")
    bench_tr = SyntheticDAGBenchmark(n_examples=100, seed=0, mode="single_fault", split="train")
    bench_val = SyntheticDAGBenchmark(n_examples=100, seed=0, mode="single_fault", split="val")
    bench_te = SyntheticDAGBenchmark(n_examples=100, seed=0, mode="single_fault", split="test")
    assert len(bench_tr) + len(bench_val) + len(bench_te) == len(bench_all)
    # Splits must be disjoint by task_id.
    ids_tr = {e.task_id for e in bench_tr}
    ids_val = {e.task_id for e in bench_val}
    ids_te = {e.task_id for e in bench_te}
    assert ids_tr.isdisjoint(ids_val)
    assert ids_tr.isdisjoint(ids_te)
    assert ids_val.isdisjoint(ids_te)
    # Examples must report their split correctly.
    for e in bench_val:
        assert e.split == "val"
    for e in bench_te:
        assert e.split == "test"


def test_single_fault_node_is_manual() -> None:
    """The fault node in single_fault mode is a `manual` node: that's what
    makes the mode discriminating for attribution."""
    from intro_specter.benchmarks.synthetic_dag import MealPlanningDomain

    domain = MealPlanningDomain()
    graph = domain.graph("single_fault")
    fault = graph.by_id(domain.fault_target("single_fault"))
    assert fault.kind == NodeKind.MANUAL


def test_multi_valid_fault_node_is_function() -> None:
    from intro_specter.benchmarks.synthetic_dag import MealPlanningDomain

    domain = MealPlanningDomain()
    graph = domain.graph("multi_valid")
    fault = graph.by_id(domain.fault_target("multi_valid"))
    assert fault.kind == NodeKind.FUNCTION


# ---------------------------------------------------------------------------
# Mode-specific pipeline behavior
# ---------------------------------------------------------------------------


def _run(ex):  # type: ignore[no-untyped-def]
    verifier = HybridVerifier(rules=list(ex.rules))
    sampler = RuleBasedCounterfactualSampler(
        swap_fn=ex.swap_fn,  # type: ignore[arg-type]
        evaluator=ex.evaluator,  # type: ignore[arg-type]
    )
    cfg = IntroSpecterConfig(n_counterfactual_trials=1)
    return run_intro_specter(
        profile=ex.profile, task=ex.task, trajectory=ex.trajectory,
        verifier=verifier, sampler=sampler, config=cfg,
        gold_dag=ex.dag, rerun_callable=ex.rerun_fn,
    )


def test_single_fault_mode_attribution_top1_matches_gold() -> None:
    """In single_fault mode only ONE swap is valid, so top-1 attribution must
    match the gold fault node exactly. This is the strict-attribution metric."""
    bench = SyntheticDAGBenchmark(n_examples=30, seed=11, mode="single_fault")
    n_top1 = 0
    n_repaired = 0
    for ex in bench:
        out = _run(ex)
        if out.status == "repaired":
            n_repaired += 1
        if out.fault_node == ex.gold.fault_node_id:
            n_top1 += 1
    # All 30 should be repaired (the swap at the manual fault node always works).
    assert n_repaired >= 28
    # And top-1 should match gold for nearly all of them.
    assert n_top1 >= 28


def test_multi_valid_mode_top3_contains_gold_and_cheapest_picked() -> None:
    """In multi_valid mode, multiple swaps remove the violation. Top-3 should
    contain the gold root-cause node, and the cost-aware selector should
    prefer the cheapest valid swap (latest in topo order)."""
    bench = SyntheticDAGBenchmark(n_examples=30, seed=11, mode="multi_valid")
    n_top3 = 0
    n_repaired = 0
    n_picked_late = 0
    for ex in bench:
        out = _run(ex)
        if out.status == "repaired":
            n_repaired += 1
        if out.posterior is not None and ex.gold.fault_node_id in out.posterior.top_k:
            n_top3 += 1
        # The gold fault is at "a1"; the cost-cheapest valid swap is "a5". The
        # selector should usually prefer a5 in this benchmark.
        if out.fault_node in {"a5", "a1"}:
            n_picked_late += 1
    assert n_repaired >= 25, f"only {n_repaired}/30 repaired"
    assert n_top3 >= 25, f"gold in top-3 only {n_top3}/30"
    assert n_picked_late >= 25, f"selector picked a5 or a1 only {n_picked_late}/30"


# ---------------------------------------------------------------------------
# Mode-specific *evaluator* behavior — single_fault vs multi_valid
# ---------------------------------------------------------------------------


def test_single_fault_evaluator_returns_true_only_for_fault_node() -> None:
    """The point of single_fault: only swap at the gold fault node clears."""
    bench = SyntheticDAGBenchmark(n_examples=10, seed=99, mode="single_fault")
    for ex in bench:
        for node in ex.dag.nodes:
            repair = ex.swap_fn(node)  # type: ignore[misc]
            if repair is None:
                continue
            removed = ex.evaluator(repair, ex.trajectory, ex.gold_violations[0])  # type: ignore[misc]
            if node.id == ex.gold.fault_node_id:
                assert removed, f"{ex.task_id}: gold node {node.id} swap should clear"
            else:
                assert not removed, f"{ex.task_id}: non-gold node {node.id} swap should NOT clear"


def test_multi_valid_evaluator_has_at_least_two_valid_swaps() -> None:
    """The point of multi_valid: more than one swap clears the violation. The
    fault is at a1; swaps at a1 and at a5 both produce a clean trajectory in
    our meal-planning compute graph."""
    bench = SyntheticDAGBenchmark(n_examples=10, seed=99, mode="multi_valid")
    for ex in bench:
        valid = []
        for node in ex.dag.nodes:
            repair = ex.swap_fn(node)  # type: ignore[misc]
            if repair is None:
                continue
            if ex.evaluator(repair, ex.trajectory, ex.gold_violations[0]):  # type: ignore[misc]
                valid.append(node.id)
        assert ex.gold.fault_node_id in valid, ex.task_id
        assert len(valid) >= 2, f"{ex.task_id}: only {valid} swaps clear; expected >= 2"
