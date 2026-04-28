"""Layer 1: build the Assumption-DAG.

Two paths:

* ``llm``: call a `ChatProvider` with the assumption-extraction prompt and parse the
  returned JSON into an `AssumptionDAG`. Cycles are broken by removing the lowest-
  confidence edge (per the plan PDF code-generation prompt).
* ``passthrough``: use a DAG that the benchmark already supplies (synthetic DAGs and
  fault-injected naturalistic tasks).
"""

from __future__ import annotations

from typing import Any

from .dag import remove_cycles
from .models import ChatProvider
from .prompts import ASSUMPTION_EXTRACTION_SYSTEM, assumption_extraction_user
from .schemas import AssumptionDAG, Trajectory, UserProfile


def build_assumption_dag(
    *,
    profile: UserProfile,
    task: dict[str, Any],
    trajectory: Trajectory,
    provider: ChatProvider,
    model: str,
    temperature: float = 0.0,
    seed: int | None = None,
) -> tuple[AssumptionDAG, dict[str, Any]]:
    """LLM-based extraction. Returns the cleaned DAG and a metadata dict (raw JSON,
    cycles removed, token counts).
    """
    user = assumption_extraction_user(
        profile=profile.model_dump(mode="json"),
        task=task,
        trajectory=trajectory.model_dump(mode="json"),
    )
    payload, completion = provider.complete_json(
        system=ASSUMPTION_EXTRACTION_SYSTEM,
        user=user,
        model=model,
        temperature=temperature,
        seed=seed,
    )
    payload.setdefault("task_id", trajectory.task_id)
    raw_dag = AssumptionDAG.model_validate(payload)
    cleaned, removed = remove_cycles(raw_dag)
    meta = {
        "tokens_input": completion.tokens_input,
        "tokens_output": completion.tokens_output,
        "latency_ms": completion.latency_ms,
        "cycles_removed": [(e.source, e.target) for e in removed],
        "raw": payload,
    }
    return cleaned, meta


def passthrough_dag(dag: AssumptionDAG) -> tuple[AssumptionDAG, dict[str, Any]]:
    """Use the gold DAG that the benchmark provides. Verifies it is acyclic."""
    cleaned, removed = remove_cycles(dag)
    return cleaned, {"cycles_removed": [(e.source, e.target) for e in removed]}
