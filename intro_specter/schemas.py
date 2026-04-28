"""Pydantic schemas for Intro-Specter.

These mirror the Assumption-DAG schema and verifier output format defined in the
review-and-experiment-plan PDF (Phase 3, "Assumption-DAG Schema" and the verifier
prompt). Field names are kept identical so the same JSON can flow between LLM
prompts, persisted JSONL records, and Python code without translation.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Provenance(str, Enum):
    PROFILE = "profile"
    TOOL = "tool"
    EXTERNAL_EVIDENCE = "external_evidence"
    MODEL_INFERRED = "model_inferred"
    WORLD_KNOWLEDGE = "world_knowledge"


class EdgeType(str, Enum):
    SUPPORTS = "supports"
    DEPENDS_ON = "depends_on"
    CONTRADICTS = "contradicts"
    DOWNSTREAM_OF = "downstream_of"


class NodeStatus(str, Enum):
    ACTIVE = "active"
    REPLACED = "replaced"
    REMOVED = "removed"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class StepKind(str, Enum):
    OBSERVATION = "observation"
    ASSUMPTION = "assumption"
    ACTION = "action"
    TOOL_CALL = "tool_call"
    OUTPUT = "output"


class ProfileSpan(BaseModel):
    """A single addressable fact in the user profile."""

    model_config = ConfigDict(extra="forbid")

    id: str
    text: str
    kind: Literal["constraint", "preference", "history", "fact"] = "fact"
    is_hard: bool = False
    contradicts: list[str] = Field(default_factory=list)


class UserProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str
    spans: list[ProfileSpan]

    def get(self, span_id: str) -> ProfileSpan | None:
        for s in self.spans:
            if s.id == span_id:
                return s
        return None


class TrajectoryStep(BaseModel):
    """One observable step in an agent trajectory.

    The PDF's Method Requirements section explicitly forbids hidden chain-of-thought:
    only structured `reason_summary`, action rationales, assumption statements, and
    tool outputs are stored.
    """

    model_config = ConfigDict(extra="forbid")

    step_id: int
    kind: StepKind
    text: str
    reason_summary: str | None = None
    tool_name: str | None = None
    tool_input: dict[str, Any] | None = None
    tool_output: str | None = None


class Trajectory(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    steps: list[TrajectoryStep]
    final_output: str | None = None


# ---------------------------------------------------------------------------
# Tolerant parsing helpers — used everywhere we read LLM-produced JSON into
# pydantic. Open-weight models (Llama, Qwen, DeepSeek) sometimes invent enum
# values (e.g., kind="translation") or send wrong types (e.g., tool_input as
# a bare string). Rather than crash a 4-hour headline run, we coerce.
# ---------------------------------------------------------------------------

_VALID_STEP_KINDS = {k.value for k in StepKind}


def coerce_trajectory_step(raw: Any) -> TrajectoryStep:
    """Best-effort conversion of a possibly-malformed LLM step dict into a
    valid TrajectoryStep. Falls back to ``OUTPUT`` kind and stringifies any
    non-dict tool_input rather than raising."""
    if not isinstance(raw, dict):
        return TrajectoryStep(step_id=0, kind=StepKind.OUTPUT, text=str(raw))
    try:
        step_id = int(raw.get("step_id", 0))
    except (TypeError, ValueError):
        step_id = 0
    kind_str = str(raw.get("kind", "output")).strip().lower().replace("-", "_")
    if kind_str not in _VALID_STEP_KINDS:
        kind_str = StepKind.OUTPUT.value
    text = str(raw.get("text", "") or "")
    reason = raw.get("reason_summary")
    reason = str(reason) if reason is not None else None
    tool_name = raw.get("tool_name")
    tool_name = str(tool_name) if tool_name is not None else None
    tool_input = raw.get("tool_input")
    if tool_input is not None and not isinstance(tool_input, dict):
        tool_input = {"value": str(tool_input)}
    tool_output = raw.get("tool_output")
    tool_output = str(tool_output) if tool_output is not None else None
    return TrajectoryStep(
        step_id=step_id,
        kind=StepKind(kind_str),
        text=text,
        reason_summary=reason,
        tool_name=tool_name,
        tool_input=tool_input,
        tool_output=tool_output,
    )


def coerce_trajectory_steps(raw_steps: Any) -> list[TrajectoryStep]:
    if not isinstance(raw_steps, list):
        return []
    out: list[TrajectoryStep] = []
    for r in raw_steps:
        try:
            out.append(coerce_trajectory_step(r))
        except Exception:
            continue
    return out


class AssumptionNode(BaseModel):
    """A claim the agent relies on, with provenance and confidence.

    Mirrors the JSON schema in Phase 3 of the plan PDF.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    step_id: int
    assumption: str
    provenance: Provenance
    profile_span_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    depends_on: list[str] = Field(default_factory=list)
    status: NodeStatus = NodeStatus.ACTIVE


class AssumptionEdge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: str
    target: str
    type: EdgeType = EdgeType.DEPENDS_ON


class AssumptionDAG(BaseModel):
    """Directed acyclic graph of assumptions with a single final decision node."""

    model_config = ConfigDict(extra="forbid")

    task_id: str
    nodes: list[AssumptionNode]
    edges: list[AssumptionEdge] = Field(default_factory=list)
    final_decision_node: str | None = None

    @model_validator(mode="after")
    def _validate_edges_reference_nodes(self) -> "AssumptionDAG":
        ids = {n.id for n in self.nodes}
        for e in self.edges:
            if e.source not in ids:
                raise ValueError(f"edge source {e.source!r} is not a known node")
            if e.target not in ids:
                raise ValueError(f"edge target {e.target!r} is not a known node")
        if self.final_decision_node is not None and self.final_decision_node not in ids:
            raise ValueError(f"final_decision_node {self.final_decision_node!r} is not a known node")
        return self


class ViolationEvent(BaseModel):
    """A detected mismatch between the trajectory and the user profile (or task)."""

    model_config = ConfigDict(extra="forbid")

    violation_id: str
    step_id: int
    violated_profile_span_id: str | None = None
    violated_constraint: str
    trajectory_text: str = ""
    severity: Severity = Severity.MEDIUM
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    explanation: str = ""


class VerifierResult(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    passed: bool = Field(alias="pass")
    violations: list[ViolationEvent] = Field(default_factory=list)

    @field_validator("violations")
    @classmethod
    def _violation_ids_unique(cls, v: list[ViolationEvent]) -> list[ViolationEvent]:
        seen: set[str] = set()
        for x in v:
            if x.violation_id in seen:
                raise ValueError(f"duplicate violation_id {x.violation_id!r}")
            seen.add(x.violation_id)
        return v


class CounterfactualRepair(BaseModel):
    model_config = ConfigDict(extra="forbid")

    repair_id: str
    new_assumption: str
    nodes_to_rerun: list[str]
    repair_instruction: str
    expected_violation_removed: bool
    risk_notes: str = ""


class CandidateScore(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_id: str
    prior: float
    likelihood: float
    cost: float
    posterior: float = 0.0


class AttributionPosterior(BaseModel):
    """Output of `posterior_update`."""

    model_config = ConfigDict(extra="forbid")

    candidates: list[CandidateScore]
    entropy: float
    top_k: list[str]

    def by_id(self, node_id: str) -> CandidateScore | None:
        for c in self.candidates:
            if c.node_id == node_id:
                return c
        return None


class RepairDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["accepted", "repaired", "abstain_or_full_regenerate"]
    fault_node: str | None = None
    posterior: AttributionPosterior | None = None
    expected_cost: float | None = None
    expected_utility: float | None = None
    explanation: str = ""


class Task(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    dataset: str
    profile: UserProfile
    prompt: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class GoldLabels(BaseModel):
    """Ground truth used for evaluation. All fields are optional because not every
    benchmark provides every label kind."""

    model_config = ConfigDict(extra="forbid")

    success: bool | None = None
    fault_node_id: str | None = None
    correct_final_output: str | None = None
    expected_violations: list[str] = Field(default_factory=list)


class TaskRecord(BaseModel):
    """A single benchmark example in the unified profile-grounded trajectory format
    described in the PDF's Dataset Construction section."""

    model_config = ConfigDict(extra="forbid")

    task: Task
    trajectory: Trajectory
    dag: AssumptionDAG | None = None
    verifier_signal: VerifierResult | None = None
    gold: GoldLabels = Field(default_factory=GoldLabels)


class RunResult(BaseModel):
    """One row of experiment output (one task × one method)."""

    model_config = ConfigDict(extra="forbid")

    task_id: str
    dataset: str
    method: str
    model: str
    seed: int
    success: bool
    constraint_satisfied: bool | None = None
    violation_rate: float | None = None
    profile_violation: bool | None = None
    repair_status: str | None = None
    fault_node_predicted: str | None = None
    posterior: list[CandidateScore] | None = None
    final_output: str | None = None
    tokens_input: int = 0
    tokens_output: int = 0
    tool_calls: int = 0
    latency_ms: float = 0.0
    extra: dict[str, Any] = Field(default_factory=dict)
