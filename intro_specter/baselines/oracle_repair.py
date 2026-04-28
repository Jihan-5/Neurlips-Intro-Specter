"""Oracle-fault-node baseline.

Upper-bounds Intro-Specter's repair component if attribution were perfect.
The plan PDF specifically lists "Oracle fault node — Upper-bounds repair if
attribution is perfect" as a baseline.

Given a gold ``fault_node_id``, run the same downstream-rerun procedure as
Intro-Specter would after attribution. Token cost reflects only the repair
stage (not the attribution stage).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..repair import rerun_downstream_subgraph_callable
from ..schemas import AssumptionDAG, AssumptionNode, Trajectory, TrajectoryStep, UserProfile
from ..verifier import HybridVerifier
from .base import BaselineResult, register


def run_oracle_repair(
    *,
    profile: UserProfile,
    task: dict[str, Any],
    trajectory: Trajectory,
    verifier: HybridVerifier,
    dag: AssumptionDAG,
    fault_node_id: str,
    rerun_fn: Callable[
        [list[TrajectoryStep], AssumptionNode, AssumptionDAG], tuple[list[TrajectoryStep], str | None]
    ],
    **_: Any,
) -> BaselineResult:
    new_traj = rerun_downstream_subgraph_callable(
        trajectory=trajectory,
        dag=dag,
        fault_node_id=fault_node_id,
        rerun_fn=rerun_fn,
    )
    verdict, _ = verifier.check(
        profile=profile, task=task, trajectory=new_traj, final_output=new_traj.final_output
    )
    return BaselineResult(
        method="oracle_repair",
        final_trajectory=new_traj,
        verifier=verdict,
        meta={"fault_node_id": fault_node_id},
    )


register("oracle_repair", run_oracle_repair)
