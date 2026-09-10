#!/usr/bin/env python3
"""Experiment C non-synthetic multi-fault leg, model=qwen-2.5-72b (via
OpenRouter, matching the existing qwen-2.5-7b convention).

Post-hoc 5th model, added after the original 4-model matrix
(mistral-nemo-12b, qwen-2.5-7b, llama-3.1-8b, llama-3.3-70b) showed a 2-2
split on TravelPlanner non-synthetic multi-fault (intro_specter ahead on
llama-3.3-70b and qwen-2.5-7b, behind on llama-3.1-8b and mistral-nemo-12b).
Chosen as a same-size-class, same-family extension of llama-3.3-70b (72B vs
70B dense, same generation) -- NOT chosen or reported based on expected
outcome; results here are reported regardless of which way they land.

Thin per-model wrapper around
`rebuttal_experiment_c_nonsynthetic_multifault_common.py`. See that module's
docstring for the full N=2..5 design.

Usage:
    python3 scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen72b.py --smoke --num-faults 2
    python3 scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen72b.py --num-faults 2 --seeds 0,1,2 --n-examples 60
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
    "nonsynth_multifault_common_qwen72b", "scripts/rebuttal_experiment_c_nonsynthetic_multifault_common.py"
)

MODEL_TABLE = {
    "qwen-2.5-72b": ("openrouter", "qwen/qwen-2.5-72b-instruct"),
}

if __name__ == "__main__":
    _COMMON.run_cli(model_table=MODEL_TABLE, default_model="qwen-2.5-72b", default_output_dirname="qwen-2.5-72b")
