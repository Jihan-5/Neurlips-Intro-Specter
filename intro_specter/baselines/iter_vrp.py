"""IterVRP: violation-reprompt baseline run at Intro-Specter's matched retry budget.

Experiment B (rebuttal campaign) asks: at the SAME round budget Intro-Specter gets
(1 initial generation + up to T_spr=2 additional rounds = 3 rounds total), does
flat-text violation feedback with full-trajectory regeneration match selective,
attributed subgraph repair? This module answers the "flat-text, matched-budget"
side of that comparison.

This is a thin wrapper around the existing `violation_reprompt` baseline
(`intro_specter/baselines/violation_reprompt.py`), which already implements
exactly the retry-loop shape we need:

  - each iteration re-verifies the CURRENT trajectory,
  - stops (returns) immediately if the verifier accepts,
  - otherwise formats the verifier's violated-span feedback via
    `_format_violation_feedback` and regenerates the FULL trajectory
    (never a selective/subgraph repair — that is the point of the
    comparison), and
  - loops up to `max_trials` regeneration rounds.

`run_violation_reprompt` is called with the caller-supplied trajectory treated
as round 1 (no regeneration needed if it already passes). Each loop iteration
beyond that is round 2, 3, .... To land on the same "1 + 2 retries = 3 rounds
total" budget as Intro-Specter's default `spr_max_rounds=2`, IterVRP fixes
`max_trials=2` (i.e. at most 2 regenerations on top of the initial trajectory).

No other file was modified to add this baseline (additive-only, per the
rebuttal-campaign constraint) — it is not registered in
`intro_specter/baselines/__init__.py` or `base.py`'s global registry; callers
should import `run_iter_vrp` directly, as `scripts/rebuttal_experiment_b.py`
does.
"""

from __future__ import annotations

from typing import Any

from ..models import ChatProvider
from ..schemas import Trajectory, UserProfile
from ..verifier import HybridVerifier
from .base import BaselineResult
from .violation_reprompt import run_violation_reprompt

# Intro-Specter's default budget is 1 initial verify/decide round + spr_max_rounds
# (default 2) additional SPR rounds = 3 rounds total (see IntroSpecterConfig in
# intro_specter/pipeline.py). IterVRP's round 1 is the caller-supplied trajectory
# itself (checked, not regenerated, if already passing) so MAX_TRIALS=2 additional
# regenerations gives the same 3-round ceiling.
MAX_TRIALS_DEFAULT = 2


def run_iter_vrp(
    *,
    profile: UserProfile,
    task: dict[str, Any],
    trajectory: Trajectory,
    verifier: HybridVerifier,
    provider: ChatProvider | None = None,
    model: str = "",
    max_trials: int = MAX_TRIALS_DEFAULT,
    temperature: float = 0.7,
    seed: int | None = None,
    **kwargs: Any,
) -> BaselineResult:
    """Run violation-reprompt in a loop, budget-matched to Intro-Specter.

    Returns the same `BaselineResult` shape as `run_violation_reprompt`, with
    `meta["rounds_used"]` added: 1 (the initial trajectory, un-regenerated) plus
    the number of regeneration rounds actually performed (`meta["trials"]`,
    which is <= max_trials and stops early the moment the verifier accepts).
    """
    result = run_violation_reprompt(
        profile=profile,
        task=task,
        trajectory=trajectory,
        verifier=verifier,
        provider=provider,
        model=model,
        max_trials=max_trials,
        temperature=temperature,
        seed=seed,
        **kwargs,
    )
    n_trials = int(result.meta.get("trials", 0))
    result.meta["rounds_used"] = 1 + n_trials
    result.meta["max_trials"] = max_trials
    return result
