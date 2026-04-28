"""Layer 2 (attribution half): posterior over candidate faulty assumptions.

`p(a_k | e) ∝ p(e | a_k) p(a_k)` per the plan PDF's "Posterior and Repair Objective"
section. Priors are provenance-aware; likelihoods come from counterfactual repair
trials.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .dag import descendants_of_node
from .models import ChatProvider
from .prompts import COUNTERFACTUAL_SYSTEM, counterfactual_user
from .schemas import (
    AssumptionDAG,
    AssumptionNode,
    AttributionPosterior,
    CandidateScore,
    CounterfactualRepair,
    Provenance,
    Trajectory,
    UserProfile,
    ViolationEvent,
)


# ---------------------------------------------------------------------------
# Priors
# ---------------------------------------------------------------------------

# Default prior weights per provenance. The PDF requires that "the prior should be
# higher for unsupported model-inferred assumptions than for directly observed tool
# outputs or explicit profile facts."
DEFAULT_PROVENANCE_PRIOR: dict[Provenance, float] = {
    Provenance.MODEL_INFERRED: 1.0,
    Provenance.WORLD_KNOWLEDGE: 0.6,
    Provenance.EXTERNAL_EVIDENCE: 0.4,
    Provenance.TOOL: 0.25,
    Provenance.PROFILE: 0.15,
}


def structural_prior(
    node: AssumptionNode,
    *,
    provenance_weights: dict[Provenance, float] = DEFAULT_PROVENANCE_PRIOR,
    use_confidence: bool = True,
) -> float:
    """Unnormalized prior. Multiplied by `(1 - confidence)` so that high-confidence
    assumptions are *less* likely to be at fault.
    """
    base = provenance_weights.get(node.provenance, 0.5)
    if use_confidence:
        # Avoid zeroing out perfectly confident nodes entirely; floor at 0.05.
        base *= max(0.05, 1.0 - node.confidence)
    return base


# ---------------------------------------------------------------------------
# Counterfactual likelihood
# ---------------------------------------------------------------------------


@dataclass
class RepairTrial:
    candidate_node_id: str
    repair: CounterfactualRepair
    violation_removed: bool
    notes: str = ""


class CounterfactualSampler(ABC):
    """Generate counterfactual repairs for a candidate node and report whether each
    repair removes the violation."""

    @abstractmethod
    def sample(
        self,
        *,
        profile: UserProfile,
        task: dict[str, Any],
        dag: AssumptionDAG,
        candidate: AssumptionNode,
        trajectory: Trajectory,
        violation: ViolationEvent,
        n: int = 3,
    ) -> list[RepairTrial]: ...


class LLMCounterfactualSampler(CounterfactualSampler):
    """Calls the counterfactual-repair prompt and uses an external `evaluator`
    callback to decide whether each proposed repair removes the violation.

    The evaluator is provided by the benchmark so that this module never needs to
    re-run a real environment. It takes the proposed repair and the current
    trajectory and returns ``True`` if the violation is expected to be removed.
    """

    def __init__(
        self,
        provider: ChatProvider,
        model: str,
        evaluator: Callable[[CounterfactualRepair, Trajectory, ViolationEvent], bool],
        *,
        temperature: float = 0.7,
        seed: int | None = None,
    ) -> None:
        self.provider = provider
        self.model = model
        self.evaluator = evaluator
        self.temperature = temperature
        self.seed = seed

    def sample(
        self,
        *,
        profile: UserProfile,
        task: dict[str, Any],
        dag: AssumptionDAG,
        candidate: AssumptionNode,
        trajectory: Trajectory,
        violation: ViolationEvent,
        n: int = 3,
    ) -> list[RepairTrial]:
        user = counterfactual_user(
            profile=profile.model_dump(mode="json"),
            task=task,
            dag=dag.model_dump(mode="json"),
            candidate_node=candidate.model_dump(mode="json"),
            trajectory=trajectory.model_dump(mode="json"),
            violation=violation.model_dump(mode="json"),
        )
        payload, _ = self.provider.complete_json(
            system=COUNTERFACTUAL_SYSTEM,
            user=user,
            model=self.model,
            temperature=self.temperature,
            seed=self.seed,
        )
        repairs_raw = payload.get("repairs", [])[:n]
        trials: list[RepairTrial] = []
        for r in repairs_raw:
            try:
                repair = CounterfactualRepair.model_validate(r)
            except Exception:  # pragma: no cover - defensive
                continue
            removed = bool(self.evaluator(repair, trajectory, violation))
            trials.append(RepairTrial(candidate.id, repair, removed))
        return trials


class RuleBasedCounterfactualSampler(CounterfactualSampler):
    """Used by the synthetic benchmark and by oracle ablations.

    The benchmark supplies a `swap_fn(node) -> repair_or_None` that returns a
    counterfactual repair (e.g., the gold-correct assumption) along with an
    `evaluator` that says whether that swap removes the violation.
    """

    def __init__(
        self,
        swap_fn: Callable[[AssumptionNode], CounterfactualRepair | None],
        evaluator: Callable[[CounterfactualRepair, Trajectory, ViolationEvent], bool],
    ) -> None:
        self.swap_fn = swap_fn
        self.evaluator = evaluator

    def sample(
        self,
        *,
        profile: UserProfile,
        task: dict[str, Any],
        dag: AssumptionDAG,
        candidate: AssumptionNode,
        trajectory: Trajectory,
        violation: ViolationEvent,
        n: int = 3,
    ) -> list[RepairTrial]:
        repair = self.swap_fn(candidate)
        if repair is None:
            return []
        removed = bool(self.evaluator(repair, trajectory, violation))
        return [RepairTrial(candidate.id, repair, removed)]


# ---------------------------------------------------------------------------
# Posterior update
# ---------------------------------------------------------------------------


def posterior_update(
    *,
    candidates: list[AssumptionNode],
    dag: AssumptionDAG,
    sampler: CounterfactualSampler,
    profile: UserProfile,
    task: dict[str, Any],
    trajectory: Trajectory,
    violations: list[ViolationEvent],
    n_trials: int = 3,
    cost_lambda: float = 0.0,
    provenance_weights: dict[Provenance, float] = DEFAULT_PROVENANCE_PRIOR,
) -> tuple[AttributionPosterior, list[RepairTrial]]:
    """Compute `p(a_k | e)` for each candidate node.

    For the multi-violation case we aggregate by max-likelihood across the
    detected violations (the most-explanatory violation drives the score).
    """
    if not candidates:
        return AttributionPosterior(candidates=[], entropy=0.0, top_k=[]), []

    primary_violation = violations[0] if violations else None
    if primary_violation is None:  # pragma: no cover - guarded by caller
        return AttributionPosterior(candidates=[], entropy=0.0, top_k=[]), []

    all_trials: list[RepairTrial] = []
    raw_scores: list[CandidateScore] = []

    for cand in candidates:
        prior = structural_prior(cand, provenance_weights=provenance_weights)
        trials = sampler.sample(
            profile=profile,
            task=task,
            dag=dag,
            candidate=cand,
            trajectory=trajectory,
            violation=primary_violation,
            n=n_trials,
        )
        all_trials.extend(trials)
        if trials:
            removed = sum(1 for t in trials if t.violation_removed)
            likelihood = removed / len(trials)
        else:
            likelihood = 0.0
        cost = float(len(descendants_of_node(dag, cand.id)) + 1)  # +1 for the node itself
        raw_scores.append(
            CandidateScore(
                node_id=cand.id,
                prior=prior,
                likelihood=likelihood,
                cost=cost,
            )
        )

    Z = sum(s.prior * s.likelihood for s in raw_scores)
    if Z <= 0:
        # Fall back to prior-only if no counterfactual removed the violation.
        Z = sum(s.prior for s in raw_scores) or 1.0
        for s in raw_scores:
            s.posterior = s.prior / Z
    else:
        for s in raw_scores:
            s.posterior = (s.prior * s.likelihood) / Z

    if cost_lambda > 0:
        # Soft cost penalty (subtract before re-normalizing); only used when the
        # caller wants posterior to already incorporate edit cost.
        max_cost = max(s.cost for s in raw_scores) or 1.0
        for s in raw_scores:
            s.posterior = max(0.0, s.posterior - cost_lambda * (s.cost / max_cost))
        Z2 = sum(s.posterior for s in raw_scores) or 1.0
        for s in raw_scores:
            s.posterior /= Z2

    entropy = -sum(
        s.posterior * math.log(s.posterior + 1e-12) for s in raw_scores if s.posterior > 0
    )
    ranked = sorted(raw_scores, key=lambda s: s.posterior, reverse=True)
    top_k = [s.node_id for s in ranked[:3]]
    return AttributionPosterior(candidates=ranked, entropy=entropy, top_k=top_k), all_trials
