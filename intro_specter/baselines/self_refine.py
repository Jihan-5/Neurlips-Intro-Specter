"""Self-Refine baseline (Madaan et al. 2023).

One critique-and-revise pass over the entire trajectory. No backward attribution,
no graph structure, no selective repair — this is the head-to-head comparison the
draft paper claims a 44% reduction over.
"""

from __future__ import annotations

from typing import Any

from ..models import ChatProvider
from ..prompts import SELF_REFINE_CRITIQUE_SYSTEM, self_refine_user
from ..schemas import Trajectory, TrajectoryStep, UserProfile
from ..verifier import HybridVerifier
from .base import BaselineResult, register


def run_self_refine(
    *,
    profile: UserProfile,
    task: dict[str, Any],
    trajectory: Trajectory,
    verifier: HybridVerifier,
    provider: ChatProvider | None = None,
    model: str = "",
    n_rounds: int = 1,
    temperature: float = 0.0,
    seed: int | None = None,
    **_: Any,
) -> BaselineResult:
    if provider is None or not model:
        # No-LLM fallback: behave like Direct so the baseline can still be run in
        # the dry-run and still produce a verifier signal.
        result, _ = verifier.check(
            profile=profile, task=task, trajectory=trajectory, final_output=trajectory.final_output
        )
        return BaselineResult(method="self_refine", final_trajectory=trajectory, verifier=result)

    tokens_in = 0
    tokens_out = 0
    cur = trajectory
    last_meta: dict[str, Any] = {}
    for r in range(n_rounds):
        payload, completion = provider.complete_json(
            system=SELF_REFINE_CRITIQUE_SYSTEM,
            user=self_refine_user(
                profile=profile.model_dump(mode="json"),
                task=task,
                trajectory=cur.model_dump(mode="json"),
            ),
            model=model,
            temperature=temperature,
            seed=seed,
        )
        tokens_in += completion.tokens_input
        tokens_out += completion.tokens_output
        revised_steps = [
            TrajectoryStep.model_validate(s) for s in payload.get("revised_steps", [])
        ]
        cur = Trajectory(
            task_id=cur.task_id,
            steps=revised_steps or cur.steps,
            final_output=payload.get("final_output", cur.final_output),
        )
        last_meta = {"round": r, "critique": payload.get("critique", "")}
        verdict, _ = verifier.check(
            profile=profile, task=task, trajectory=cur, final_output=cur.final_output
        )
        if verdict.passed:
            break

    final_verdict, _ = verifier.check(
        profile=profile, task=task, trajectory=cur, final_output=cur.final_output
    )
    return BaselineResult(
        method="self_refine",
        final_trajectory=cur,
        verifier=final_verdict,
        tokens_input=tokens_in,
        tokens_output=tokens_out,
        meta=last_meta,
    )


register("self_refine", run_self_refine)
