#!/usr/bin/env python3
"""Recipes non-synthetic multi-fault leg, model=llama-3.3-70b (via Together,
matching the existing repo convention, e.g.
`configs/real/spr__musique_real__llama-3.3-70b.yaml`).

Thin per-model wrapper around `rebuttal_experiment_recipes_common.py`.

Usage:
    python3 scripts/rebuttal_experiment_recipes_llama70b.py --smoke --num-faults 1
    python3 scripts/rebuttal_experiment_recipes_llama70b.py --num-faults 1 --seeds 0,1,2 --n-examples 60
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


_COMMON = _load_module("recipes_common_llama70b", "scripts/rebuttal_experiment_recipes_common.py")

MODEL_TABLE = {
    "llama-3.3-70b": ("together", "meta-llama/Llama-3.3-70B-Instruct-Turbo"),
}

if __name__ == "__main__":
    _COMMON.run_cli(model_table=MODEL_TABLE, default_model="llama-3.3-70b", default_output_dirname="llama-3.3-70b")
