"""Prompts used by Intro-Specter, transcribed verbatim from the plan PDF.

Each prompt is a callable that accepts the structured inputs and returns a
single string. Keeping them in one module makes prompt-version tracking and
A/B-comparison easier downstream.
"""

from __future__ import annotations

import json
from typing import Any


def _dump(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2, default=str)


# ---------------------------------------------------------------------------
# 1. Assumption extraction (Phase 3 §"Prompt for Assumption Extraction")
# ---------------------------------------------------------------------------

ASSUMPTION_EXTRACTION_SYSTEM = """\
You are extracting explicit assumptions from an agent trajectory for evaluation.

Inputs:
- User profile JSON
- Task
- Agent trajectory with steps, actions, observations, and final output

Return JSON only with:
- nodes: assumption nodes used by the agent
- edges: dependencies among assumptions
- final_decision_node: the node most directly supporting the final output

For each node, include:
- id (string, e.g. "a0", "a1", ...)
- step_id (integer, matches a trajectory step_id)
- assumption: one sentence
- provenance: one of profile, tool, external_evidence, model_inferred, world_knowledge
- profile_span_ids: list of profile evidence spans, or empty list
- confidence: number from 0 to 1
- depends_on: list of node ids

For each edge, include:
- source: assumption id
- target: assumption id
- type: one of supports, depends_on, contradicts, downstream_of

Do not include hidden chain-of-thought. Use concise observable reasoning summaries only.
Output a single valid JSON object and nothing else.
"""


def assumption_extraction_user(profile: dict, task: dict, trajectory: dict) -> str:
    return (
        "PROFILE:\n"
        + _dump(profile)
        + "\n\nTASK:\n"
        + _dump(task)
        + "\n\nTRAJECTORY:\n"
        + _dump(trajectory)
    )


# ---------------------------------------------------------------------------
# 2. Profile-grounded verification
# ---------------------------------------------------------------------------

VERIFIER_SYSTEM = """\
You are a profile-grounded verifier.

Inputs:
- User profile JSON with span ids
- Task
- Agent trajectory
- Final output

Return JSON only:
{
  "pass": true or false,
  "violations": [
    {
      "violation_id": "v1",
      "step_id": integer,
      "violated_profile_span_id": "p3",
      "violated_constraint": "string",
      "trajectory_text": "string",
      "severity": "low|medium|high",
      "confidence": number from 0 to 1,
      "explanation": "one sentence"
    }
  ]
}

A violation exists if the trajectory or final output contradicts an explicit profile
fact, depends on an unsupported inferred user property, or allows irrelevant profile
context to distort a factual answer.

Output a single valid JSON object and nothing else.
"""


def verifier_user(profile: dict, task: dict, trajectory: dict, final_output: str | None) -> str:
    return (
        "PROFILE:\n"
        + _dump(profile)
        + "\n\nTASK:\n"
        + _dump(task)
        + "\n\nTRAJECTORY:\n"
        + _dump(trajectory)
        + "\n\nFINAL_OUTPUT:\n"
        + (final_output or "")
    )


# ---------------------------------------------------------------------------
# 3. Counterfactual repair generation
# ---------------------------------------------------------------------------

COUNTERFACTUAL_SYSTEM = """\
You are testing whether an assumption is the root cause of a profile-grounded error.

Inputs:
- User profile JSON
- Task
- Current Assumption-DAG
- Candidate faulty node
- Original trajectory
- Detected violation

Generate 3 counterfactual repairs that minimally change the candidate node while preserving
upstream assumptions. Each repair should describe what the new assumption is, which downstream
nodes need to be re-run, and whether the violation is expected to be removed.

Return JSON only:
{
  "candidate_node_id": "a4",
  "repairs": [
    {
      "repair_id": "r1",
      "new_assumption": "string",
      "nodes_to_rerun": ["a4", "a5", "a6"],
      "repair_instruction": "string",
      "expected_violation_removed": true,
      "risk_notes": "string"
    }
  ]
}

Output a single valid JSON object and nothing else.
"""


def counterfactual_user(
    profile: dict,
    task: dict,
    dag: dict,
    candidate_node: dict,
    trajectory: dict,
    violation: dict,
) -> str:
    return (
        "PROFILE:\n"
        + _dump(profile)
        + "\n\nTASK:\n"
        + _dump(task)
        + "\n\nDAG:\n"
        + _dump(dag)
        + "\n\nCANDIDATE_NODE:\n"
        + _dump(candidate_node)
        + "\n\nTRAJECTORY:\n"
        + _dump(trajectory)
        + "\n\nVIOLATION:\n"
        + _dump(violation)
    )


# ---------------------------------------------------------------------------
# 4. Re-execution of the downstream subgraph
# ---------------------------------------------------------------------------

REEXECUTION_SYSTEM = """\
You are repairing only the downstream part of an agent trajectory.

Inputs:
- User profile JSON
- Task
- Original valid prefix steps
- Repaired assumption node
- Downstream nodes to regenerate
- Tool observations available so far

Regenerate the downstream trajectory from the repaired assumption onward.

Constraints:
- Preserve all valid prefix steps.
- Do not invent new user preferences.
- If a profile fact is missing, mark it unknown instead of assuming it.
- Use available tool observations exactly as given.
- Return structured JSON with repaired steps and final output.

Return JSON only with the schema:
{
  "repaired_steps": [ { "step_id": int, "kind": "...", "text": "...", "reason_summary": "..." } ],
  "final_output": "string"
}

Output a single valid JSON object and nothing else.
"""


def reexecution_user(
    profile: dict,
    task: dict,
    valid_prefix: list[dict],
    repaired_node: dict,
    downstream_node_ids: list[str],
    tool_observations: list[dict],
) -> str:
    return (
        "PROFILE:\n"
        + _dump(profile)
        + "\n\nTASK:\n"
        + _dump(task)
        + "\n\nVALID_PREFIX:\n"
        + _dump(valid_prefix)
        + "\n\nREPAIRED_NODE:\n"
        + _dump(repaired_node)
        + "\n\nDOWNSTREAM_NODE_IDS:\n"
        + _dump(downstream_node_ids)
        + "\n\nTOOL_OBSERVATIONS:\n"
        + _dump(tool_observations)
    )


# ---------------------------------------------------------------------------
# 5. Initial trajectory generation (used for synthetic-natural tasks where the
# benchmark gives a profile and prompt but not a pre-rolled trajectory).
# ---------------------------------------------------------------------------

DIRECT_AGENT_SYSTEM = """\
You are a personal-agent that acts on behalf of a user. You are given a structured user
profile and a task. Produce a step-by-step trajectory that satisfies all hard constraints
in the profile and respects soft preferences where possible.

Output JSON only:
{
  "steps": [
    {"step_id": int, "kind": "observation|assumption|action|tool_call|output",
     "text": "string", "reason_summary": "string"}
  ],
  "final_output": "string"
}

Do not produce hidden chain-of-thought. Do not invent profile facts.
Output a single valid JSON object and nothing else.
"""


def direct_agent_user(profile: dict, task: dict) -> str:
    return "PROFILE:\n" + _dump(profile) + "\n\nTASK:\n" + _dump(task)


# ---------------------------------------------------------------------------
# 6. Self-Refine baseline (Madaan et al. 2023) — single-prompt critique+refine.
# ---------------------------------------------------------------------------

SELF_REFINE_CRITIQUE_SYSTEM = """\
You critique an agent trajectory against a user profile. List concrete problems with the
trajectory, especially any constraint violations or profile mismatches. Then propose a
revised trajectory that fixes those problems.

Output JSON only:
{
  "critique": "string",
  "revised_steps": [...same schema as the agent...],
  "final_output": "string"
}
"""


def self_refine_user(profile: dict, task: dict, trajectory: dict) -> str:
    return (
        "PROFILE:\n"
        + _dump(profile)
        + "\n\nTASK:\n"
        + _dump(task)
        + "\n\nORIGINAL_TRAJECTORY:\n"
        + _dump(trajectory)
    )


# ---------------------------------------------------------------------------
# 7. Reflexion baseline (Shinn et al. 2023) — verbal reflection on prior trial.
# ---------------------------------------------------------------------------

REFLEXION_REFLECT_SYSTEM = """\
You are a reflection module. You read a failed agent trajectory and a description of why it
failed, then write one short verbal lesson that could prevent the failure on a retry.

Output JSON only: {"reflection": "string"}
"""


REFLEXION_RETRY_SYSTEM = """\
You are an agent retrying a task. You have access to (1) the user profile, (2) the task,
(3) prior failed attempts and reflections. Produce a fresh trajectory that incorporates the
reflections.

Output JSON only with the same schema as the direct agent.
"""


def reflexion_reflect_user(
    profile: dict, task: dict, trajectory: dict, failure_text: str
) -> str:
    return (
        "PROFILE:\n"
        + _dump(profile)
        + "\n\nTASK:\n"
        + _dump(task)
        + "\n\nFAILED_TRAJECTORY:\n"
        + _dump(trajectory)
        + "\n\nFAILURE_REASON:\n"
        + failure_text
    )


def reflexion_retry_user(
    profile: dict, task: dict, prior_attempts: list[dict], reflections: list[str]
) -> str:
    return (
        "PROFILE:\n"
        + _dump(profile)
        + "\n\nTASK:\n"
        + _dump(task)
        + "\n\nPRIOR_ATTEMPTS:\n"
        + _dump(prior_attempts)
        + "\n\nREFLECTIONS:\n"
        + _dump(reflections)
    )


# ---------------------------------------------------------------------------
# 8. ReAct baseline (Yao et al. 2023). Explicit Thought→Action→Observation
# interleaving over a fixed maximum number of steps. Unlike Direct (which
# emits a flat trajectory in one pass) and Self-Refine (which critiques an
# already-completed trajectory), ReAct decomposes reasoning into discrete
# steps where each Action's Observation is conditioned on prior steps.
#
# Our adaptation: since most of the benchmark suite does not provide an
# external tool/environment, the ReAct loop runs entirely in-LLM —
# Action steps emit a string the model intends to "do" and the
# Observation is a self-generated reflection on the action's effect.
# This matches the original ReAct framing for non-tool reasoning tasks.
# ---------------------------------------------------------------------------

REACT_SYSTEM = """\
You are a ReAct-style agent solving a task for a user with a given profile.
Iterate Thought → Action → Observation up to MAX_STEPS times. Each step
must include all three. After enough steps, emit a Final Answer that
respects every hard profile constraint.

Output JSON only:
{
  "steps": [
    {"step_id": int, "kind": "observation|assumption|action|tool_call|output",
     "text": "string", "reason_summary": "string"}
  ],
  "thoughts": [{"step_id": int, "thought": "string", "action": "string",
                "observation": "string"}],
  "final_output": "string"
}

Do NOT skip the thoughts array — every iteration must record one entry there.
Do NOT invent profile facts. Output a single valid JSON object and nothing else.
"""


def react_user(profile: dict, task: dict, max_steps: int = 4) -> str:
    return (
        f"MAX_STEPS={max_steps}\n\nPROFILE:\n"
        + _dump(profile)
        + "\n\nTASK:\n"
        + _dump(task)
    )


# ---------------------------------------------------------------------------
# 9. Detection-only baseline (SelfCheckGPT / HaloScope-style). Uses the
# Intro-Specter LLM verifier to detect whether the trajectory has a
# profile-grounded violation. If a violation is detected, we *abstain* —
# return the trajectory unchanged and mark the trial as a detection-flag.
# This isolates the contribution of detection from the contribution of
# repair. Pairs with the IS results to show that detection alone is
# insufficient.
# ---------------------------------------------------------------------------

DETECTION_ONLY_SYSTEM = """\
You are a detector. Read the user profile and the agent trajectory.
Decide whether the trajectory contains a profile-grounded error
(a hard constraint violation, contradicted profile span, or assumption
unsupported by the profile). Return a JSON object only:

{
  "violation_present": true|false,
  "rationale": "string",
  "confidence": float in [0, 1]
}

Be conservative — only flag if a hard violation is clearly present.
Output a single valid JSON object and nothing else.
"""


def detection_only_user(profile: dict, task: dict, trajectory: dict, final_output: str | None) -> str:
    return (
        "PROFILE:\n"
        + _dump(profile)
        + "\n\nTASK:\n"
        + _dump(task)
        + "\n\nTRAJECTORY:\n"
        + _dump(trajectory)
        + "\n\nFINAL_OUTPUT:\n"
        + (final_output or "")
    )
