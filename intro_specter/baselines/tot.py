"""Tree of Thoughts baseline (Yao et al. 2023, NeurIPS).

BFS over reasoning branches. At each depth we sample `k` candidate
next-steps per surviving path, score each candidate with a value
prompt that includes the user profile, and keep the top `b` paths
(beam width). Continue until `max_depth` or a candidate's value score
indicates "answer-ready", then call the solve prompt for the final
answer on the best path.

For profile-grounded tasks, the value prompt subtracts 3 from any
candidate that violates a hard profile constraint, biasing the search
away from constraint-violating paths.

Total LLM calls: at most `k × max_depth` generation + `k × max_depth`
evaluation + 1 solve. Defaults k=3, b=2, max_depth=5 for QA — about
31 calls per trial.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..models import ChatProvider
from ..prompts import (
    TOT_EVALUATE_SYSTEM,
    TOT_GENERATE_SYSTEM,
    TOT_SOLVE_SYSTEM,
    tot_evaluate_user,
    tot_generate_user,
    tot_solve_user,
)
from ..schemas import (
    Trajectory,
    TrajectoryStep,
    UserProfile,
    coerce_final_output,
)
from ..verifier import HybridVerifier
from .base import BaselineResult, register


@dataclass
class _ToTNode:
    path: list[str] = field(default_factory=list)
    score: float = 0.0


def _generate_next(
    *,
    provider: ChatProvider,
    model: str,
    profile_dict: dict,
    task: dict[str, Any],
    path_so_far: list[str],
    seed: int | None,
    temperature: float,
) -> tuple[str, int, int]:
    payload, completion = provider.complete_json(
        system=TOT_GENERATE_SYSTEM,
        user=tot_generate_user(profile_dict, task, path_so_far),
        model=model,
        temperature=temperature,
        seed=seed,
        max_tokens=512,
    )
    step = str(payload.get("next_step", "")).strip() or "(no step)"
    return step, completion.tokens_input, completion.tokens_output


def _evaluate(
    *,
    provider: ChatProvider,
    model: str,
    profile_dict: dict,
    task: dict[str, Any],
    path: list[str],
    seed: int | None,
    temperature: float,
) -> tuple[float, int, int]:
    payload, completion = provider.complete_json(
        system=TOT_EVALUATE_SYSTEM,
        user=tot_evaluate_user(profile_dict, task, path),
        model=model,
        temperature=temperature,
        seed=seed,
        max_tokens=256,
    )
    try:
        score = float(payload.get("score", 0))
    except (TypeError, ValueError):
        score = 0.0
    return max(0.0, min(10.0, score)), completion.tokens_input, completion.tokens_output


def _solve(
    *,
    provider: ChatProvider,
    model: str,
    profile_dict: dict,
    task: dict[str, Any],
    best_path: list[str],
    seed: int | None,
    temperature: float,
    fallback: str | None,
) -> tuple[str, int, int]:
    payload, completion = provider.complete_json(
        system=TOT_SOLVE_SYSTEM,
        user=tot_solve_user(profile_dict, task, best_path),
        model=model,
        temperature=temperature,
        seed=seed,
        max_tokens=512,
    )
    final = coerce_final_output(payload.get("final_output"), fallback=fallback) or ""
    return final, completion.tokens_input, completion.tokens_output


def run_tot(
    *,
    profile: UserProfile,
    task: dict[str, Any],
    trajectory: Trajectory,
    verifier: HybridVerifier,
    provider: ChatProvider | None = None,
    model: str = "",
    temperature: float = 0.7,
    seed: int | None = None,
    k: int = 3,                 # candidates per parent
    b: int = 2,                 # beam width
    max_depth: int = 5,
    **_: Any,
) -> BaselineResult:
    if provider is None or not model:
        result, _ = verifier.check(
            profile=profile, task=task, trajectory=trajectory, final_output=trajectory.final_output
        )
        return BaselineResult(method="tot", final_trajectory=trajectory, verifier=result)

    profile_dict = profile.model_dump(mode="json")
    tokens_in = 0
    tokens_out = 0
    n_calls = 0

    # BFS: start from a single empty path, expand to k * b at each depth, prune to b.
    beam: list[_ToTNode] = [_ToTNode(path=[], score=0.0)]
    base_seed = seed or 0

    for depth in range(max_depth):
        new_candidates: list[_ToTNode] = []
        for parent_idx, parent in enumerate(beam):
            for cand_idx in range(k):
                step_seed = base_seed + 7919 * (depth * 100 + parent_idx * 10 + cand_idx)
                step, ti, to = _generate_next(
                    provider=provider, model=model,
                    profile_dict=profile_dict, task=task,
                    path_so_far=parent.path,
                    seed=step_seed,
                    temperature=temperature,
                )
                tokens_in += ti
                tokens_out += to
                n_calls += 1
                new_path = parent.path + [step]
                # Score this new path.
                eval_seed = base_seed + 11003 * (depth * 100 + parent_idx * 10 + cand_idx)
                score, ti2, to2 = _evaluate(
                    provider=provider, model=model,
                    profile_dict=profile_dict, task=task,
                    path=new_path,
                    seed=eval_seed,
                    temperature=0.0,  # deterministic eval
                )
                tokens_in += ti2
                tokens_out += to2
                n_calls += 1
                new_candidates.append(_ToTNode(path=new_path, score=score))

        # Prune to top b by score.
        new_candidates.sort(key=lambda n: -n.score)
        beam = new_candidates[:b]

        # Early stop if best score is high (≥ 9 means answer-ready in our scale).
        if beam and beam[0].score >= 9.0:
            break

    best = beam[0] if beam else _ToTNode(path=["(empty path)"], score=0.0)

    final, ti, to = _solve(
        provider=provider, model=model,
        profile_dict=profile_dict, task=task,
        best_path=best.path,
        seed=base_seed + 99991,
        temperature=0.0,
        fallback=trajectory.final_output,
    )
    tokens_in += ti
    tokens_out += to
    n_calls += 1

    # Render the winning path as a Trajectory.
    steps: list[TrajectoryStep] = [
        TrajectoryStep(step_id=i + 1, kind="assumption", text=p, reason_summary="ToT step")  # type: ignore[arg-type]
        for i, p in enumerate(best.path)
    ]
    new_traj = Trajectory(
        task_id=trajectory.task_id,
        steps=steps or trajectory.steps,
        final_output=final or trajectory.final_output,
    )
    final_verdict, _ = verifier.check(
        profile=profile, task=task, trajectory=new_traj, final_output=new_traj.final_output
    )
    return BaselineResult(
        method="tot",
        final_trajectory=new_traj,
        verifier=final_verdict,
        tokens_input=tokens_in,
        tokens_output=tokens_out,
        meta={
            "n_llm_calls": n_calls,
            "k": k,
            "b": b,
            "max_depth": max_depth,
            "best_path_score": best.score,
            "best_path_len": len(best.path),
        },
    )


register("tot", run_tot)
