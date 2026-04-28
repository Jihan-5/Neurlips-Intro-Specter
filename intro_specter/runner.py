"""Experiment runner.

* Loads a benchmark (currently only ``synthetic_dag``).
* Iterates over examples, applies a method, writes one JSONL line per task.
* Supports resume by skipping any ``task_id`` already present in the output file.
* Emits a summary CSV with primary metrics and paired bootstrap CIs vs. the
  ``direct`` baseline.

Method names recognised:

* ``direct``                 — pass-through, no correction
* ``self_refine``            — Self-Refine (no-LLM fallback if no provider configured)
* ``reflexion``              — Reflexion (idem)
* ``full_regen``             — full regeneration
* ``oracle_repair``          — gold fault node + selective rerun
* ``intro_specter``          — rule-based sampler (no LLM required)
* ``intro_specter_llm``      — LLM counterfactual sampler (requires provider)
"""

from __future__ import annotations

import json
import time
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from .attribution import (
    LLMCounterfactualSampler,
    RuleBasedCounterfactualSampler,
)
from .baselines import (
    run_direct,
    run_full_regen,
    run_oracle_repair,
    run_reflexion,
    run_self_refine,
)
from .baselines.base import BaselineResult
from .benchmarks.base import BenchmarkExample
from .benchmarks.synthetic_dag import SyntheticDAGBenchmark
from .metrics.repair import degradation_rate, delta_success_rate
from .metrics.stats import paired_bootstrap_ci
from .models import build_provider
from .models.cache import SQLiteCache
from .pipeline import IntroSpecterConfig, run_intro_specter
from .schemas import CandidateScore, RunResult
from .verifier import HybridVerifier


# ---------------------------------------------------------------------------
# Method dispatch
# ---------------------------------------------------------------------------


@dataclass
class MethodConfig:
    name: str
    provider_name: str = "mock"
    model: str = ""
    temperature: float = 0.0
    seed: int = 0
    extra: dict[str, Any] = field(default_factory=dict)


def _method_runs_without_provider(name: str) -> bool:
    """`direct`, `full_regen`, `oracle_repair`, and `intro_specter` (rule-based)
    can all execute on the synthetic benchmark with no API calls."""
    return name in {"direct", "full_regen", "oracle_repair", "intro_specter"}


def run_method_on_example(
    method: MethodConfig,
    example: BenchmarkExample,
    *,
    cache: SQLiteCache | None = None,
    verifier_provider_name: str | None = None,
    verifier_model: str = "",
) -> RunResult:
    verifier = HybridVerifier(rules=list(example.rules))
    if verifier_provider_name:
        verifier.provider = build_provider(verifier_provider_name, cache=cache)
        verifier.model = verifier_model

    t0 = time.perf_counter()
    profile_violation_initial: bool | None = None
    initial_check, _ = verifier.check(
        profile=example.profile,
        task=example.task,
        trajectory=example.trajectory,
        final_output=example.trajectory.final_output,
    )
    profile_violation_initial = not initial_check.passed

    fault_node_predicted: str | None = None
    repair_status: str | None = None
    posterior_dump = None

    if method.name == "direct":
        result = run_direct(
            profile=example.profile,
            task=example.task,
            trajectory=example.trajectory,
            verifier=verifier,
        )
    elif method.name == "self_refine":
        provider = (
            build_provider(method.provider_name, cache=cache)
            if method.provider_name and method.provider_name != "none"
            else None
        )
        result = run_self_refine(
            profile=example.profile,
            task=example.task,
            trajectory=example.trajectory,
            verifier=verifier,
            provider=provider,
            model=method.model,
            temperature=method.temperature,
            seed=method.seed,
        )
    elif method.name == "reflexion":
        provider = (
            build_provider(method.provider_name, cache=cache)
            if method.provider_name and method.provider_name != "none"
            else None
        )
        result = run_reflexion(
            profile=example.profile,
            task=example.task,
            trajectory=example.trajectory,
            verifier=verifier,
            provider=provider,
            model=method.model,
            temperature=method.temperature,
            seed=method.seed,
            max_trials=int(method.extra.get("max_trials", 2)),
        )
    elif method.name == "full_regen":
        result = run_full_regen(
            profile=example.profile,
            task=example.task,
            trajectory=example.trajectory,
            verifier=verifier,
            regenerate_fn=example.regenerate_fn,
        )
    elif method.name == "oracle_repair":
        if example.gold.fault_node_id is None or example.rerun_fn is None:
            raise ValueError("oracle_repair requires gold.fault_node_id and example.rerun_fn")
        result = run_oracle_repair(
            profile=example.profile,
            task=example.task,
            trajectory=example.trajectory,
            verifier=verifier,
            dag=example.dag,
            fault_node_id=example.gold.fault_node_id,
            rerun_fn=example.rerun_fn,
        )
        fault_node_predicted = example.gold.fault_node_id
    elif method.name in {"intro_specter", "intro_specter_llm"}:
        if method.name == "intro_specter":
            if example.swap_fn is None or example.evaluator is None:
                raise ValueError(
                    "intro_specter (rule-based) requires example.swap_fn and example.evaluator"
                )
            sampler = RuleBasedCounterfactualSampler(
                swap_fn=example.swap_fn, evaluator=example.evaluator
            )
            extraction_provider = None
            reexecution_provider = None
        else:
            provider = build_provider(method.provider_name, cache=cache)
            if example.evaluator is None:
                raise ValueError("intro_specter_llm needs an evaluator")
            sampler = LLMCounterfactualSampler(
                provider=provider,
                model=method.model,
                evaluator=example.evaluator,
                temperature=method.temperature,
                seed=method.seed,
            )
            extraction_provider = provider
            reexecution_provider = provider
        cfg = IntroSpecterConfig(
            model_extraction=method.model,
            model_verification=method.model,
            model_counterfactual=method.model,
            model_reexecution=method.model,
            extraction_provider=extraction_provider,
            reexecution_provider=reexecution_provider,
            tau_abstain=float(method.extra.get("tau_abstain", 0.0)),
            cost_lambda=float(method.extra.get("cost_lambda", 0.0)),
            n_counterfactual_trials=int(method.extra.get("n_counterfactual_trials", 1)),
        )
        is_result = run_intro_specter(
            profile=example.profile,
            task=example.task,
            trajectory=example.trajectory,
            verifier=verifier,
            sampler=sampler,
            config=cfg,
            gold_dag=example.dag,  # synthetic benchmark supplies a gold DAG
            rerun_callable=example.rerun_fn,
        )
        repair_status = is_result.status
        fault_node_predicted = is_result.fault_node
        if is_result.posterior is not None:
            posterior_dump = [c.model_dump(mode="json") for c in is_result.posterior.candidates]
        result = BaselineResult(
            method=method.name,
            final_trajectory=is_result.final_trajectory,
            verifier=is_result.verifier,
            tokens_input=int(is_result.meta.get("tokens_input", 0)),
            tokens_output=int(is_result.meta.get("tokens_output", 0)),
            meta=is_result.meta,
        )
    else:
        raise KeyError(f"unknown method {method.name!r}")

    latency_ms = (time.perf_counter() - t0) * 1000.0

    success = _success(result, example)

    return RunResult(
        task_id=example.task_id,
        dataset=example.dataset,
        method=method.name,
        model=method.model,
        seed=method.seed,
        success=success,
        constraint_satisfied=result.verifier.passed,
        violation_rate=float(0 if result.verifier.passed else 1),
        profile_violation=profile_violation_initial,
        repair_status=repair_status,
        fault_node_predicted=fault_node_predicted,
        posterior=None if posterior_dump is None else [
            CandidateScore.model_validate(p) for p in posterior_dump
        ],
        final_output=result.final_trajectory.final_output,
        tokens_input=result.tokens_input,
        tokens_output=result.tokens_output,
        latency_ms=latency_ms,
        extra={"meta_summary": _meta_summary(result.meta)},
    )


def _success(result: BaselineResult, example: BenchmarkExample) -> bool:
    """Synthetic benchmark success: the final output equals the gold-correct one
    (or, less strictly, the verifier passes after repair)."""
    if not result.verifier.passed:
        return False
    gold = example.gold.correct_final_output
    if gold is None:
        return True
    return (result.final_trajectory.final_output or "").strip() == gold.strip()


def _meta_summary(meta: dict[str, Any] | None) -> dict[str, Any]:
    if not meta:
        return {}
    out = {}
    if "stages" in meta:
        out["stages"] = [s.get("stage") for s in meta["stages"]]
    if "trials" in meta:
        out["trials"] = meta["trials"]
    return out


# ---------------------------------------------------------------------------
# Top-level run
# ---------------------------------------------------------------------------


@dataclass
class RunSpec:
    benchmark: str = "synthetic_dag"
    n_examples: int = 100
    seed: int = 0
    methods: list[MethodConfig] = field(default_factory=list)
    output_dir: str = "outputs"
    cache_path: str = "cache/completions.sqlite"
    verifier_provider: str | None = None
    verifier_model: str = ""


def _build_benchmark(spec: RunSpec) -> Iterable[BenchmarkExample]:
    if spec.benchmark == "synthetic_dag":
        return SyntheticDAGBenchmark(n_examples=spec.n_examples, seed=spec.seed)
    raise KeyError(f"unknown benchmark {spec.benchmark!r}")


def _existing_task_ids(jsonl_path: Path) -> set[str]:
    if not jsonl_path.exists():
        return set()
    ids: set[str] = set()
    with jsonl_path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ids.add(json.loads(line)["task_id"])
            except (json.JSONDecodeError, KeyError):
                continue
    return ids


def run(spec: RunSpec) -> dict[str, Any]:
    out_dir = Path(spec.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cache = SQLiteCache(spec.cache_path) if spec.cache_path else None
    benchmark = list(_build_benchmark(spec))

    per_method_paths: dict[str, Path] = {}
    for method in spec.methods:
        per_method_paths[method.name] = out_dir / f"{spec.benchmark}__{method.name}.jsonl"

    summary = {"methods": {}, "benchmark": spec.benchmark, "n": len(benchmark)}

    for method in spec.methods:
        path = per_method_paths[method.name]
        done = _existing_task_ids(path)
        with path.open("a") as f:
            for example in benchmark:
                if example.task_id in done:
                    continue
                run_res = run_method_on_example(
                    method,
                    example,
                    cache=cache,
                    verifier_provider_name=spec.verifier_provider,
                    verifier_model=spec.verifier_model,
                )
                f.write(json.dumps(run_res.model_dump(mode="json"), default=str) + "\n")
                f.flush()

    # Aggregate: load every method JSONL and build per-task wide table.
    rows = []
    for method in spec.methods:
        with per_method_paths[method.name].open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rows.append(json.loads(line))
    df = pd.DataFrame(rows)
    if df.empty:
        return summary
    df.to_csv(out_dir / f"{spec.benchmark}__results_long.csv", index=False)

    pivoted = df.pivot_table(
        index="task_id",
        columns="method",
        values=["success", "tokens_input", "tokens_output", "violation_rate"],
        aggfunc="first",
    )
    pivoted.to_csv(out_dir / f"{spec.benchmark}__results_wide.csv")

    # Per-method aggregate metrics + paired CI vs. direct (when available).
    methods_present = sorted(df["method"].unique())
    by_method = {
        m: df[df["method"] == m].sort_values("task_id").reset_index(drop=True)
        for m in methods_present
    }
    direct_df = by_method.get("direct")
    method_summaries = {}
    for m, sub in by_method.items():
        s = {
            "n": int(len(sub)),
            "success_rate": float(sub["success"].mean()),
            "violation_rate": float(sub["violation_rate"].mean()),
            "tokens_input_mean": float(sub["tokens_input"].mean()),
            "tokens_output_mean": float(sub["tokens_output"].mean()),
            "latency_ms_mean": float(sub["latency_ms"].mean()),
        }
        if direct_df is not None and m != "direct" and len(sub) == len(direct_df):
            ci = paired_bootstrap_ci(
                direct_df["success"].astype(int).tolist(),
                sub["success"].astype(int).tolist(),
            )
            s["delta_success_vs_direct"] = ci.point
            s["delta_success_ci_low"] = ci.low
            s["delta_success_ci_high"] = ci.high
            s["degradation_rate_vs_direct"] = degradation_rate(
                direct_df["success"].astype(bool).tolist(),
                sub["success"].astype(bool).tolist(),
            )
            s["delta_success_rate_vs_direct"] = delta_success_rate(
                direct_df["success"].astype(bool).tolist(),
                sub["success"].astype(bool).tolist(),
            )
        method_summaries[m] = s
    summary["methods"] = method_summaries

    with (out_dir / f"{spec.benchmark}__summary.json").open("w") as f:
        json.dump(summary, f, indent=2, default=str)

    summary_df = pd.DataFrame(method_summaries).T
    summary_df.to_csv(out_dir / f"{spec.benchmark}__summary.csv")

    return summary
