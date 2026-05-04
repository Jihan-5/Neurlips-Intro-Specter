"""Paired-sampling determinism for Real-* benchmarks.

The McNemar paired tests on the Real-* matrix require that the same task_id
appears across all (method, model) cells for a given (benchmark, seed). If
the loader sample is non-deterministic, the paired statistics silently
break: the test assumes (task_id, seed) keys align but they don't, and
McNemar will compute over a misaligned pairing.

This test asserts that two independent instantiations of each Real-*
benchmark with the same (n_examples, seed, split) produce the SAME
ordered list of task_ids. The runner pairs methods within a single
process (so this would be tautologically true), but cross-process
runs (different intro-specter invocations) must also pair correctly.
"""

from __future__ import annotations

import pytest

from intro_specter.benchmarks.hotpotqa_real import HotpotQAReal
from intro_specter.benchmarks.longmemeval_real import LongMemEvalReal
from intro_specter.benchmarks.musique_real import MuSiQueReal
from intro_specter.benchmarks.strategyqa_real import StrategyQAReal
from intro_specter.benchmarks.travelplanner_real import TravelPlannerReal
from intro_specter.benchmarks.truthfulqa_real import TruthfulQAReal
from intro_specter.benchmarks.twowiki_real import TwoWikiReal


REAL_LOADERS = [
    pytest.param(HotpotQAReal, id="hotpotqa_real"),
    pytest.param(TruthfulQAReal, id="truthfulqa_real"),
    pytest.param(StrategyQAReal, id="strategyqa_real"),
    pytest.param(TravelPlannerReal, id="travelplanner_real"),
    pytest.param(MuSiQueReal, id="musique_real"),
    pytest.param(TwoWikiReal, id="twowiki_real"),
    pytest.param(LongMemEvalReal, id="longmemeval_real"),
]


@pytest.mark.parametrize("cls", REAL_LOADERS)
def test_same_seed_same_task_ids(cls):
    """Two instantiations with seed=42 must yield identical task_id sequences."""
    a = cls(n_examples=12, seed=42, split="all")
    b = cls(n_examples=12, seed=42, split="all")
    ids_a = [ex.task_id for ex in a]
    ids_b = [ex.task_id for ex in b]
    assert ids_a == ids_b, (
        f"{cls.__name__}: non-deterministic sampling across instantiations.\n"
        f"  first run:  {ids_a[:3]}\n"
        f"  second run: {ids_b[:3]}"
    )


@pytest.mark.parametrize("cls", REAL_LOADERS)
def test_split_subsets_align(cls):
    """The test split must be a subset of the all split with matching task_ids."""
    full = cls(n_examples=10, seed=42, split="all")
    test = cls(n_examples=10, seed=42, split="test")
    full_ids = [ex.task_id for ex in full]
    test_ids = [ex.task_id for ex in test]
    assert all(t in full_ids for t in test_ids), (
        f"{cls.__name__}: test split contains task_ids not in the full split"
    )


@pytest.mark.parametrize("cls", REAL_LOADERS)
def test_different_seeds_diverge(cls):
    """Different seeds must select different underlying HF rows.

    Some loaders (TruthfulQA, TravelPlanner) build task_ids from local idx
    only, so the surface task_id label looks the same across seeds. The
    invariant that actually matters for McNemar pairing is that the
    underlying problem differs across seeds — which we check here by
    comparing prompt content, not the task_id label.
    """
    a = list(cls(n_examples=12, seed=42, split="all"))
    b = list(cls(n_examples=12, seed=43, split="all"))
    prompts_a = [ex.task["prompt"] for ex in a]
    prompts_b = [ex.task["prompt"] for ex in b]
    assert prompts_a != prompts_b, (
        f"{cls.__name__}: seed change selects the same HF rows. "
        "Seeding is effectively broken; multi-seed runs are not independent samples."
    )


@pytest.mark.parametrize("cls", REAL_LOADERS)
def test_profile_constraints_paired_per_task(cls):
    """For a given (task_id, seed), the same profile must be injected across instantiations.

    The McNemar paired tests rely on every method seeing the SAME profile
    on the same task_id; if the profile injection is non-deterministic,
    methods are comparing on subtly different problems.
    """
    a = list(cls(n_examples=10, seed=42, split="all"))
    b = list(cls(n_examples=10, seed=42, split="all"))
    for ea, eb in zip(a, b, strict=True):
        assert ea.task_id == eb.task_id
        # Compare profile span ids and texts (stable identifiers).
        spans_a = [(s.id, s.text) for s in ea.profile.spans]
        spans_b = [(s.id, s.text) for s in eb.profile.spans]
        assert spans_a == spans_b, (
            f"{cls.__name__}/{ea.task_id}: profile injection is non-deterministic across "
            f"instantiations.\n  first:  {spans_a}\n  second: {spans_b}"
        )
