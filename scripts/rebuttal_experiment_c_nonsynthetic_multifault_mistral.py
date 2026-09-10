#!/usr/bin/env python3
"""Experiment C non-synthetic multi-fault leg, model=mistral-nemo-12b.

Thin per-model wrapper around
`rebuttal_experiment_c_nonsynthetic_multifault_common.py` (shared native
multi-fault construction + 7-arm-runner core). See that module's docstring
for the full N=2..5 design and per-level feasibility.

Usage:
    python3 scripts/rebuttal_experiment_c_nonsynthetic_multifault_mistral.py --smoke --num-faults 2
    python3 scripts/rebuttal_experiment_c_nonsynthetic_multifault_mistral.py --num-faults 2 --seeds 0,1,2 --n-examples 60
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))


def _load_module(name: str, rel_path: str):
    spec = importlib.util.spec_from_file_location(name, _REPO_ROOT / rel_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


_COMMON = _load_module(
    "nonsynth_multifault_common_mistral", "scripts/rebuttal_experiment_c_nonsynthetic_multifault_common.py"
)

MODEL_TABLE = {
    "mistral-nemo-12b": ("openrouter", "mistralai/mistral-nemo"),
}

if __name__ == "__main__":
    _COMMON.run_cli(model_table=MODEL_TABLE, default_model="mistral-nemo-12b", default_output_dirname="mistral-nemo-12b")
