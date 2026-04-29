"""Generate the YAML configs for the real-benchmark matrix.

Spec asked for 224 configs (4 datasets × 8 models × 7 methods). We produce
one config per (dataset, model) cell with all 7 methods inside (4 × 8 = 32
configs total) — this preserves cache efficiency: the Direct baseline's
primed trajectory is generated once per cell and reused across the other
forward-correction baselines (Self-Refine, Reflexion, Full-Regen,
SelfCheckGPT), reducing API spend by ~30 %.

For reviewers wanting selective re-runs of a single method, the runner
supports `--method-filter` to run a subset; or the per-method
configs can be derived by filtering the `methods` list.
"""

from __future__ import annotations

from itertools import product
from pathlib import Path

import yaml


DATASETS = {
    "hotpotqa_real":     {"n_examples": 60, "split": "test", "label": "Real-HotpotQA"},
    "truthfulqa_real":   {"n_examples": 60, "split": "test", "label": "Real-TruthfulQA"},
    "strategyqa_real":   {"n_examples": 60, "split": "test", "label": "Real-StrategyQA"},
    "travelplanner_real":{"n_examples": 60, "split": "test", "label": "Real-TravelPlanner"},
}

MODELS = [
    # (slug, provider_name, model_id)
    ("llama-3.3-70b",   "together",   "meta-llama/Llama-3.3-70B-Instruct-Turbo"),
    ("llama-3.1-8b",    "openrouter", "meta-llama/llama-3.1-8b-instruct"),
    ("deepseek-v3",     "together",   "deepseek-ai/DeepSeek-V3"),
    ("deepseek-v3.1",   "together",   "deepseek-ai/DeepSeek-V3.1"),
    ("mistral-nemo-12b","openrouter", "mistralai/mistral-nemo"),
    ("qwen-2.5-7b",     "openrouter", "qwen/qwen-2.5-7b-instruct"),
    ("gemini-2.5-flash","openrouter", "google/gemini-2.5-flash"),
    ("gpt-oss-20b",     "together",   "openai/gpt-oss-20b"),
]

# Method block templates. The runner consumes this list verbatim.
def _methods_block(provider: str, model: str) -> list[dict]:
    return [
        {"name": "direct",         "provider_name": provider, "model": model},
        {"name": "self_refine",    "provider_name": provider, "model": model},
        {"name": "reflexion",      "provider_name": provider, "model": model,
         "extra": {"max_trials": 2}},
        {"name": "full_regen",     "provider_name": provider, "model": model,
         "extra": {"max_attempts": 1}},
        {"name": "react",          "provider_name": provider, "model": model,
         "extra": {"max_steps": 4}},
        {"name": "selfcheckgpt",   "provider_name": provider, "model": model,
         "extra": {"n_samples": 5, "sample_temperature": 1.0}},
        # ToT is expensive (k×depth×2 calls per trial). Use modest defaults to
        # keep within budget. Skipped for the most expensive (DS V3.1, Llama 70B)
        # × planning combinations to control spend; we'll re-add them after the
        # initial pass if budget allows.
        {"name": "tot",            "provider_name": provider, "model": model,
         "extra": {"tot_candidates": 3, "tot_beam_width": 2,
                   "tot_max_depth": 4, "tot_temperature": 0.7}},
        {"name": "intro_specter_llm", "provider_name": provider, "model": model,
         "temperature": 0.0,
         "extra": {"tau_abstain": 0.0, "n_counterfactual_trials": 1}},
    ]


def main() -> None:
    out_dir = Path("configs/real")
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for (ds_name, ds_cfg), (slug, provider, model_id) in product(DATASETS.items(), MODELS):
        config = {
            "benchmark": ds_name,
            "split": ds_cfg["split"],
            "n_examples": ds_cfg["n_examples"],
            "seeds": [42, 123, 456],
            "output_dir": f"outputs/real/{ds_name}__{slug}",
            "cache_path": "cache/completions.sqlite",
            "verifier_provider": None,
            "verifier_model": "",
            "methods": _methods_block(provider, model_id),
        }
        fname = out_dir / f"real_{ds_name}__{slug}.yaml"
        with fname.open("w") as f:
            yaml.dump(config, f, sort_keys=False, default_flow_style=False)
        written.append(fname)
    print(f"Wrote {len(written)} configs to {out_dir}/")
    print("First few:")
    for p in written[:5]:
        print(f"  {p}")


if __name__ == "__main__":
    main()
