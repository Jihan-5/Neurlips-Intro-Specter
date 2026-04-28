"""Full-regeneration baseline: regenerate the entire trajectory from scratch.

Exists primarily as a token-cost reference: the headline efficiency claim in the
plan PDF (and the user's draft) is that selective repair costs ~62% fewer tokens
than re-running the whole trajectory.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..schemas import Trajectory, UserProfile
from ..verifier import HybridVerifier
from .base import BaselineResult, register


def run_full_regen(
    *,
    profile: UserProfile,
    task: dict[str, Any],
    trajectory: Trajectory,
    verifier: HybridVerifier,
    regenerate_fn: Callable[[UserProfile, dict[str, Any]], tuple[Trajectory, int, int]] | None = None,
    max_attempts: int = 3,
    **_: Any,
) -> BaselineResult:
    """``regenerate_fn(profile, task) -> (trajectory, tokens_in, tokens_out)`` is
    benchmark-specific. For the synthetic benchmark it is a deterministic Python
    callable that produces a fresh trajectory; for natural benchmarks it wraps
    `direct_agent_user`."""
    if regenerate_fn is None:
        result, meta = verifier.check(
            profile=profile, task=task, trajectory=trajectory, final_output=trajectory.final_output
        )
        return BaselineResult(
            method="full_regen",
            final_trajectory=trajectory,
            verifier=result,
            meta={"note": "no regenerate_fn provided; passthrough", "verifier": meta},
        )

    tokens_in = 0
    tokens_out = 0
    attempt_traj = trajectory
    last_verifier = None
    for i in range(max_attempts):
        attempt_traj, ti, to = regenerate_fn(profile, task)
        tokens_in += ti
        tokens_out += to
        last_verifier, _ = verifier.check(
            profile=profile,
            task=task,
            trajectory=attempt_traj,
            final_output=attempt_traj.final_output,
        )
        if last_verifier.passed:
            break
    return BaselineResult(
        method="full_regen",
        final_trajectory=attempt_traj,
        verifier=last_verifier,  # type: ignore[arg-type]
        tokens_input=tokens_in,
        tokens_output=tokens_out,
        meta={"attempts": i + 1},
    )


register("full_regen", run_full_regen)
