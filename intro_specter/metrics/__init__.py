"""Metrics — attribution, calibration, detection, paired statistical tests."""

from .attribution import (
    ancestor_hit_rate,
    earliest_fault_distance,
    mrr,
    topk_accuracy,
)
from .calibration import brier_score, expected_calibration_error
from .detection import (
    auprc,
    auroc,
    detection_f1,
    false_commit_rate,
)
from .repair import degradation_rate, delta_success_rate
from .stats import (
    holm_bonferroni,
    mcnemar,
    paired_bootstrap_ci,
    wilcoxon_signed_rank,
)

__all__ = [
    "ancestor_hit_rate",
    "auprc",
    "auroc",
    "brier_score",
    "degradation_rate",
    "delta_success_rate",
    "detection_f1",
    "earliest_fault_distance",
    "expected_calibration_error",
    "false_commit_rate",
    "holm_bonferroni",
    "mcnemar",
    "mrr",
    "paired_bootstrap_ci",
    "topk_accuracy",
    "wilcoxon_signed_rank",
]
