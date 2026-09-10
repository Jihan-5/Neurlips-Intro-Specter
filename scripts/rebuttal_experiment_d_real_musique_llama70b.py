#!/usr/bin/env python3
"""Experiment D (real), musique_real leg, model=llama-3.3-70b (via Together,
NOT OpenRouter -- matches the existing repo convention, e.g.
`configs/real/spr__musique_real__llama-3.3-70b.yaml`).

Thin per-model wrapper around `rebuttal_experiment_d_real_musique_common.py`
(shared fault-construction + 7-arm-runner core). See that module's docstring
for the full N=2..5 design.

Usage:
    python3 scripts/rebuttal_experiment_d_real_musique_llama70b.py --smoke --num-faults 2
    python3 scripts/rebuttal_experiment_d_real_musique_llama70b.py --num-faults 4 --seeds 0,1,2 --n-examples 60
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


_COMMON = _load_module("musique_common_llama70b", "scripts/rebuttal_experiment_d_real_musique_common.py")

MODEL_TABLE = {
    "llama-3.3-70b": ("together", "meta-llama/Llama-3.3-70B-Instruct-Turbo"),
}

if __name__ == "__main__":
    _COMMON.run_cli(model_table=MODEL_TABLE, default_model="llama-3.3-70b", default_output_dirname="llama-3.3-70b")
