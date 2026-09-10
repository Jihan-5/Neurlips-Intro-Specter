"""Additive N-fault injector for the N=5/N=6 real multi-fault sweep, built on
top of a DIFFERENT structural resource than `double_fault_injection.py`.

Context / why this file exists
-------------------------------
The N=2/3/4 real sweep (`scripts/rebuttal_experiment_d_real.py` +
`intro_specter/profiles/double_fault_injection.py`) builds N faults as
1 context fault + (N-1) profile-constraint faults. That approach hits a hard
structural ceiling at N=4: `inject_profile` only samples 3-5 constraints per
example from 4 available mechanically-clean profile-fault types (english /
concise / bullets / preamble), and a direct 6000-draw simulation found 0
examples where all 4 co-occur. N=5 needs a genuinely different resource that
doesn't depend on profile-constraint count at all.

That resource exists in `xanhho/2WikiMultihopQA`'s `bridge_comparison`
question type (~2751/12576 dev rows, 2671 of which have exactly 4 evidence
triples -- see this module's companion investigation). Each such example's
`evidences` field is FOUR independent (subject, relation, object) facts, each
tied to its own supporting paragraph via `supporting_facts`, e.g.:

    ["El extraño viaje", "director", "Fernando Fernán Gómez"]
    ["Love in Pawn", "director", "Charles Saunders"]
    ["Fernando Fernán Gómez", "date of birth", "28 August 1921"]
    ["Charles Saunders (director)", "date of birth", "8 April 1904"]

for the question "Which film has the director who was born later, El
Extraño Viaje or Love in Pawn?". This is a genuine 4-independent-fact
structure (unlike 2-hop HotpotQA/generic-2WikiMultiHopQA, where there is only
one supporting chain per hop). We inject one near-neighbor-distractor
corruption PER FACT (4 independent context-level faults, no profile
involvement at all), using the SAME "swap in another true value as a
decoy" idea `fault_injection.py`'s own `wrong_value` branch already uses --
we just source the decoy from the *other* (paired) fact in the example
rather than from a synthetic pool, since bridge_comparison's parallel
structure hands us a real near-neighbor for free:

  * fact 0 (filmA's director) <-> fact 1 (filmB's director): same relation
    ("director"), different subject -- swap objects as mutual decoys.
  * fact 2 (personA's DOB)   <-> fact 3 (personB's DOB): same relation
    ("date of birth"), different subject -- swap objects as mutual decoys.

Each fact's corruption is a separate sentence appended to the context,
naming the specific (subject, relation) it concerns, so the four faults are
textually disjoint and independently attributable in the prompt. Resolution
is checked (mechanically, no LLM judge -- same predicate style
`rebuttal_experiment_d_real.py`'s `_fault_ctx_resolved` already uses: true
value present in the produced text) against the FULL trajectory text (all
step texts + final_output), not just `final_output` alone, since the system
prompt asks the agent to show its reasoning in visible `steps` rather than
hide it, and a fact can be "resolved" internally even if not echoed in the
one-sentence final answer.

For N=6, this module also supports layering a SMALL number of the existing,
unmodified profile-constraint faults on top of the 4 hop-context faults, via
`_find_fault` re-imported (unmodified, not copied) from
`double_fault_injection.py`. A direct 2671-example simulation (see
`scripts/rebuttal_experiment_d_real_hop.py`'s module docstring for the exact
counts) found: 73.0% of eligible bridge_comparison rows have >=1 of the 4
mechanically-clean profile-fault types present (enough for N=5 = 4 hop +
1 profile), and 19.9% have >=2 present (enough for N=6 = 4 hop + 2 profile).
Neither number is a workaround -- both are directly measured, and both
provide comfortably large scan pools for n=36-60 examples.

`fault_injection.py` and `double_fault_injection.py` are both untouched --
this module only imports from them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .double_fault_injection import ProfileFaultTarget, _find_fault
from .fault_injection import FaultRecord

# Canonical bridge_comparison evidence layout (validated by the caller to be
# len==4 before this module is used): [filmA_director, filmB_director,
# personA_dob, personB_dob]. Facts are paired by matching relation.
_PAIRS = {0: 1, 1: 0, 2: 3, 3: 2}


@dataclass(frozen=True)
class HopFaultRecord:
    task_id: str
    # per fact index -> (subject, relation, true_object, decoy_object)
    facts: dict[int, tuple[str, str, str, str]]
    corrupted_context_text: str
    # optional profile-constraint faults layered on top (N=6 only)
    profile_faults: dict[str, FaultRecord]
    true_constraint_texts: dict[str, str]
    true_constraint_ids: dict[str, str | None]
    corrupted_profile_dict: dict[str, Any]


def build_hop_multi_fault(
    *,
    task_id: str,
    seed: int,
    profile_dict: dict[str, Any],
    context_text: str,
    evidences: list[tuple[str, str, str]],
    answer: Any,
    profile_targets: list[ProfileFaultTarget] | None = None,
) -> HopFaultRecord:
    """Builds 4 independent hop-level context faults (always) plus
    `len(profile_targets)` additional profile-constraint faults (0 for N=5's
    "pure hop" variant used here with 1 profile fault, or more for N=6),
    each restricted to its own predicate over constraints not already
    claimed -- same disjointness guarantee `build_multi_fault` provides.
    """
    if len(evidences) != 4:
        raise ValueError(
            f"build_hop_multi_fault requires exactly 4 evidence facts (bridge_comparison "
            f"canonical layout), got {len(evidences)} for task_id={task_id!r}"
        )

    facts: dict[int, tuple[str, str, str, str]] = {}
    notes: list[str] = []
    for i, (subject, relation, true_obj) in enumerate(evidences):
        decoy_obj = evidences[_PAIRS[i]][2]
        facts[i] = (subject, relation, true_obj, decoy_obj)
        notes.append(
            f"[Additional note found in a related source: some references instead state "
            f"that {subject}'s {relation} is {decoy_obj!r}.]"
        )
    corrupted_context = context_text.rstrip() + "\n" + "\n".join(notes)

    profile_faults: dict[str, FaultRecord] = {}
    true_texts: dict[str, str] = {}
    true_ids: dict[str, str | None] = {}
    new_constraints_by_id: dict[str, dict[str, Any]] = {
        c["id"]: dict(c) for c in profile_dict["constraints"]
    }
    if profile_targets:
        claimed_ids: set[str] = set()
        working_constraints = list(profile_dict["constraints"])
        for target in profile_targets:
            eligible = [
                c for c in working_constraints
                if c["id"] not in claimed_ids and target.predicate(c)
            ]
            if not eligible:
                raise RuntimeError(
                    f"build_hop_multi_fault: no eligible constraints for slot "
                    f"{target.name!r} (task_id={task_id!r})"
                )
            view = {**profile_dict, "constraints": eligible}
            fr = _find_fault(
                task_id=task_id, seed=seed, profile=view, gold_answer=answer,
                wanted_type="wrong_constraint", tag=f"hopprof_{target.name}",
            )
            true_text = fr.original_text
            matched = next(c for c in eligible if c["text"] == true_text)
            claimed_ids.add(matched["id"])
            new_constraints_by_id[matched["id"]] = {**matched, "text": fr.injected_text}
            profile_faults[target.name] = fr
            true_texts[target.name] = true_text
            true_ids[target.name] = matched["id"]

    corrupted_profile_dict = {
        **profile_dict,
        "constraints": [new_constraints_by_id[c["id"]] for c in profile_dict["constraints"]],
    }

    return HopFaultRecord(
        task_id=task_id,
        facts=facts,
        corrupted_context_text=corrupted_context,
        profile_faults=profile_faults,
        true_constraint_texts=true_texts,
        true_constraint_ids=true_ids,
        corrupted_profile_dict=corrupted_profile_dict,
    )


__all__ = ["HopFaultRecord", "build_hop_multi_fault"]
