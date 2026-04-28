"""Multi-seed runner end-to-end on synthetic data."""

from __future__ import annotations

import json
from pathlib import Path

from intro_specter.runner import MethodConfig, RunSpec, run


def _spec(tmp_path: Path, mode: str, seeds: list[int]) -> RunSpec:
    return RunSpec(
        benchmark="synthetic_dag",
        mode=mode,
        split="test",
        n_examples=30,
        seeds=seeds,
        output_dir=str(tmp_path),
        cache_path=str(tmp_path / "cache.sqlite"),
        verifier_provider=None,
        verifier_model="",
        methods=[
            MethodConfig(name="direct"),
            MethodConfig(name="full_regen"),
            MethodConfig(name="oracle_repair"),
            MethodConfig(name="oracle_detector"),
            MethodConfig(name="intro_specter"),
        ],
    )


def test_multi_seed_runner_writes_per_seed_jsonl_and_aggregate(tmp_path: Path) -> None:
    summary = run(_spec(tmp_path, mode="single_fault", seeds=[0, 1, 2]))
    label = "synthetic_dag__single_fault__test"
    # Per-seed × per-method JSONLs exist.
    for seed in (0, 1, 2):
        for method in ("direct", "full_regen", "oracle_repair", "oracle_detector", "intro_specter"):
            p = tmp_path / f"{label}__seed{seed}__{method}.jsonl"
            assert p.exists()
            assert sum(1 for _ in p.open()) > 0
    # Aggregate JSON lists every method.
    summary_path = tmp_path / f"{label}__summary.json"
    assert summary_path.exists()
    s = json.loads(summary_path.read_text())
    methods = s["methods"]
    for m in ("direct", "intro_specter", "oracle_detector"):
        assert m in methods
        assert "success_rate" in methods[m]
    # Non-direct methods have paired stats.
    for m in ("intro_specter", "oracle_repair", "oracle_detector", "full_regen"):
        assert "delta_success" in methods[m]
        assert "mcnemar_success_p" in methods[m]
        assert "wilcoxon_tokens_p" in methods[m]
        # Holm-Bonferroni adjusted p-values for the family.
        assert "holm_success_p_adj" in methods[m]


def test_intro_specter_beats_direct_on_synthetic(tmp_path: Path) -> None:
    summary = run(_spec(tmp_path, mode="single_fault", seeds=[0]))
    methods = summary["methods"]
    assert methods["direct"]["success_rate"] == 0.0
    assert methods["intro_specter"]["success_rate"] >= 0.9
    # Δsuccess CI for intro_specter must exclude zero.
    assert methods["intro_specter"]["delta_success_ci_low"] > 0


def test_multi_valid_runner_completes(tmp_path: Path) -> None:
    summary = run(_spec(tmp_path, mode="multi_valid", seeds=[0]))
    methods = summary["methods"]
    assert methods["intro_specter"]["success_rate"] >= 0.9
    assert methods["full_regen"]["success_rate"] >= 0.9
    # full_regen costs tokens; intro_specter (rule-based, synthetic) costs none.
    assert methods["intro_specter"]["tokens_input_mean"] == 0
    assert methods["full_regen"]["tokens_input_mean"] > 0


def test_resume_skips_completed_tasks(tmp_path: Path) -> None:
    spec = _spec(tmp_path, mode="single_fault", seeds=[0])
    # First run writes everything.
    run(spec)
    label = "synthetic_dag__single_fault__test"
    intro_path = tmp_path / f"{label}__seed0__intro_specter.jsonl"
    n_lines_before = sum(1 for _ in intro_path.open())
    # Second run should not append duplicates.
    run(spec)
    n_lines_after = sum(1 for _ in intro_path.open())
    assert n_lines_after == n_lines_before
