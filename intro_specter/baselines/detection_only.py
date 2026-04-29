"""Detection-only baseline (SelfCheckGPT / HaloScope-style).

Runs an LLM detector over the agent trajectory and asks whether a
profile-grounded violation is present. If yes, the baseline *abstains*:
the trajectory is left unchanged but marked as detected. If no, the
trajectory is committed.

This baseline isolates the contribution of *detection* from the
contribution of *repair* — showing that flagging an error without
correcting it doesn't lift downstream success.

Success accounting:
* If the model abstains and the trajectory truly fails → counted as
  success in selective-accuracy but as a hold-out in coverage.
* If the model abstains and the trajectory was actually correct →
  counted as a false positive (we didn't commit a correct answer).
* If the model commits and the trajectory passes the verifier → success.
* If the model commits and the trajectory fails → failure.

Following the standard SelfCheckGPT evaluation, we report **commit-rate
weighted accuracy** in summary statistics. The runner records the
abstention decision via `meta["abstained"]`.
"""

from __future__ import annotations

from typing import Any

from ..models import ChatProvider
from ..prompts import DETECTION_ONLY_SYSTEM, detection_only_user
from ..schemas import Trajectory, UserProfile
from ..verifier import HybridVerifier
from .base import BaselineResult, register


def run_detection_only(
    *,
    profile: UserProfile,
    task: dict[str, Any],
    trajectory: Trajectory,
    verifier: HybridVerifier,
    provider: ChatProvider | None = None,
    model: str = "",
    temperature: float = 0.0,
    seed: int | None = None,
    abstain_on_detection: bool = True,
    **_: Any,
) -> BaselineResult:
    # Always run the rule-based ground-truth verifier so success is recorded.
    final_verdict, _ = verifier.check(
        profile=profile, task=task, trajectory=trajectory, final_output=trajectory.final_output
    )

    if provider is None or not model:
        # No-LLM fallback: behave like Direct.
        return BaselineResult(
            method="detection_only",
            final_trajectory=trajectory,
            verifier=final_verdict,
            meta={"detected": False, "abstained": False, "detector_confidence": 0.0},
        )

    payload, completion = provider.complete_json(
        system=DETECTION_ONLY_SYSTEM,
        user=detection_only_user(
            profile=profile.model_dump(mode="json"),
            task=task,
            trajectory=trajectory.model_dump(mode="json"),
            final_output=trajectory.final_output,
        ),
        model=model,
        temperature=temperature,
        seed=seed,
        max_tokens=512,
    )
    detected = bool(payload.get("violation_present", False))
    detector_confidence = float(payload.get("confidence", 0.5) or 0.5)
    rationale = str(payload.get("rationale", ""))[:300]

    abstained = bool(detected and abstain_on_detection)

    # When we abstain, the verifier verdict still reflects ground truth.
    # The downstream runner reads meta["abstained"] for selective metrics;
    # success on the abstained trial is computed against the *original*
    # trajectory (whatever it was), so this baseline never changes the
    # trajectory itself — by design.
    return BaselineResult(
        method="detection_only",
        final_trajectory=trajectory,
        verifier=final_verdict,
        tokens_input=completion.tokens_input,
        tokens_output=completion.tokens_output,
        meta={
            "detected": detected,
            "detector_confidence": detector_confidence,
            "abstained": abstained,
            "rationale": rationale,
        },
    )


register("detection_only", run_detection_only)
