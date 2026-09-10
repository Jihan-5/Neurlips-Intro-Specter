"""Self-correction baselines used in the experiment plan.

Each baseline exposes the same `run(...) -> BaselineResult` signature so the
experiment runner can drop one in for another. Forward-only baselines (Direct,
Self-Refine, Reflexion, Full-Regen, Oracle-Repair) are implemented here. ReAct,
ToT, and tool-grounded baselines belong in benchmark-specific subpackages
because they require an environment.
"""

from .base import BaselineResult, run_baseline
from .detection_only import run_detection_only
from .direct import run_direct
from .full_regen import run_full_regen
from .oracle_detector import run_oracle_detector
from .oracle_repair import run_oracle_repair
from .react import run_react
from .reflexion import run_reflexion
from .selfcheckgpt import run_selfcheckgpt
from .self_refine import run_self_refine
from .tot import run_tot
from .violation_reprompt import run_violation_reprompt

__all__ = [
    "BaselineResult",
    "run_baseline",
    "run_detection_only",
    "run_direct",
    "run_full_regen",
    "run_oracle_detector",
    "run_oracle_repair",
    "run_react",
    "run_reflexion",
    "run_selfcheckgpt",
    "run_self_refine",
    "run_tot",
    "run_violation_reprompt",
]
