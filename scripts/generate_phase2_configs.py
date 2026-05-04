"""Generate add-on + new-benchmark configs for Phase 2:

1. Real-HotpotQA add-on: 4 IS-winner cells × {ToT, SelfCheckGPT}
   (existing dirs already have direct/SR/Reflex/FR/ReAct/detection_only/IS).
2. Profile-Travel add-on: 8 LLMs × {ReAct, ToT, SelfCheckGPT}
   (existing dirs already have direct/SR/Reflex/FR/IS).
3. 2WikiMultiHopQA: 6 LLMs × 8 methods (new).
4. LongMemEval: 6 LLMs × 8 methods (new).
"""

from __future__ import annotations

from pathlib import Path

import yaml


# Provider × model_id mapping for the 6+ models we use.
MODELS_OR = {
    "llama-3.1-8b":     ("openrouter", "meta-llama/llama-3.1-8b-instruct"),
    "mistral-nemo-12b": ("openrouter", "mistralai/mistral-nemo"),
    "qwen-2.5-7b":      ("openrouter", "qwen/qwen-2.5-7b-instruct"),
    "gemini-2.5-flash": ("openrouter", "google/gemini-2.5-flash"),
}
MODELS_TOG = {
    "llama-3.3-70b":  ("together", "meta-llama/Llama-3.3-70B-Instruct-Turbo"),
    "deepseek-v3":    ("together", "deepseek-ai/DeepSeek-V3"),
    "deepseek-v3.1":  ("together", "deepseek-ai/DeepSeek-V3.1"),
    "gpt-oss-20b":    ("together", "openai/gpt-oss-20b"),
}
ALL_MODELS = {**MODELS_OR, **MODELS_TOG}

ADDON_QA_METHODS = [
    {"name": "tot",          "extra": {"tot_candidates": 3, "tot_beam_width": 2,
                                         "tot_max_depth": 4, "tot_temperature": 0.7}},
    {"name": "selfcheckgpt", "extra": {"n_samples": 5, "sample_temperature": 1.0}},
]
ADDON_TRAVEL_METHODS = [
    {"name": "react",        "extra": {"max_steps": 4}},
    {"name": "tot",          "extra": {"tot_candidates": 3, "tot_beam_width": 2,
                                         "tot_max_depth": 4, "tot_temperature": 0.7}},
    {"name": "selfcheckgpt", "extra": {"n_samples": 5, "sample_temperature": 1.0}},
]
FULL_METHODS = [
    {"name": "direct"},
    {"name": "self_refine"},
    {"name": "reflexion",    "extra": {"max_trials": 2}},
    {"name": "full_regen",   "extra": {"max_attempts": 1}},
    {"name": "react",        "extra": {"max_steps": 4}},
    {"name": "selfcheckgpt", "extra": {"n_samples": 5, "sample_temperature": 1.0}},
    {"name": "tot",          "extra": {"tot_candidates": 3, "tot_beam_width": 2,
                                         "tot_max_depth": 4, "tot_temperature": 0.7}},
    {"name": "intro_specter_llm",
     "temperature": 0.0, "extra": {"tau_abstain": 0.0, "n_counterfactual_trials": 1}},
]


def _methods_block(methods_template: list[dict], provider: str, model: str,
                    is_full: bool = False) -> list[dict]:
    out = []
    for m in methods_template:
        block = {"name": m["name"], "provider_name": provider, "model": model}
        if "temperature" in m:
            block["temperature"] = m["temperature"]
        if "extra" in m:
            block["extra"] = m["extra"]
        out.append(block)
    return out


def main() -> None:
    out_addon = Path("configs/addon_phase2")
    out_addon.mkdir(parents=True, exist_ok=True)
    out_real = Path("configs/real")
    out_real.mkdir(parents=True, exist_ok=True)

    # 1. Real-HotpotQA add-on (4 IS-winner cells)
    HOTPOTQA_CELLS = {
        "deepseek-v3":     "outputs/tier_b/real_hotpotqa_deepseek_v3",
        "mistral-nemo-12b":"outputs/tier_b/real_hotpotqa_mistral_nemo",
        "qwen-2.5-7b":     "outputs/tier_b/real_hotpotqa_qwen_7b",
        "gemini-2.5-flash":"outputs/tier_b/real_hotpotqa_gemini_flash",
    }
    for slug, dir_path in HOTPOTQA_CELLS.items():
        provider, model = ALL_MODELS[slug]
        config = {
            "benchmark": "hotpotqa_real",
            "split": "test",
            "n_examples": 100,
            "seeds": [0, 1, 2],
            "output_dir": dir_path,
            "cache_path": "cache/completions.sqlite",
            "verifier_provider": None, "verifier_model": "",
            "methods": _methods_block(ADDON_QA_METHODS, provider, model),
        }
        path = out_addon / f"addon_real_hotpotqa__{slug}.yaml"
        path.write_text(yaml.dump(config, sort_keys=False, default_flow_style=False))
        print(f"  {path}")

    # 2. Profile-Travel add-on (8 LLMs)
    TRAVEL_CELLS = {
        "llama-3.1-8b":    "outputs/tier_a/travel_llama3_8b",
        "llama-3.3-70b":   "outputs/tier_a/travel_llama",
        "deepseek-v3":     "outputs/tier_a/travel_deepseek",
        "deepseek-v3.1":   "outputs/tier_a/travel_deepseek_v31",
        "mistral-nemo-12b":"outputs/tier_a/travel_mistral7b",
        "qwen-2.5-7b":     "outputs/tier_a/travel_qwen7b",
        "gemini-2.5-flash":"outputs/tier_a/travel_gemini_flash",
        "gpt-oss-20b":     "outputs/tier_a/travel_gptoss20b",
    }
    for slug, dir_path in TRAVEL_CELLS.items():
        provider, model = ALL_MODELS[slug]
        config = {
            "benchmark": "travelplanner_recon",
            "split": "test",
            "n_examples": 100,
            "seeds": [0, 1, 2],
            "output_dir": dir_path,
            "cache_path": "cache/completions.sqlite",
            "verifier_provider": None, "verifier_model": "",
            "methods": _methods_block(ADDON_TRAVEL_METHODS, provider, model),
        }
        path = out_addon / f"addon_travel__{slug}.yaml"
        path.write_text(yaml.dump(config, sort_keys=False, default_flow_style=False))
        print(f"  {path}")

    # 3. 2WikiMultiHopQA: full 8-method on 6 LLMs
    PHASE2_LLMS = ["llama-3.1-8b", "llama-3.3-70b", "deepseek-v3",
                    "mistral-nemo-12b", "qwen-2.5-7b", "gemini-2.5-flash"]
    for slug in PHASE2_LLMS:
        provider, model = ALL_MODELS[slug]
        config = {
            "benchmark": "twowiki_real",
            "split": "all",
            "n_examples": 60,
            "seeds": [42],
            "output_dir": f"outputs/real/twowiki_real__{slug}",
            "cache_path": "cache/completions.sqlite",
            "verifier_provider": None, "verifier_model": "",
            "methods": _methods_block(FULL_METHODS, provider, model),
        }
        path = out_real / f"real_2wiki__{slug}.yaml"
        path.write_text(yaml.dump(config, sort_keys=False, default_flow_style=False))
        print(f"  {path}")

    # 4. LongMemEval: full 8-method on 6 LLMs
    for slug in PHASE2_LLMS:
        provider, model = ALL_MODELS[slug]
        config = {
            "benchmark": "longmemeval_real",
            "split": "all",
            "n_examples": 60,
            "seeds": [42],
            "output_dir": f"outputs/real/longmemeval_real__{slug}",
            "cache_path": "cache/completions.sqlite",
            "verifier_provider": None, "verifier_model": "",
            "methods": _methods_block(FULL_METHODS, provider, model),
        }
        path = out_real / f"real_longmemeval__{slug}.yaml"
        path.write_text(yaml.dump(config, sort_keys=False, default_flow_style=False))
        print(f"  {path}")


if __name__ == "__main__":
    main()
