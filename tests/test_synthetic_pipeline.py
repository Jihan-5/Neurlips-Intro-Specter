"""End-to-end Intro-Specter pipeline on the synthetic Tier-C benchmark.

Runs without any API key: the synthetic benchmark is fully deterministic and the
rule-based counterfactual sampler does not call an LLM.
"""

from __future__ import annotations

from intro_specter.attribution import RuleBasedCounterfactualSampler
from intro_specter.benchmarks.synthetic_dag import SyntheticDAGBenchmark
from intro_specter.pipeline import IntroSpecterConfig, run_intro_specter
from intro_specter.verifier import HybridVerifier


def test_synthetic_benchmark_yields_violating_examples() -> None:
    bench = SyntheticDAGBenchmark(n_examples=10, seed=42)
    examples = list(bench)
    assert len(examples) == 10
    # Every fault-injected example should fail the rule-based verifier.
    for ex in examples:
        verifier = HybridVerifier(rules=list(ex.rules))
        result, _ = verifier.check(
            profile=ex.profile,
            task=ex.task,
            trajectory=ex.trajectory,
            final_output=ex.trajectory.final_output,
        )
        assert not result.passed, ex.task_id


def test_intro_specter_repairs_majority_of_synthetic_faults() -> None:
    """End-to-end smoke test on the synthetic Tier-C benchmark.

    By construction, the current synthetic benchmark scores every ancestor swap as
    a valid repair (the rule-based rerun produces a clean trajectory regardless
    of swap location), so multiple nodes will tie on likelihood and the
    cost-aware selector will prefer the *cheapest* — i.e., the latest — fix
    point. Therefore we assert top-3 contains the gold fault, not top-1. This is
    the expected behavior for a discriminating-by-repair-cost benchmark; a harder
    Tier-C variant in which only the actual fault location's swap removes the
    violation is on the to-do list.
    """
    bench = SyntheticDAGBenchmark(n_examples=30, seed=7)
    n_repaired = 0
    n_top3_attribution = 0
    for ex in bench:
        verifier = HybridVerifier(rules=list(ex.rules))
        sampler = RuleBasedCounterfactualSampler(
            swap_fn=ex.swap_fn,  # type: ignore[arg-type]
            evaluator=ex.evaluator,  # type: ignore[arg-type]
        )
        cfg = IntroSpecterConfig(n_counterfactual_trials=1)
        out = run_intro_specter(
            profile=ex.profile,
            task=ex.task,
            trajectory=ex.trajectory,
            verifier=verifier,
            sampler=sampler,
            config=cfg,
            gold_dag=ex.dag,
            rerun_callable=ex.rerun_fn,
        )
        if out.status == "repaired":
            n_repaired += 1
        if out.posterior is not None and ex.gold.fault_node_id in out.posterior.top_k:
            n_top3_attribution += 1
    assert n_repaired >= 25, f"only {n_repaired}/30 repaired"
    assert n_top3_attribution >= 25, (
        f"only {n_top3_attribution}/30 had gold fault in top-3"
    )
