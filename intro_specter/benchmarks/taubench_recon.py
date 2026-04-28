"""tau-bench reconstruction.

The original tau-bench (Yao et al. 2024) evaluates LLM agents on realistic
user-agent-tool-policy interactions and reports pass^k. We don't reproduce
the tool-use simulator here — it's not feasible inside a 9-day window. The
plan PDF allows a "tau-bench-style" reconstruction that preserves the
*policy-compliance* core: the agent must follow a stated policy when making
a decision about a user request, and is graded on whether the decision
matches the policy outcome.

Each example is a single-turn customer-support decision task:

* Profile contains: customer tier, days since purchase, prior return count,
  membership status. The first three together determine policy outcome
  (refund / partial / deny / escalate) per a fixed rule book.
* Task: respond to a refund / waiver / exception request.
* Verifier: the agent's stated decision must match the policy gold.

Faults the agent can make: misread the tier, miscount the days, miss the
prior-returns blocker, or misapply the rule book to a correctly-read profile.
The Intro-Specter pipeline should localise the misread on attribution.
"""

from __future__ import annotations

import random
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, Literal

from ..schemas import (
    AssumptionDAG,
    GoldLabels,
    ProfileSpan,
    Severity,
    Trajectory,
    UserProfile,
    ViolationEvent,
)
from .base import BenchmarkExample

TIERS = ["gold", "silver", "standard"]
REQUEST_TYPES = ["refund", "exchange", "fee_waiver"]

Split = Literal["train", "val", "test", "all"]


def _policy_decision(tier: str, days_since: int, prior_returns: int) -> str:
    """The fixed rule book the agent must follow.

    Documented here so the verifier rule and the prompt template stay in sync.
    """
    if prior_returns >= 3:
        return "deny"
    if tier == "gold":
        return "refund"
    if tier == "silver" and days_since <= 30:
        return "refund"
    if tier == "silver":
        return "partial"
    if tier == "standard" and days_since <= 14:
        return "refund"
    if tier == "standard" and days_since <= 30:
        return "partial"
    return "deny"


_POLICY_TEXT = """\
POLICY (fixed rule book):
- If the customer has 3+ prior returns this year, the answer is always 'deny'.
- Otherwise, gold-tier customers always get 'refund'.
- Silver-tier customers within 30 days of purchase get 'refund', otherwise 'partial'.
- Standard-tier customers within 14 days get 'refund', within 15-30 days get 'partial', else 'deny'.

Respond with one word as the decision: refund, partial, or deny. Then briefly
state the rule that justifies your decision in one sentence.
"""


def _build_profile(rng: random.Random, idx: int) -> tuple[UserProfile, dict[str, Any]]:
    tier = rng.choice(TIERS)
    days = rng.choice([5, 12, 18, 25, 35, 60, 90])
    prior_returns = rng.choice([0, 1, 2, 3, 4])
    request_type = rng.choice(REQUEST_TYPES)
    spans = [
        ProfileSpan(id="p_tier", text=f"Customer tier is {tier}", kind="fact", is_hard=False),
        ProfileSpan(id="p_days", text=f"It has been {days} days since the customer's purchase",
                    kind="fact", is_hard=False),
        ProfileSpan(id="p_prior",
                    text=f"Customer has {prior_returns} prior returns this year",
                    kind="fact", is_hard=False),
        ProfileSpan(id="p_request",
                    text=f"The customer is requesting a {request_type}",
                    kind="fact", is_hard=False),
    ]
    profile = UserProfile(user_id=f"taubench_user_{idx:04d}", spans=spans)
    facts = {
        "tier": tier, "days": days, "prior_returns": prior_returns, "request_type": request_type,
        "gold_decision": _policy_decision(tier, days, prior_returns),
    }
    return profile, facts


def _decision_rule(facts: dict[str, Any]):
    """Verifier rule: the agent's first decision word must match the gold."""
    gold = facts["gold_decision"]
    other_words = [w for w in {"refund", "partial", "deny"} if w != gold]

    def rule(profile, task, trajectory, final_output):
        text = (final_output or "").lower()
        # Look for the gold decision word; absent → violation.
        out: list[ViolationEvent] = []
        if gold not in text:
            out.append(ViolationEvent(
                violation_id="v_decision_miss",
                step_id=trajectory.steps[-1].step_id if trajectory.steps else 0,
                violated_constraint=f"agent decision must match policy gold={gold!r}",
                trajectory_text=(final_output or "")[:200],
                severity=Severity.HIGH,
                explanation="gold decision word not present",
            ))
        # If multiple decision words are present and the gold isn't first, also flag.
        first_decision = None
        for w in ("refund", "partial", "deny"):
            i = text.find(w)
            if i >= 0 and (first_decision is None or i < first_decision[1]):
                first_decision = (w, i)
        if first_decision and first_decision[0] != gold:
            out.append(ViolationEvent(
                violation_id="v_decision_wrong_first",
                step_id=trajectory.steps[-1].step_id if trajectory.steps else 0,
                violated_constraint=f"first decision word is {first_decision[0]!r}, gold is {gold!r}",
                trajectory_text=(final_output or "")[:200],
                severity=Severity.HIGH,
                explanation="agent committed to a decision other than the policy outcome",
            ))
        return out

    rule.__name__ = "taubench_recon_rule"
    return rule


@dataclass
class TauBenchRecon:
    n_examples: int = 100
    seed: int = 0
    split: Split = "all"
    train_frac: float = 0.6
    val_frac: float = 0.2

    @property
    def name(self) -> str:
        return "taubench_recon"

    def __len__(self) -> int:
        return len(self._indices())

    def __iter__(self) -> Iterator[BenchmarkExample]:
        for idx in self._indices():
            yield self._build_example(idx)

    def _indices(self) -> list[int]:
        n = self.n_examples
        train_end = int(n * self.train_frac)
        val_end = int(n * (self.train_frac + self.val_frac))
        if self.split == "train":
            return list(range(0, train_end))
        if self.split == "val":
            return list(range(train_end, val_end))
        if self.split == "test":
            return list(range(val_end, n))
        return list(range(n))

    def split_of(self, idx: int) -> Split:
        n = self.n_examples
        train_end = int(n * self.train_frac)
        val_end = int(n * (self.train_frac + self.val_frac))
        if idx < train_end:
            return "train"
        if idx < val_end:
            return "val"
        return "test"

    def _build_example(self, idx: int) -> BenchmarkExample:
        rng = random.Random(self.seed * 1_000_003 + idx)
        profile, facts = _build_profile(rng, idx)
        task_id = f"taubench_recon_{idx:05d}"
        prompt = (
            f"The customer is requesting a {facts['request_type']} for a recent purchase. "
            "Apply the policy below to decide what to grant. Output only the decision and "
            "a one-sentence justification.\n\n" + _POLICY_TEXT
        )
        task = {
            "task_id": task_id, "task_type": "taubench",
            "prompt": prompt, "split": self.split_of(idx), "facts": facts,
        }
        rule = _decision_rule(facts)
        gold = GoldLabels(success=None, correct_final_output=facts["gold_decision"])
        return BenchmarkExample(
            task_id=task_id, dataset=self.name, profile=profile, task=task,
            trajectory=Trajectory(task_id=task_id, steps=[], final_output=None),
            dag=AssumptionDAG(task_id=task_id, nodes=[], edges=[]),
            gold=gold, rules=[rule], split=self.split_of(idx),
        )


__all__ = ["TIERS", "REQUEST_TYPES", "TauBenchRecon"]
