"""Profile injection + fault injection utilities for the real-benchmark suite.

This sub-package is shared across the four real-data loaders
(hotpotqa_real, truthfulqa_real, strategyqa_real, travelplanner_real)
so that the profile-grounded conditions are applied consistently
across the matrix.

Two responsibilities:

* `templates`: a bank of ~50 realistic user-profile constraint templates
  tagged by category (dietary / language / accessibility / expertise /
  budget / time / cultural / preference) and by "relevance to the task"
  semantics. Selected deterministically via hash(task_id + seed) so the
  same example always gets the same profile.
* `fault_injection`: deterministic injection of one wrong assumption
  per ~30% of trials, with a recorded `gold_fault_node_id` so the
  Intro-Specter posterior can be scored for top-1 / top-3 / MRR
  attribution accuracy.
"""

from .fault_injection import FaultRecord, inject_fault
from .templates import (
    PROFILE_TEMPLATES,
    ProfileConstraint,
    inject_profile,
)

__all__ = [
    "FaultRecord",
    "PROFILE_TEMPLATES",
    "ProfileConstraint",
    "inject_fault",
    "inject_profile",
]
