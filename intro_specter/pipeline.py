"""Top-level Intro-Specter pipeline.

Mirrors the `intro_specter(...)` pseudocode in the plan PDF: build DAG → verify →
candidates = ancestors → posterior → abstain-or-repair.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field, replace
from typing import Any

from .attribution import (
    DEFAULT_PROVENANCE_PRIOR,
    CounterfactualSampler,
    posterior_update,
)
from .dag import candidate_nodes_for_violations
from .extraction import build_assumption_dag, passthrough_dag
from .models import ChatProvider
from .repair import (
    CostModel,
    choose_repair_node,
    rerun_downstream_subgraph_callable,
    rerun_downstream_subgraph_llm,
)
from .schemas import (
    AssumptionDAG,
    AttributionPosterior,
    CandidateScore,
    Provenance,
    RepairDecision,
    Trajectory,
    TrajectoryStep,
    UserProfile,
    VerifierResult,
)
from .verifier import HybridVerifier


@dataclass
class IntroSpecterConfig:
    model_extraction: str = ""
    model_verification: str = ""
    model_counterfactual: str = ""
    model_reexecution: str = ""
    extraction_provider: ChatProvider | None = None
    reexecution_provider: ChatProvider | None = None
    cost_model: CostModel = field(default_factory=CostModel)
    tau_abstain: float = 0.0
    cost_lambda: float = 0.0
    n_counterfactual_trials: int = 3
    provenance_weights: dict[Provenance, float] = field(default_factory=lambda: dict(DEFAULT_PROVENANCE_PRIOR))
    # ---- Ablation toggles (all default off = full method) ----
    flat_dag: bool = False           # drop dependency edges before attribution
    uniform_prior: bool = False      # all candidates get equal prior (1.0)
    skip_likelihood: bool = False    # posterior = prior only (no counterfactual sampling)
    disable_cost: bool = False       # choose_repair_node picks argmax posterior, ignores cost
    use_confidence_in_prior: bool = True  # multiply prior by (1 - confidence)
    # ---- Sequential Posterior Refinement (SPR) ----
    # When the first targeted repair does not satisfy the verifier, that failure is
    # partial evidence against the tried candidate (it could be the wrong fault, or
    # the right fault with a bad repair). We down-weight tried candidates by a
    # Bayesian decay factor `spr_decay_alpha` and renormalize, then re-select the
    # next argmax. alpha=0.0 = hard exclusion, alpha=1.0 = no learning from failure;
    # 0.1 is the default (frozen on dev split). spr_max_rounds=0 disables SPR
    # (used by the no-SPR ablation in Table 9).
    spr_max_rounds: int = 2
    spr_decay_alpha: float = 0.1


@dataclass
class IntroSpecterResult:
    status: str
    final_trajectory: Trajectory
    dag: AssumptionDAG
    verifier: VerifierResult
    posterior: AttributionPosterior | None
    decision: RepairDecision | None
    fault_node: str | None
    meta: dict[str, Any] = field(default_factory=dict)


def run_intro_specter(
    *,
    profile: UserProfile,
    task: dict[str, Any],
    trajectory: Trajectory,
    verifier: HybridVerifier,
    sampler: CounterfactualSampler,
    config: IntroSpecterConfig,
    gold_dag: AssumptionDAG | None = None,
    rerun_callable: Callable[
        [list[TrajectoryStep], Any, AssumptionDAG], tuple[list[TrajectoryStep], str | None]
    ] | None = None,
) -> IntroSpecterResult:
    """End-to-end Intro-Specter pass on one task.

    Either ``gold_dag`` or ``config.extraction_provider`` must be provided. If
    ``rerun_callable`` is set, downstream re-execution is delegated to it (used by
    synthetic benchmarks). Otherwise we call the LLM re-execution prompt with
    ``config.reexecution_provider``.
    """
    meta: dict[str, Any] = {"tokens_input": 0, "tokens_output": 0, "stages": []}

    # ---- Layer 1: build/load Assumption-DAG ----
    if gold_dag is not None:
        dag, dag_meta = passthrough_dag(gold_dag)
    else:
        if config.extraction_provider is None or not config.model_extraction:
            raise ValueError(
                "either gold_dag or (config.extraction_provider, model_extraction) must be set"
            )
        dag, dag_meta = build_assumption_dag(
            profile=profile,
            task=task,
            trajectory=trajectory,
            provider=config.extraction_provider,
            model=config.model_extraction,
        )
        meta["tokens_input"] += dag_meta.get("tokens_input", 0)
        meta["tokens_output"] += dag_meta.get("tokens_output", 0)
    if config.flat_dag:
        # Ablation: strip dependency edges so attribution treats candidates as siblings.
        dag = dag.model_copy(update={"edges": []})
        dag_meta["flat_dag_applied"] = True
    if config.uniform_prior:
        # Ablation: replace per-provenance weights with uniform 1.0 (no provenance bias).
        from .schemas import Provenance as _P
        config = replace(config, provenance_weights={p: 1.0 for p in _P})
    meta["stages"].append({"stage": "extraction", **dag_meta})

    # ---- Layer 2a: detection ----
    verifier_result, ver_meta = verifier.check(
        profile=profile,
        task=task,
        trajectory=trajectory,
        final_output=trajectory.final_output,
    )
    meta["tokens_input"] += ver_meta.get("llm_tokens_input", 0)
    meta["tokens_output"] += ver_meta.get("llm_tokens_output", 0)
    meta["stages"].append({"stage": "verifier", **ver_meta})

    if verifier_result.passed:
        return IntroSpecterResult(
            status="accepted",
            final_trajectory=trajectory,
            dag=dag,
            verifier=verifier_result,
            posterior=None,
            decision=None,
            fault_node=None,
            meta=meta,
        )

    # ---- Layer 2b: posterior attribution ----
    candidates = candidate_nodes_for_violations(dag, verifier_result.violations)
    if config.skip_likelihood:
        # Ablation: prior-only posterior (no counterfactual sampling).
        from .attribution import (
            structural_prior as _sp,
            DEFAULT_PROVENANCE_PRIOR as _DEF,
        )
        weights = config.provenance_weights or _DEF
        priors = []
        for c in candidates:
            p = _sp(c, provenance_weights=weights, use_confidence=config.use_confidence_in_prior)
            priors.append(p)
        Z = sum(priors) or 1.0
        from .schemas import (
            AttributionPosterior as _AP,
            CandidateScore as _CS,
        )
        ranked = [
            _CS(node_id=c.id, prior=priors[i], likelihood=1.0,
                cost=float(len([n for n in dag.nodes if c.id in n.depends_on]) + 1),
                posterior=priors[i] / Z)
            for i, c in enumerate(candidates)
        ]
        ranked.sort(key=lambda s: s.posterior, reverse=True)
        posterior = _AP(
            candidates=ranked,
            entropy=0.0,
            top_k=[s.node_id for s in ranked[:3]],
        )
        trials = []
    else:
        posterior, trials = posterior_update(
            candidates=candidates,
            dag=dag,
            sampler=sampler,
            profile=profile,
            task=task,
            trajectory=trajectory,
            violations=verifier_result.violations,
            n_trials=config.n_counterfactual_trials,
            cost_lambda=config.cost_lambda,
            provenance_weights=config.provenance_weights,
        )
    meta["stages"].append(
        {"stage": "attribution", "n_candidates": len(candidates), "n_trials": len(trials)}
    )

    # ---- Layer 3: repair decision ----
    cost_model_eff = config.cost_model
    if config.disable_cost:
        # Ablation: zero out cost so the selector picks argmax(posterior).
        from .repair import CostModel as _CM
        cost_model_eff = _CM(w_desc=0.0, w_tokens=0.0, w_corruption=0.0)
    decision = choose_repair_node(
        posterior=posterior,
        dag=dag,
        cost_model=cost_model_eff,
        tau_abstain=config.tau_abstain,
    )
    meta["stages"].append({"stage": "decision", "status": decision.status})

    if decision.status != "repaired" or decision.fault_node is None:
        return IntroSpecterResult(
            status=decision.status,
            final_trajectory=trajectory,
            dag=dag,
            verifier=verifier_result,
            posterior=posterior,
            decision=decision,
            fault_node=None,
            meta=meta,
        )

    # ---- Layer 3 cont.: re-execute downstream ----
    if rerun_callable is not None:
        new_traj = rerun_downstream_subgraph_callable(
            trajectory=trajectory,
            dag=dag,
            fault_node_id=decision.fault_node,
            rerun_fn=rerun_callable,
        )
    else:
        if config.reexecution_provider is None or not config.model_reexecution:
            raise ValueError(
                "either rerun_callable or (config.reexecution_provider, model_reexecution)"
                " must be set"
            )
        # Use the top trial's repair text if available, else fall back to "unknown".
        repaired_assumption = "(repaired by re-execution prompt)"
        new_traj = rerun_downstream_subgraph_llm(
            profile=profile,
            task=task,
            trajectory=trajectory,
            dag=dag,
            fault_node_id=decision.fault_node,
            repaired_assumption=repaired_assumption,
            provider=config.reexecution_provider,
            model=config.model_reexecution,
        )

    # Re-verify after repair so the caller learns whether it stuck.
    post_verifier, _ = verifier.check(
        profile=profile,
        task=task,
        trajectory=new_traj,
        final_output=new_traj.final_output,
    )
    meta["stages"].append({"stage": "post_verifier", "passed": post_verifier.passed})

    # ---- Layer 4: Sequential Posterior Refinement (SPR) ----
    # If targeted repair at n* did not satisfy the verifier, that failure is partial
    # evidence against n* being the fault: it could mean n* is the wrong candidate,
    # or that n* is the right candidate where the LLM failed to generate a valid
    # downstream trajectory. We down-weight tried candidates by `spr_decay_alpha`
    # rather than excluding them outright (Eq. 7 in the paper). Pure sequential
    # Bayesian inference over the same Assumption-DAG --- no external model, no
    # verbal reflection. Bounded by `config.spr_max_rounds`.
    last_traj: Trajectory = new_traj
    last_verdict: VerifierResult = post_verifier
    last_decision: RepairDecision = decision
    last_posterior: AttributionPosterior = posterior
    tried_nodes: set[str] = {decision.fault_node}

    if not post_verifier.passed and config.spr_max_rounds > 0:
        import math as _math
        alpha = max(0.0, min(1.0, config.spr_decay_alpha))
        for round_idx in range(config.spr_max_rounds):
            # Soft-decay update: tried candidates get their posterior multiplied by
            # alpha; untried candidates keep their posterior; renormalize over both.
            untried = [c for c in posterior.candidates if c.node_id not in tried_nodes]
            tried_scores = [c for c in posterior.candidates if c.node_id in tried_nodes]
            Z = (alpha * sum(c.posterior for c in tried_scores)
                 + sum(c.posterior for c in untried)) or 1.0
            updated_scores = [
                CandidateScore(
                    node_id=c.node_id,
                    prior=c.prior,
                    likelihood=c.likelihood,
                    cost=c.cost,
                    posterior=(alpha if c.node_id in tried_nodes else 1.0) * c.posterior / Z,
                )
                for c in posterior.candidates
            ]
            # Stop if every remaining candidate has effectively zero posterior mass
            # (e.g., when alpha=0 and we've exhausted untried candidates).
            if not untried:
                meta["stages"].append({"stage": f"spr_round_{round_idx+1}", "exhausted": True})
                break
            updated_scores.sort(key=lambda s: s.posterior, reverse=True)
            ent = -sum(
                s.posterior * _math.log(s.posterior + 1e-12)
                for s in updated_scores if s.posterior > 0
            )
            spr_posterior = AttributionPosterior(
                candidates=updated_scores,
                entropy=ent,
                top_k=[s.node_id for s in updated_scores[:3]],
            )
            spr_decision = choose_repair_node(
                posterior=spr_posterior,
                dag=dag,
                cost_model=cost_model_eff,
                tau_abstain=config.tau_abstain,
            )
            meta["stages"].append({
                "stage": f"spr_round_{round_idx+1}_decision",
                "status": spr_decision.status,
                "fault_node": spr_decision.fault_node,
            })
            if spr_decision.status != "repaired" or spr_decision.fault_node is None:
                break
            # If the soft-decay still let a tried candidate win the argmax (rare;
            # only when its posterior was much larger than the next-best), force
            # the next-best untried candidate to break the loop.
            if spr_decision.fault_node in tried_nodes:
                next_best = max(untried, key=lambda c: c.posterior, default=None)
                if next_best is None:
                    break
                spr_decision = spr_decision.model_copy(update={"fault_node": next_best.node_id})
            if rerun_callable is not None:
                spr_traj = rerun_downstream_subgraph_callable(
                    trajectory=trajectory,
                    dag=dag,
                    fault_node_id=spr_decision.fault_node,
                    rerun_fn=rerun_callable,
                )
            else:
                if config.reexecution_provider is None or not config.model_reexecution:
                    break
                spr_traj = rerun_downstream_subgraph_llm(
                    profile=profile,
                    task=task,
                    trajectory=trajectory,
                    dag=dag,
                    fault_node_id=spr_decision.fault_node,
                    repaired_assumption="(repaired by SPR re-execution)",
                    provider=config.reexecution_provider,
                    model=config.model_reexecution,
                )
            spr_verdict, _ = verifier.check(
                profile=profile,
                task=task,
                trajectory=spr_traj,
                final_output=spr_traj.final_output,
            )
            meta["stages"].append({
                "stage": f"spr_round_{round_idx+1}_post_verifier",
                "passed": spr_verdict.passed,
            })
            tried_nodes.add(spr_decision.fault_node)
            last_traj = spr_traj
            last_verdict = spr_verdict
            last_decision = spr_decision
            last_posterior = spr_posterior
            if spr_verdict.passed:
                return IntroSpecterResult(
                    status="repaired_via_spr",
                    final_trajectory=spr_traj,
                    dag=dag,
                    verifier=spr_verdict,
                    posterior=spr_posterior,
                    decision=spr_decision,
                    fault_node=spr_decision.fault_node,
                    meta=meta,
                )

    return IntroSpecterResult(
        status="repaired" if last_verdict.passed else "repair_failed",
        final_trajectory=last_traj,
        dag=dag,
        verifier=last_verdict,
        posterior=last_posterior,
        decision=last_decision,
        fault_node=last_decision.fault_node,
        meta=meta,
    )
