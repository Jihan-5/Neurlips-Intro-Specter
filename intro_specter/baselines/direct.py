"""Direct baseline: pass the agent's initial trajectory through the verifier with
no correction applied. Establishes the floor performance."""

from __future__ import annotations

from typing import Any

from ..schemas import Trajectory, UserProfile
from ..verifier import HybridVerifier
from .base import BaselineResult, register


def run_direct(
    *,
    profile: UserProfile,
    task: dict[str, Any],
    trajectory: Trajectory,
    verifier: HybridVerifier,
    **_: Any,
) -> BaselineResult:
    result, meta = verifier.check(
        profile=profile, task=task, trajectory=trajectory, final_output=trajectory.final_output
    )
    return BaselineResult(
        method="direct",
        final_trajectory=trajectory,
        verifier=result,
        meta={"verifier": meta},
    )


register("direct", run_direct)
