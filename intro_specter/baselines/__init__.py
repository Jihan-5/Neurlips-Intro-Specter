"""Self-correction baselines used in the experiment plan.

Each baseline exposes the same `run(...) -> BaselineResult` signature so the
experiment runner can drop one in for another. Forward-only baselines (Direct,
Self-Refine, Reflexion, Full-Regen, Oracle-Repair) are implemented here. ReAct,
ToT, and tool-grounded baselines belong in benchmark-specific subpackages
because they require an environment.
"""

from .base import BaselineResult, run_baseline
from .direct import run_direct
from .full_regen import run_full_regen
from .oracle_repair import run_oracle_repair
from .reflexion import run_reflexion
from .self_refine import run_self_refine

__all__ = [
    "BaselineResult",
    "run_baseline",
    "run_direct",
    "run_full_regen",
    "run_oracle_repair",
    "run_reflexion",
    "run_self_refine",
]
