"""Generate add-on configs that run ONLY ReAct + ToT + SelfCheckGPT on
existing Profile-* benchmark output dirs, so the new baselines are
joined with the existing Direct/SR/Reflex/FullReg/IS data.

Targets Profile-MuSiQue and Profile-StrategyQA on the 4 IS-winner models.
"""

from __future__ import annotations

from pathlib import Path

import yaml


CELLS = [
    # (benchmark, model_slug_in_dir, provider, model)
    ("musique_recon",   "musique_deepseek_v3",     "together",   "deepseek-ai/DeepSeek-V3"),
    ("musique_recon",   "musique_mistral_nemo",    "openrouter", "mistralai/mistral-nemo"),
    ("musique_recon",   "musique_qwen_7b",         "openrouter", "qwen/qwen-2.5-7b-instruct"),
    ("musique_recon",   "musique_gemini_flash",    "openrouter", "google/gemini-2.5-flash"),
    ("strategyqa_recon","strategyqa_deepseek_v3",  "together",   "deepseek-ai/DeepSeek-V3"),
    ("strategyqa_recon","strategyqa_mistral_nemo", "openrouter", "mistralai/mistral-nemo"),
    ("strategyqa_recon","strategyqa_qwen_7b",      "openrouter", "qwen/qwen-2.5-7b-instruct"),
    ("strategyqa_recon","strategyqa_gemini_flash", "openrouter", "google/gemini-2.5-flash"),
]


def main() -> None:
    out_dir = Path("configs/addon")
    out_dir.mkdir(parents=True, exist_ok=True)
    for benchmark, dir_slug, provider, model in CELLS:
        config = {
            "benchmark": benchmark,
            "split": "test",
            "n_examples": 100,
            "seeds": [0, 1, 2],
            "output_dir": f"outputs/tier_b/{dir_slug}",
            "cache_path": "cache/completions.sqlite",
            "verifier_provider": None,
            "verifier_model": "",
            "methods": [
                {"name": "react",        "provider_name": provider, "model": model,
                 "extra": {"max_steps": 4}},
                {"name": "selfcheckgpt", "provider_name": provider, "model": model,
                 "extra": {"n_samples": 5, "sample_temperature": 1.0}},
                {"name": "tot",          "provider_name": provider, "model": model,
                 "extra": {"tot_candidates": 3, "tot_beam_width": 2,
                           "tot_max_depth": 4, "tot_temperature": 0.7}},
            ],
        }
        fname = out_dir / f"addon_{dir_slug}.yaml"
        with fname.open("w") as f:
            yaml.dump(config, f, sort_keys=False, default_flow_style=False)
        print(f"  wrote {fname}")


if __name__ == "__main__":
    main()
