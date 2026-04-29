"""Layer 1: build the Assumption-DAG.

Two paths:

* ``llm``: call a `ChatProvider` with the assumption-extraction prompt and parse the
  returned JSON into an `AssumptionDAG`. Cycles are broken by removing the lowest-
  confidence edge (per the plan PDF code-generation prompt).
* ``passthrough``: use a DAG that the benchmark already supplies (synthetic DAGs and
  fault-injected naturalistic tasks).

Open-weight LLMs adhere to enum values inconsistently — Llama, in particular,
will invent novel `provenance` strings. We normalize the JSON payload before
pydantic validation so the run survives without lossy retry loops.
"""

from __future__ import annotations

from typing import Any

from .dag import remove_cycles
from .models import ChatProvider
from .prompts import ASSUMPTION_EXTRACTION_SYSTEM, assumption_extraction_user
from .schemas import AssumptionDAG, EdgeType, Provenance, Trajectory, UserProfile

# ---------------------------------------------------------------------------
# Tolerant JSON normalization
# ---------------------------------------------------------------------------

_PROVENANCE_ALIASES: dict[str, Provenance] = {
    "profile": Provenance.PROFILE,
    "user_profile": Provenance.PROFILE,
    "tool": Provenance.TOOL,
    "tool_output": Provenance.TOOL,
    "tool_observation": Provenance.TOOL,
    "external": Provenance.EXTERNAL_EVIDENCE,
    "external_evidence": Provenance.EXTERNAL_EVIDENCE,
    "evidence": Provenance.EXTERNAL_EVIDENCE,
    "model_inferred": Provenance.MODEL_INFERRED,
    "inferred": Provenance.MODEL_INFERRED,
    "model": Provenance.MODEL_INFERRED,
    "world": Provenance.WORLD_KNOWLEDGE,
    "world_knowledge": Provenance.WORLD_KNOWLEDGE,
}

_EDGE_TYPE_ALIASES: dict[str, EdgeType] = {
    "supports": EdgeType.SUPPORTS,
    "support": EdgeType.SUPPORTS,
    "depends": EdgeType.DEPENDS_ON,
    "depends_on": EdgeType.DEPENDS_ON,
    "dependency": EdgeType.DEPENDS_ON,
    "contradicts": EdgeType.CONTRADICTS,
    "contradict": EdgeType.CONTRADICTS,
    "downstream": EdgeType.DOWNSTREAM_OF,
    "downstream_of": EdgeType.DOWNSTREAM_OF,
}


def _coerce_provenance(value: Any) -> str:
    if value is None:
        return Provenance.MODEL_INFERRED.value
    s = str(value).strip().lower().replace(" ", "_").replace("-", "_")
    return _PROVENANCE_ALIASES.get(s, Provenance.MODEL_INFERRED).value


def _coerce_edge_type(value: Any) -> str:
    if value is None:
        return EdgeType.SUPPORTS.value
    s = str(value).strip().lower().replace(" ", "_").replace("-", "_")
    return _EDGE_TYPE_ALIASES.get(s, EdgeType.SUPPORTS).value


def _coerce_confidence(value: Any) -> float:
    try:
        c = float(value)
    except (TypeError, ValueError):
        return 0.5
    return max(0.0, min(1.0, c))


def _normalize_dag_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Run before `AssumptionDAG.model_validate`. Maps fuzzy LLM enum strings
    back into the schema's strict enum values. Drops malformed nodes silently
    rather than crashing the whole run."""
    raw_final = payload.get("final_decision_node")
    if isinstance(raw_final, dict):
        # Llama 3.1 8B sometimes embeds the node object instead of just its id.
        raw_final = raw_final.get("id") or raw_final.get("node_id")
    final_str = str(raw_final) if raw_final is not None else None
    out: dict[str, Any] = {
        "task_id": payload.get("task_id", "unknown"),
        "final_decision_node": final_str,
    }
    nodes_in = payload.get("nodes") or []
    edges_in = payload.get("edges") or []
    seen_ids: set[str] = set()
    nodes_out: list[dict[str, Any]] = []
    for raw in nodes_in:
        if not isinstance(raw, dict) or "id" not in raw:
            continue
        nid = str(raw["id"])
        if nid in seen_ids:
            continue
        seen_ids.add(nid)
        try:
            step_id = int(raw.get("step_id", 0))
        except (TypeError, ValueError):
            step_id = 0
        nodes_out.append({
            "id": nid,
            "step_id": step_id,
            "assumption": str(raw.get("assumption", "")),
            "provenance": _coerce_provenance(raw.get("provenance")),
            "profile_span_ids": list(raw.get("profile_span_ids", []) or []),
            "confidence": _coerce_confidence(raw.get("confidence", 0.5)),
            "depends_on": [str(x) for x in (raw.get("depends_on") or []) if x in seen_ids or True],
            "status": str(raw.get("status", "active")),
        })
    out["nodes"] = nodes_out

    valid_ids = {n["id"] for n in nodes_out}
    edges_out: list[dict[str, Any]] = []
    for raw in edges_in:
        if not isinstance(raw, dict):
            continue
        s, t = raw.get("source"), raw.get("target")
        if s not in valid_ids or t not in valid_ids:
            continue
        edges_out.append({"source": s, "target": t, "type": _coerce_edge_type(raw.get("type"))})
    out["edges"] = edges_out

    if out.get("final_decision_node") and out["final_decision_node"] not in valid_ids:
        out["final_decision_node"] = nodes_out[-1]["id"] if nodes_out else None

    return out


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
    normalized = _normalize_dag_payload(payload)
    raw_dag = AssumptionDAG.model_validate(normalized)
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
