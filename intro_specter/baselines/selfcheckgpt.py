"""SelfCheckGPT baseline (Manakul et al. 2023, ACL).

Sampling-based hallucination detection over N=5 alternative completions
of the same prompt at temperature=1.0. The original answer is split
into atomic claims (sentence-level here for simplicity); each claim is
checked against the N alternatives via an LLM consistency prompt. If
any claim is flagged UNSUPPORTED, the model regenerates the full
answer with an instruction to avoid the flagged claims.

This baseline tests whether *detection* alone (without root-cause
attribution) is sufficient for repair. The regeneration is flat —
it doesn't preserve the prefix or attribute the error to a specific
assumption.

Total LLM calls: 1 (initial) + N (samples) + C (consistency) + 0–1
(regeneration), where C = number of sentence-claims in the original.
"""

from __future__ import annotations

import re
from typing import Any

from ..models import ChatProvider
from ..prompts import (
    SELFCHECK_CONSISTENCY_SYSTEM,
    SELFCHECK_REGENERATE_SYSTEM,
    SELFCHECK_SAMPLE_SYSTEM,
    selfcheck_consistency_user,
    selfcheck_regenerate_user,
    selfcheck_sample_user,
)
from ..schemas import (
    Trajectory,
    UserProfile,
    coerce_final_output,
)
from ..verifier import HybridVerifier
from .base import BaselineResult, register


_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")


def _split_claims(text: str, max_claims: int = 6) -> list[str]:
    """Split into sentence-level claims, drop empties, cap to max_claims."""
    if not text:
        return []
    parts = [p.strip() for p in _SENT_SPLIT.split(text.strip())]
    parts = [p for p in parts if p and len(p) > 6]
    return parts[:max_claims]


def run_selfcheckgpt(
    *,
    profile: UserProfile,
    task: dict[str, Any],
    trajectory: Trajectory,
    verifier: HybridVerifier,
    provider: ChatProvider | None = None,
    model: str = "",
    temperature: float = 0.0,
    sample_temperature: float = 1.0,
    seed: int | None = None,
    n_samples: int = 5,
    abstain_on_inconsistency: bool = False,
    **_: Any,
) -> BaselineResult:
    """Run the SelfCheckGPT pipeline. The original answer is taken from
    `trajectory.final_output` (which the runner has already filled via
    the Direct prime call). We sample N alternatives, score each
    sentence-claim for consistency, and regenerate if any are flagged.
    """
    if provider is None or not model:
        result, _ = verifier.check(
            profile=profile, task=task, trajectory=trajectory, final_output=trajectory.final_output
        )
        return BaselineResult(method="selfcheckgpt", final_trajectory=trajectory, verifier=result)

    profile_dict = profile.model_dump(mode="json")
    base_seed = seed or 0
    tokens_in = 0
    tokens_out = 0
    n_calls = 0

    original_answer = trajectory.final_output or ""

    # 1. Sample N alternatives at higher temperature.
    alternatives: list[str] = []
    for i in range(n_samples):
        sample_seed = base_seed * 7919 + i * 1009 + 1
        payload, completion = provider.complete_json(
            system=SELFCHECK_SAMPLE_SYSTEM,
            user=selfcheck_sample_user(profile_dict, task),
            model=model,
            temperature=sample_temperature,
            seed=sample_seed,
            max_tokens=512,
        )
        alt = coerce_final_output(payload.get("final_output"), fallback="") or ""
        alternatives.append(alt)
        tokens_in += completion.tokens_input
        tokens_out += completion.tokens_output
        n_calls += 1

    # 2. Per-sentence consistency check.
    claims = _split_claims(original_answer)
    flagged: list[str] = []
    flagged_rationales: list[str] = []
    for claim in claims:
        payload, completion = provider.complete_json(
            system=SELFCHECK_CONSISTENCY_SYSTEM,
            user=selfcheck_consistency_user(claim, alternatives),
            model=model,
            temperature=0.0,
            seed=base_seed + 31337,
            max_tokens=256,
        )
        verdict = str(payload.get("verdict", "")).strip().upper()
        rationale = str(payload.get("rationale", ""))
        tokens_in += completion.tokens_input
        tokens_out += completion.tokens_output
        n_calls += 1
        if "UNSUPPORTED" in verdict:
            flagged.append(claim)
            flagged_rationales.append(rationale[:200])

    # 3. If any claims flagged, regenerate. Otherwise commit the original answer.
    final = original_answer
    detected = bool(flagged)
    abstained = False
    regen_used = False
    if detected:
        if abstain_on_inconsistency:
            abstained = True
        else:
            payload, completion = provider.complete_json(
                system=SELFCHECK_REGENERATE_SYSTEM,
                user=selfcheck_regenerate_user(profile_dict, task, flagged),
                model=model,
                temperature=temperature,
                seed=base_seed + 41999,
                max_tokens=512,
            )
            final = coerce_final_output(payload.get("final_output"), fallback=original_answer) or original_answer
            tokens_in += completion.tokens_input
            tokens_out += completion.tokens_output
            n_calls += 1
            regen_used = True

    new_traj = Trajectory(
        task_id=trajectory.task_id,
        steps=trajectory.steps,
        final_output=final,
    )
    final_verdict, _ = verifier.check(
        profile=profile, task=task, trajectory=new_traj, final_output=new_traj.final_output
    )
    return BaselineResult(
        method="selfcheckgpt",
        final_trajectory=new_traj,
        verifier=final_verdict,
        tokens_input=tokens_in,
        tokens_output=tokens_out,
        meta={
            "n_samples": n_samples,
            "n_claims_checked": len(claims),
            "n_claims_flagged": len(flagged),
            "detected": detected,
            "abstained": abstained,
            "regen_used": regen_used,
            "flagged_rationales": flagged_rationales[:3],
            "n_llm_calls": n_calls,
        },
    )


register("selfcheckgpt", run_selfcheckgpt)
