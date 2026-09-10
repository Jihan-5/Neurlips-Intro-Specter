"""Violation-aware reprompt baseline.

Tests the natural ablation question: is the Assumption-DAG necessary, or does
simply feeding the violated profile span back into a re-prompt achieve the
same lift? This baseline detects a profile violation, formats the violated
constraint(s) as explicit feedback, and re-prompts the agent with that feedback
to produce a single revised trajectory.

Distinguishing factors vs. existing baselines:
- vs. Self-Refine: Self-Refine generates an LLM critique of the output before
  revising. This baseline injects the *verifier's* concrete violated profile
  span(s) directly, with no critique step.
- vs. Reflexion: Reflexion generates a free-form verbal reflection over the
  trajectory before retrying. This baseline skips the reflection step.
- vs. Intro-Specter: no DAG construction, no attribution, no provenance
  weighting, no selective subgraph repair. The whole trajectory is regenerated
  with the violated-span feedback in context.

If this baseline matches Intro-Specter, structured attribution is unnecessary.
If Intro-Specter strictly outperforms it, the lift is attributable to typed
attribution + selective repair, not just to feeding violation evidence back.
"""

from __future__ import annotations

from typing import Any

from ..models import ChatProvider
from ..prompts import (
    DIRECT_AGENT_SYSTEM,
    direct_agent_user,
)
from ..schemas import Trajectory, UserProfile, coerce_final_output, coerce_trajectory_steps
from ..verifier import HybridVerifier
from .base import BaselineResult, register


def _trajectory_from_payload(payload: dict[str, Any], task_id: str) -> Trajectory:
    steps = coerce_trajectory_steps(payload.get("steps", []))
    return Trajectory(
        task_id=task_id,
        steps=steps,
        final_output=coerce_final_output(payload.get("final_output")),
    )


VIOLATION_REPROMPT_SYSTEM = (
    "You are an agent that previously produced an output that violated explicit user-profile "
    "constraints. You will be shown the user profile, the original task, your previous output, "
    "and the specific violated profile span(s). Produce a revised response that satisfies all "
    "constraints. Return JSON with keys 'steps' and 'final_output' as in the original schema."
)


def _format_violation_feedback(violations) -> str:
    if not violations:
        return ""
    lines = []
    for v in violations:
        lines.append(
            f"- Violated constraint: {getattr(v, 'violated_constraint', '<unknown>')} "
            f"(at step {getattr(v, 'step_id', '?')})"
        )
        explanation = getattr(v, 'explanation', '')
        if explanation:
            lines.append(f"  Explanation: {explanation}")
    return "\n".join(lines)


def violation_reprompt_user(
    *,
    profile: dict[str, Any],
    task: dict[str, Any],
    prior_trajectory: dict[str, Any],
    violation_feedback: str,
) -> str:
    profile_str = "\n".join(f"- [{s['kind']}] {s['text']}" for s in profile.get("spans", []))
    return (
        f"USER PROFILE:\n{profile_str}\n\n"
        f"TASK: {task.get('prompt', task)}\n\n"
        f"PREVIOUS OUTPUT (which violated constraints):\n"
        f"{prior_trajectory.get('final_output', '')}\n\n"
        f"VIOLATED PROFILE SPANS:\n{violation_feedback}\n\n"
        f"Please produce a revised response that satisfies ALL the violated constraints "
        f"above. Return JSON with keys 'steps' (list) and 'final_output' (string)."
    )


def run_violation_reprompt(
    *,
    profile: UserProfile,
    task: dict[str, Any],
    trajectory: Trajectory,
    verifier: HybridVerifier,
    provider: ChatProvider | None = None,
    model: str = "",
    max_trials: int = 1,
    temperature: float = 0.7,
    seed: int | None = None,
    **_: Any,
) -> BaselineResult:
    """Detect violation, feed the violated profile span back into a re-prompt, accept the revision.

    `max_trials` controls how many revision rounds are attempted (each round re-verifies and
    re-prompts if a violation persists). Default 1 (single revision) to keep cost ~ Self-Refine.
    """
    if provider is None or not model:
        result, _ = verifier.check(
            profile=profile, task=task, trajectory=trajectory, final_output=trajectory.final_output
        )
        return BaselineResult(method="violation_reprompt", final_trajectory=trajectory, verifier=result)

    tokens_in = 0
    tokens_out = 0
    cur = trajectory
    n_trials = 0

    for _ in range(max_trials):
        verdict, _ = verifier.check(
            profile=profile, task=task, trajectory=cur, final_output=cur.final_output
        )
        if verdict.passed:
            return BaselineResult(
                method="violation_reprompt",
                final_trajectory=cur,
                verifier=verdict,
                tokens_input=tokens_in,
                tokens_output=tokens_out,
                meta={"trials": n_trials},
            )

        feedback = _format_violation_feedback(verdict.violations)
        try:
            payload, completion = provider.complete_json(
                system=VIOLATION_REPROMPT_SYSTEM,
                user=violation_reprompt_user(
                    profile=profile.model_dump(mode="json"),
                    task=task,
                    prior_trajectory=cur.model_dump(mode="json"),
                    violation_feedback=feedback,
                ),
                model=model,
                temperature=temperature,
                seed=seed,
            )
            tokens_in += completion.tokens_input
            tokens_out += completion.tokens_output
            cur = _trajectory_from_payload(payload, task_id=trajectory.task_id)
        except Exception:
            payload, completion = provider.complete_json(
                system=DIRECT_AGENT_SYSTEM,
                user=direct_agent_user(profile=profile.model_dump(mode="json"), task=task),
                model=model,
                temperature=temperature,
                seed=seed,
            )
            tokens_in += completion.tokens_input
            tokens_out += completion.tokens_output
            cur = _trajectory_from_payload(payload, task_id=trajectory.task_id)
        n_trials += 1

    final_verdict, _ = verifier.check(
        profile=profile, task=task, trajectory=cur, final_output=cur.final_output
    )
    return BaselineResult(
        method="violation_reprompt",
        final_trajectory=cur,
        verifier=final_verdict,
        tokens_input=tokens_in,
        tokens_output=tokens_out,
        meta={"trials": n_trials},
    )


register("violation_reprompt", run_violation_reprompt)
