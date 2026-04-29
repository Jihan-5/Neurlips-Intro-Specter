"""ReAct baseline (Yao et al. 2023).

Interleaves Thought → Action → Observation up to `max_steps` times, then emits
a final answer. Unlike Direct (single forward pass) and Self-Refine (critique
on a completed trajectory), ReAct generates each reasoning step conditional
on prior steps' observations.

Adaptation note: most of our benchmarks don't provide a tool/environment,
so Observations are self-generated reflections on Actions — matching the
original ReAct framing for non-tool-augmented reasoning tasks.
"""

from __future__ import annotations

from typing import Any

from ..models import ChatProvider
from ..prompts import REACT_SYSTEM, react_user
from ..schemas import Trajectory, UserProfile, coerce_final_output, coerce_trajectory_steps
from ..verifier import HybridVerifier
from .base import BaselineResult, register


def run_react(
    *,
    profile: UserProfile,
    task: dict[str, Any],
    trajectory: Trajectory,
    verifier: HybridVerifier,
    provider: ChatProvider | None = None,
    model: str = "",
    temperature: float = 0.0,
    seed: int | None = None,
    max_steps: int = 4,
    **_: Any,
) -> BaselineResult:
    if provider is None or not model:
        # No-LLM fallback: behave like Direct.
        result, _ = verifier.check(
            profile=profile, task=task, trajectory=trajectory, final_output=trajectory.final_output
        )
        return BaselineResult(method="react", final_trajectory=trajectory, verifier=result)

    payload, completion = provider.complete_json(
        system=REACT_SYSTEM,
        user=react_user(
            profile=profile.model_dump(mode="json"),
            task=task,
            max_steps=max_steps,
        ),
        model=model,
        temperature=temperature,
        seed=seed,
        max_tokens=8192,
    )
    steps = coerce_trajectory_steps(payload.get("steps", []))
    final = coerce_final_output(payload.get("final_output"), fallback=trajectory.final_output) or ""
    new_traj = Trajectory(
        task_id=trajectory.task_id,
        steps=steps or trajectory.steps,
        final_output=final or trajectory.final_output,
    )
    final_verdict, _ = verifier.check(
        profile=profile, task=task, trajectory=new_traj, final_output=new_traj.final_output
    )
    return BaselineResult(
        method="react",
        final_trajectory=new_traj,
        verifier=final_verdict,
        tokens_input=completion.tokens_input,
        tokens_output=completion.tokens_output,
        meta={
            "n_thoughts": len(payload.get("thoughts", []) or []),
            "max_steps": max_steps,
        },
    )


register("react", run_react)
