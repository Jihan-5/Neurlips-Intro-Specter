"""Additive N-fault injector for the musique_real N=4/N=5 multi-fault sweep,
built on MuSiQue's OWN native multi-hop structure -- a DIFFERENT (and, per
the investigation below, structurally BETTER) resource than the one
`intro_specter/profiles/hop_fault_injection.py` uses for twowiki_real.

Context / why this file exists
-------------------------------
`double_fault_injection.py`'s `build_multi_fault` (1 context fault + N-1
profile-constraint faults) is dataset-agnostic and works fine for musique_real
at N=2 (1 profile-fault type required) and N=3 (2 types required) -- see
`scripts/rebuttal_experiment_d_real_musique_common.py`'s module docstring for
the measured co-occurrence numbers. N=4 would need 3-way co-occurrence of the
4 available mechanically-clean profile-fault types (english/concise/bullets/
preamble), and a direct simulation over musique_real's full 760-row 3-hop
pool (dgslibisey/MuSiQue validation split, `id` starting with "3hop") found
only 3/760 (0.4%) qualifying examples -- not enough for n=36-60. N=4/5 need a
genuinely different resource, the same situation `hop_fault_injection.py`
solved for twowiki_real using its `bridge_comparison` question type's 4
independent evidence facts.

MuSiQue's OWN dataset schema already provides an analogous (and, for the
3-hop subset used here, UNIVERSAL rather than a filtered minority) resource:
every 3hop-tagged row's `question_decomposition` field is a list of exactly 3
single-hop sub-questions, each with its own `answer` and
`paragraph_support_idx` -- e.g. for id `2hop__...` style chains:

    [{"question": "The Hobbit >> part of the series", "answer": "South Park", ...},
     {"question": "who does the voice of stan on #1", "answer": "Trey Parker", ...},
     {"question": "#2 >> place of birth", "answer": "Denver", ...}]

A direct check over the full validation split (see this module's companion
investigation, run before writing this file) found ALL 760/760 3hop rows have
exactly 3 decomposition steps, each with a non-empty `answer` -- i.e. this
resource requires no filtering to a rare subset the way twowiki's
`bridge_comparison` (2671/12576 dev rows) did. That makes musique_real's
native hop structure a STRICTLY BETTER basis for a hop-fault injector than
twowiki's bridge_comparison rows: every 3-hop example qualifies, not just a
minority question-type.

Unlike twowiki's bridge_comparison, MuSiQue's 3 hops are a SEQUENTIAL chain
(hop 2's question references hop 1's answer via the literal string "#1", hop
3 references hop 2's answer via "#2") rather than two independent PARALLEL
pairs with a matching relation -- so there is no natural same-relation
"mutual decoy" partner the way twowiki's director<->director /
DOB<->DOB pairing worked. Instead, each hop's decoy is generated with the
SAME near-neighbor-distractor mechanism `fault_injection.py`'s own
`wrong_value` branch already uses for the overall gold answer
(`_wrong_value_pool`, imported here UNMODIFIED, not copied) -- applied
per-hop-answer instead of once per task. This is not a new invented
corruption idea; it is the existing mechanism, reused per-fact instead of
once.

For N=5, this module also supports layering 1-2 of the existing, unmodified
profile-constraint faults on top of the 3 hop-context faults, via
`_find_fault` re-imported (unmodified, not copied) from
`double_fault_injection.py`. A direct 760-row simulation (same one referenced
above) found: 72.8% of examples have >=1 of the 4 mechanically-clean
profile-fault types present (enough for N=4 = 3 hop + 1 profile), 19.5% have
>=2 present (enough for N=5 = 3 hop + 2 profile), and only 0.4% (3/760) have
>=3 present -- so N=6 (3 hop + 3 profile) is, like twowiki's analogous N=6,
found IMPRACTICAL to construct at n=36-60 and is intentionally NOT exposed
as a supported num_faults value by the caller script.

`fault_injection.py` and `double_fault_injection.py` are both untouched --
this module only imports from them.
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from typing import Any

from .double_fault_injection import ProfileFaultTarget, _find_fault
from .fault_injection import FaultRecord, _wrong_value_pool

N_HOP_FACTS = 3


def _hop_seed(task_id: str, seed: int, i: int) -> int:
    """Deterministic derived seed for hop i's decoy draw -- sha256-based
    (not Python's randomized `hash()`), matching the determinism convention
    `double_fault_injection.py::_derived_seed` already documents."""
    h = hashlib.sha256(f"musique_hop::{task_id}::{seed}::{i}".encode()).hexdigest()
    return int(h[:12], 16)


@dataclass(frozen=True)
class MusiqueHopFaultRecord:
    task_id: str
    # per hop index -> (sub_question, true_answer, decoy_answer)
    facts: dict[int, tuple[str, str, str]]
    corrupted_context_text: str
    # optional profile-constraint faults layered on top (N=5 only)
    profile_faults: dict[str, FaultRecord]
    true_constraint_texts: dict[str, str]
    true_constraint_ids: dict[str, str | None]
    corrupted_profile_dict: dict[str, Any]


def build_musique_hop_fault(
    *,
    task_id: str,
    seed: int,
    profile_dict: dict[str, Any],
    context_text: str,
    decomposition: list[dict[str, Any]],
    profile_targets: list[ProfileFaultTarget] | None = None,
) -> MusiqueHopFaultRecord:
    """Builds 3 independent hop-level context faults (always, one per
    `question_decomposition` step) plus `len(profile_targets)` additional
    profile-constraint faults (0 for the "pure hop" N=4 variant, 1-2 for
    N=5), each restricted to its own predicate over constraints not already
    claimed -- same disjointness guarantee `build_hop_multi_fault` (the
    twowiki analogue) provides.
    """
    if len(decomposition) != N_HOP_FACTS:
        raise ValueError(
            f"build_musique_hop_fault requires exactly {N_HOP_FACTS} decomposition "
            f"steps (musique_real 3-hop canonical layout), got {len(decomposition)} "
            f"for task_id={task_id!r}"
        )

    facts: dict[int, tuple[str, str, str]] = {}
    notes: list[str] = []
    for i, step in enumerate(decomposition):
        sub_question = str(step["question"])
        true_answer = str(step["answer"])
        pool = _wrong_value_pool(true_answer)
        rng = random.Random(_hop_seed(task_id, seed, i))
        decoy = rng.choice(pool) if pool else "[corrupted value]"
        facts[i] = (sub_question, true_answer, decoy)
        notes.append(
            "[Additional note found in a related source: regarding the sub-question "
            f"{sub_question!r}, some references instead give the answer as {decoy!r}.]"
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
                    f"build_musique_hop_fault: no eligible constraints for slot "
                    f"{target.name!r} (task_id={task_id!r})"
                )
            view = {**profile_dict, "constraints": eligible}
            fr = _find_fault(
                task_id=task_id, seed=seed, profile=view, gold_answer=decomposition[-1]["answer"],
                wanted_type="wrong_constraint", tag=f"musiquehopprof_{target.name}",
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

    return MusiqueHopFaultRecord(
        task_id=task_id,
        facts=facts,
        corrupted_context_text=corrupted_context,
        profile_faults=profile_faults,
        true_constraint_texts=true_texts,
        true_constraint_ids=true_ids,
        corrupted_profile_dict=corrupted_profile_dict,
    )


__all__ = ["MusiqueHopFaultRecord", "N_HOP_FACTS", "build_musique_hop_fault"]
