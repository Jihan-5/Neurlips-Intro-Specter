"""Experiment runner.

Multi-seed, multi-mode, multi-split. Per (benchmark, mode, split, seed,
method) run, writes one JSONL line per task, supports resume by skipping
already-recorded ``task_id``s, and produces:

* a per-row long-format CSV;
* a wide-format pivot keyed by (task_id, seed);
* a method-level aggregate JSON / CSV with mean metrics and **paired stats vs.
  direct**: bootstrap CIs for Δsuccess and Δtokens, McNemar's test on success,
  Wilcoxon signed-rank on tokens, Holm-Bonferroni p-value adjustment across
  (success × violation × tokens) × (non-direct methods).
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
    run_oracle_detector,
    run_oracle_repair,
    run_reflexion,
    run_self_refine,
)
from .baselines.base import BaselineResult
from .benchmarks.base import BenchmarkExample
from .benchmarks.synthetic_dag import SyntheticDAGBenchmark
from .metrics.repair import degradation_rate, delta_success_rate
from .metrics.stats import (
    holm_bonferroni,
    mcnemar,
    paired_bootstrap_ci,
    wilcoxon_signed_rank,
)
from .models import build_provider
from .models.cache import SQLiteCache
from .pipeline import IntroSpecterConfig, run_intro_specter
from .repair import CostModel
from .schemas import CandidateScore, RunResult
from .verifier import HybridVerifier


# ---------------------------------------------------------------------------
# Method dispatch
# ---------------------------------------------------------------------------


@dataclass
class MethodConfig:
    name: str
    provider_name: str = "none"
    model: str = ""
    temperature: float = 0.0
    seed: int = 0
    extra: dict[str, Any] = field(default_factory=dict)


def run_method_on_example(
    method: MethodConfig,
    example: BenchmarkExample,
    *,
    cache: SQLiteCache | None = None,
    verifier_provider_name: str | None = None,
    verifier_model: str = "",
    seed_override: int | None = None,
) -> RunResult:
    method_seed = seed_override if seed_override is not None else method.seed

    verifier = HybridVerifier(rules=list(example.rules))
    if verifier_provider_name and verifier_provider_name != "none":
        verifier.provider = build_provider(verifier_provider_name, cache=cache)
        verifier.model = verifier_model

    initial_check, _ = verifier.check(
        profile=example.profile,
        task=example.task,
        trajectory=example.trajectory,
        final_output=example.trajectory.final_output,
    )
    profile_violation_initial: bool = not initial_check.passed

    fault_node_predicted: str | None = None
    repair_status: str | None = None
    posterior_dump: list[dict[str, Any]] | None = None

    t0 = time.perf_counter()

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
            seed=method_seed,
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
            seed=method_seed,
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
    elif method.name == "oracle_detector":
        if example.swap_fn is None or example.evaluator is None or example.rerun_fn is None:
            raise ValueError(
                "oracle_detector requires example.swap_fn, evaluator, rerun_fn"
            )
        sampler = RuleBasedCounterfactualSampler(
            swap_fn=example.swap_fn, evaluator=example.evaluator
        )
        result = run_oracle_detector(
            profile=example.profile,
            task=example.task,
            trajectory=example.trajectory,
            verifier=verifier,
            dag=example.dag,
            gold_violations=list(example.gold_violations),
            sampler=sampler,
            rerun_fn=example.rerun_fn,
            cost_model=CostModel(),
            tau_abstain=float(method.extra.get("tau_abstain", 0.0)),
            n_counterfactual_trials=int(method.extra.get("n_counterfactual_trials", 1)),
        )
        fault_node_predicted = result.meta.get("fault_node_predicted")
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
                seed=method_seed,
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
            gold_dag=example.dag,
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
        seed=method_seed,
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
        extra={"split": example.split, "meta_summary": _meta_summary(result.meta)},
    )


def _success(result: BaselineResult, example: BenchmarkExample) -> bool:
    """Synthetic / dataset-aware success: verifier passes AND (if a gold output
    is provided) the final output matches it modulo whitespace."""
    if not result.verifier.passed:
        return False
    gold = example.gold.correct_final_output
    if gold is None:
        return True
    return (result.final_trajectory.final_output or "").strip() == gold.strip()


def _meta_summary(meta: dict[str, Any] | None) -> dict[str, Any]:
    if not meta:
        return {}
    out: dict[str, Any] = {}
    if "stages" in meta:
        out["stages"] = [s.get("stage") for s in meta["stages"]]
    if "trials" in meta:
        out["trials"] = meta["trials"]
    if "fault_node_predicted" in meta:
        out["fault_node_predicted"] = meta["fault_node_predicted"]
    return out


# ---------------------------------------------------------------------------
# Top-level run
# ---------------------------------------------------------------------------


@dataclass
class RunSpec:
    benchmark: str = "synthetic_dag"
    mode: str | None = None  # synthetic_dag: "single_fault" or "multi_valid"
    split: str = "all"        # "train" | "val" | "test" | "all"
    n_examples: int = 100
    seeds: list[int] = field(default_factory=lambda: [0])
    methods: list[MethodConfig] = field(default_factory=list)
    output_dir: str = "outputs"
    cache_path: str = "cache/completions.sqlite"
    verifier_provider: str | None = None
    verifier_model: str = ""


def _build_benchmark(spec: RunSpec, seed: int) -> Iterable[BenchmarkExample]:
    if spec.benchmark == "synthetic_dag":
        if spec.mode is None:
            raise ValueError("synthetic_dag requires mode={'single_fault' | 'multi_valid'}")
        return SyntheticDAGBenchmark(
            n_examples=spec.n_examples,
            seed=seed,
            mode=spec.mode,  # type: ignore[arg-type]
            split=spec.split,  # type: ignore[arg-type]
        )
    raise KeyError(f"unknown benchmark {spec.benchmark!r}")


def _benchmark_label(spec: RunSpec) -> str:
    parts = [spec.benchmark]
    if spec.mode:
        parts.append(spec.mode)
    parts.append(spec.split)
    return "__".join(parts)


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
    label = _benchmark_label(spec)

    # ---- Per (seed, method) JSONL writes ----
    for seed in spec.seeds:
        bench_examples = list(_build_benchmark(spec, seed))
        for method in spec.methods:
            path = out_dir / f"{label}__seed{seed}__{method.name}.jsonl"
            done = _existing_task_ids(path)
            with path.open("a") as f:
                for example in bench_examples:
                    if example.task_id in done:
                        continue
                    res = run_method_on_example(
                        method,
                        example,
                        cache=cache,
                        verifier_provider_name=spec.verifier_provider,
                        verifier_model=spec.verifier_model,
                        seed_override=seed,
                    )
                    f.write(json.dumps(res.model_dump(mode="json"), default=str) + "\n")
                    f.flush()

    # ---- Aggregate ----
    rows: list[dict[str, Any]] = []
    for seed in spec.seeds:
        for method in spec.methods:
            path = out_dir / f"{label}__seed{seed}__{method.name}.jsonl"
            if not path.exists():
                continue
            with path.open() as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    rows.append(json.loads(line))
    if not rows:
        return {"benchmark": label, "n": 0, "seeds": spec.seeds, "methods": {}}

    df = pd.DataFrame(rows)
    df.to_csv(out_dir / f"{label}__results_long.csv", index=False)

    summary: dict[str, Any] = {
        "benchmark": label,
        "n_examples": int(df["task_id"].nunique()),
        "n_total_rows": int(len(df)),
        "seeds": spec.seeds,
        "split": spec.split,
        "mode": spec.mode,
        "methods": {},
    }

    methods_present = sorted(df["method"].unique())
    by_method: dict[str, pd.DataFrame] = {}
    for m in methods_present:
        sub = df[df["method"] == m].sort_values(["task_id", "seed"]).reset_index(drop=True)
        by_method[m] = sub

    direct_df = by_method.get("direct")
    pvals_for_holm: dict[tuple[str, str], float] = {}
    method_summaries: dict[str, dict[str, Any]] = {}

    for m, sub in by_method.items():
        s: dict[str, Any] = {
            "n": int(len(sub)),
            "success_rate": float(sub["success"].mean()),
            "violation_rate": float(sub["violation_rate"].mean()),
            "tokens_input_mean": float(sub["tokens_input"].mean()),
            "tokens_output_mean": float(sub["tokens_output"].mean()),
            "latency_ms_mean": float(sub["latency_ms"].mean()),
        }
        if direct_df is None or m == "direct":
            method_summaries[m] = s
            continue
        # Align on (task_id, seed) pairs.
        merged = sub.merge(
            direct_df[["task_id", "seed", "success", "tokens_input", "tokens_output", "violation_rate"]],
            on=["task_id", "seed"],
            suffixes=("", "_direct"),
        )
        if merged.empty:
            method_summaries[m] = s
            continue
        # Δsuccess: paired bootstrap + McNemar
        ci_succ = paired_bootstrap_ci(
            merged["success_direct"].astype(int).tolist(),
            merged["success"].astype(int).tolist(),
        )
        mc = mcnemar(
            merged["success_direct"].astype(bool).tolist(),
            merged["success"].astype(bool).tolist(),
        )
        # Δtokens: paired bootstrap + Wilcoxon
        ci_tok = paired_bootstrap_ci(
            (merged["tokens_input_direct"] + merged["tokens_output_direct"]).astype(float).tolist(),
            (merged["tokens_input"] + merged["tokens_output"]).astype(float).tolist(),
        )
        wx = wilcoxon_signed_rank(
            (merged["tokens_input_direct"] + merged["tokens_output_direct"]).astype(float).tolist(),
            (merged["tokens_input"] + merged["tokens_output"]).astype(float).tolist(),
        )
        # Δviolation: paired bootstrap + McNemar (binary indicator)
        ci_viol = paired_bootstrap_ci(
            merged["violation_rate_direct"].astype(float).tolist(),
            merged["violation_rate"].astype(float).tolist(),
        )
        mc_viol = mcnemar(
            (merged["violation_rate_direct"].astype(float) > 0.5).tolist(),
            (merged["violation_rate"].astype(float) > 0.5).tolist(),
        )
        s.update({
            "delta_success": ci_succ.point,
            "delta_success_ci_low": ci_succ.low,
            "delta_success_ci_high": ci_succ.high,
            "mcnemar_success_p": mc.pvalue,
            "delta_tokens": ci_tok.point,
            "delta_tokens_ci_low": ci_tok.low,
            "delta_tokens_ci_high": ci_tok.high,
            "wilcoxon_tokens_p": wx.pvalue,
            "delta_violation": ci_viol.point,
            "delta_violation_ci_low": ci_viol.low,
            "delta_violation_ci_high": ci_viol.high,
            "mcnemar_violation_p": mc_viol.pvalue,
            "degradation_rate": degradation_rate(
                merged["success_direct"].astype(bool).tolist(),
                merged["success"].astype(bool).tolist(),
            ),
            "delta_success_per_task": delta_success_rate(
                merged["success_direct"].astype(bool).tolist(),
                merged["success"].astype(bool).tolist(),
            ),
        })
        pvals_for_holm[(m, "success")] = mc.pvalue
        pvals_for_holm[(m, "tokens")] = wx.pvalue
        pvals_for_holm[(m, "violation")] = mc_viol.pvalue
        method_summaries[m] = s

    # ---- Holm-Bonferroni adjustment across (method × metric) family ----
    if pvals_for_holm:
        keys = list(pvals_for_holm.keys())
        ps = [pvals_for_holm[k] for k in keys]
        rejected, adjusted = holm_bonferroni(ps, alpha=0.05)
        for (m, metric), adj_p, rej in zip(keys, adjusted, rejected, strict=True):
            method_summaries[m][f"holm_{metric}_p_adj"] = adj_p
            method_summaries[m][f"holm_{metric}_reject"] = rej

    summary["methods"] = method_summaries

    with (out_dir / f"{label}__summary.json").open("w") as f:
        json.dump(summary, f, indent=2, default=str)

    pd.DataFrame(method_summaries).T.to_csv(out_dir / f"{label}__summary.csv")

    # ---- Per-seed pivots for the wide table ----
    pivot = df.pivot_table(
        index=["task_id", "seed"],
        columns="method",
        values=["success", "tokens_input", "tokens_output", "violation_rate", "fault_node_predicted"],
        aggfunc="first",
    )
    pivot.to_csv(out_dir / f"{label}__results_wide.csv")

    return summary
