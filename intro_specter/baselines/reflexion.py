"""Reflexion baseline (Shinn et al. 2023).

Detect failure → generate verbal reflection → retry from scratch with reflection
in context. The plan PDF lists this as a primary baseline; the draft paper claims
a 31% reduction over it.
"""

from __future__ import annotations

from typing import Any

from ..models import ChatProvider
from ..prompts import (
    DIRECT_AGENT_SYSTEM,
    REFLEXION_REFLECT_SYSTEM,
    REFLEXION_RETRY_SYSTEM,
    direct_agent_user,
    reflexion_reflect_user,
    reflexion_retry_user,
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


def run_reflexion(
    *,
    profile: UserProfile,
    task: dict[str, Any],
    trajectory: Trajectory,
    verifier: HybridVerifier,
    provider: ChatProvider | None = None,
    model: str = "",
    max_trials: int = 2,
    temperature: float = 0.7,
    seed: int | None = None,
    **_: Any,
) -> BaselineResult:
    if provider is None or not model:
        result, _ = verifier.check(
            profile=profile, task=task, trajectory=trajectory, final_output=trajectory.final_output
        )
        return BaselineResult(method="reflexion", final_trajectory=trajectory, verifier=result)

    tokens_in = 0
    tokens_out = 0
    attempts: list[Trajectory] = [trajectory]
    reflections: list[str] = []
    cur = trajectory

    for trial in range(max_trials):
        verdict, _ = verifier.check(
            profile=profile, task=task, trajectory=cur, final_output=cur.final_output
        )
        if verdict.passed:
            return BaselineResult(
                method="reflexion",
                final_trajectory=cur,
                verifier=verdict,
                tokens_input=tokens_in,
                tokens_output=tokens_out,
                meta={"trials": trial + 1, "reflections": reflections},
            )

        # Reflect on the failure.
        failure_text = "; ".join(
            f"step {v.step_id}: {v.violated_constraint} ({v.explanation})"
            for v in verdict.violations
        ) or "verification failed"
        ref_payload, ref_completion = provider.complete_json(
            system=REFLEXION_REFLECT_SYSTEM,
            user=reflexion_reflect_user(
                profile=profile.model_dump(mode="json"),
                task=task,
                trajectory=cur.model_dump(mode="json"),
                failure_text=failure_text,
            ),
            model=model,
            temperature=temperature,
            seed=seed,
        )
        tokens_in += ref_completion.tokens_input
        tokens_out += ref_completion.tokens_output
        reflections.append(ref_payload.get("reflection", ""))

        # Retry with reflections in context.
        try:
            retry_payload, retry_completion = provider.complete_json(
                system=REFLEXION_RETRY_SYSTEM,
                user=reflexion_retry_user(
                    profile=profile.model_dump(mode="json"),
                    task=task,
                    prior_attempts=[t.model_dump(mode="json") for t in attempts],
                    reflections=reflections,
                ),
                model=model,
                temperature=temperature,
                seed=seed,
            )
            tokens_in += retry_completion.tokens_input
            tokens_out += retry_completion.tokens_output
            cur = _trajectory_from_payload(retry_payload, task_id=trajectory.task_id)
        except Exception:  # pragma: no cover - fall back to direct prompt
            retry_payload, retry_completion = provider.complete_json(
                system=DIRECT_AGENT_SYSTEM,
                user=direct_agent_user(profile=profile.model_dump(mode="json"), task=task),
                model=model,
                temperature=temperature,
                seed=seed,
            )
            tokens_in += retry_completion.tokens_input
            tokens_out += retry_completion.tokens_output
            cur = _trajectory_from_payload(retry_payload, task_id=trajectory.task_id)
        attempts.append(cur)

    final_verdict, _ = verifier.check(
        profile=profile, task=task, trajectory=cur, final_output=cur.final_output
    )
    return BaselineResult(
        method="reflexion",
        final_trajectory=cur,
        verifier=final_verdict,
        tokens_input=tokens_in,
        tokens_output=tokens_out,
        meta={"trials": max_trials, "reflections": reflections},
    )


register("reflexion", run_reflexion)
