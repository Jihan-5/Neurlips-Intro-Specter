"""Generate val-split configs that run IS at a sweep of τ_abstain values.

For each of the 4 IS-winning cells, we run IS at τ ∈ {0, 0.1, 0.2, 0.3, 0.5, 0.7}
on the val split. This gives us per-cell selective risk-coverage curves
WITH HELD-OUT τ TUNING (vs the post-hoc analysis in tau_abstain_sweep.py
which re-interprets test data).

The chosen τ_per_cell on val is then applied to the test split in a
companion runs (configs/tau_test/*) — that's the "calibrated abstention"
the paper claims.
"""

from __future__ import annotations

from pathlib import Path

import yaml


# 4 IS-winner × 1 representative dataset = 4 cells for τ calibration.
# We use the strongest IS-significant cells (deep-DAG QA where calibration matters).
CELLS = [
    ("musique_recon",   "musique_gemini_flash",    "openrouter", "google/gemini-2.5-flash"),
    ("musique_recon",   "musique_qwen_7b",         "openrouter", "qwen/qwen-2.5-7b-instruct"),
    ("musique_recon",   "musique_mistral_nemo",    "openrouter", "mistralai/mistral-nemo"),
    ("musique_recon",   "musique_deepseek_v3",     "together",   "deepseek-ai/DeepSeek-V3"),
]

TAU_VALUES = [0.0, 0.1, 0.2, 0.3, 0.5, 0.7]


def main() -> None:
    out_dir = Path("configs/tau_sweep")
    out_dir.mkdir(parents=True, exist_ok=True)

    for benchmark, dir_slug, provider, model in CELLS:
        methods = []
        for tau in TAU_VALUES:
            tau_label = f"tau{int(tau*100):03d}"  # tau000, tau010, tau020, ...
            methods.append({
                "name": f"intro_specter_{tau_label}",
                "provider_name": provider,
                "model": model,
                "temperature": 0.0,
                "extra": {
                    "tau_abstain": float(tau),
                    "n_counterfactual_trials": 1,
                },
            })
        # Run on VAL split for τ tuning.
        config = {
            "benchmark": benchmark,
            "split": "val",
            "n_examples": 100,
            "seeds": [0, 1, 2],
            "output_dir": f"outputs/tau_sweep/{dir_slug}_val",
            "cache_path": "cache/completions.sqlite",
            "verifier_provider": None,
            "verifier_model": "",
            "methods": methods,
        }
        fname = out_dir / f"tau_sweep_{dir_slug}_val.yaml"
        with fname.open("w") as f:
            yaml.dump(config, f, sort_keys=False, default_flow_style=False)
        print(f"  wrote {fname}")


if __name__ == "__main__":
    main()
