"""Shared types and dispatcher for baselines."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from ..schemas import Trajectory, UserProfile, VerifierResult
from ..verifier import HybridVerifier


@dataclass
class BaselineResult:
    method: str
    final_trajectory: Trajectory
    verifier: VerifierResult
    tokens_input: int = 0
    tokens_output: int = 0
    latency_ms: float = 0.0
    meta: dict[str, Any] = field(default_factory=dict)


# A baseline is a function with the signature:
# (profile, task, trajectory, verifier, **kwargs) -> BaselineResult
BaselineFn = Callable[..., BaselineResult]

_REGISTRY: dict[str, BaselineFn] = {}


def register(name: str, fn: BaselineFn) -> None:
    _REGISTRY[name] = fn


def run_baseline(
    name: str,
    *,
    profile: UserProfile,
    task: dict[str, Any],
    trajectory: Trajectory,
    verifier: HybridVerifier,
    **kwargs: Any,
) -> BaselineResult:
    if name not in _REGISTRY:
        raise KeyError(f"unknown baseline {name!r}. Registered: {sorted(_REGISTRY)}")
    return _REGISTRY[name](
        profile=profile,
        task=task,
        trajectory=trajectory,
        verifier=verifier,
        **kwargs,
    )
