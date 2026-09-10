#!/usr/bin/env python3
"""Aggregate the PersonalWAB rebuttal experiment.

Reads:   outputs/rebuttal/experiment_personalwab/{model}/{arm}.jsonl
Writes:  outputs/rebuttal/experiment_personalwab/SUMMARY.md

Per model x arm: success rate, mean rounds_used, token totals; plus paired
exact McNemar (intro_specter vs. each baseline arm) on rows paired by
(task_id, seed), using the campaign's own `intro_specter.metrics.stats.mcnemar`
(exact binomial on discordant pairs) and `paired_bootstrap_ci` for the delta CI.
All numbers come from the JSONL files actually on disk -- if a cell is
incomplete, its real row count is printed rather than hidden.

Additive-only: new file, touches nothing existing.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from intro_specter.metrics.stats import mcnemar, paired_bootstrap_ci  # noqa: E402

ROOT = Path(__file__).resolve().parents[1] / "outputs" / "rebuttal" / "experiment_personalwab"
# qwen-2.5-7b-together: same open weights as qwen-2.5-7b, Together serverless
# FP8 Turbo endpoint -- separate cell added when the OpenRouter key hit its
# $50 total limit mid-campaign (see orchestration/live_updates.md).
MODELS = ["mistral-nemo-12b", "qwen-2.5-7b", "llama-3.1-8b", "qwen-2.5-7b-together"]
ARMS = ["direct", "reflexion", "violation_reprompt", "iter_vrp", "intro_specter"]
BASELINE_ARMS = [a for a in ARMS if a != "intro_specter"]

# $/M tokens (input, output), OpenRouter list prices as of campaign start --
# used only for the indicative cost column, clearly labeled as estimates.
PRICES = {
    "mistral-nemo-12b": (0.02, 0.04),
    "qwen-2.5-7b": (0.04, 0.10),
    "llama-3.1-8b": (0.02, 0.03),
    "qwen-2.5-7b-together": (0.30, 0.30),  # Together Qwen2.5-7B-Turbo list price
}


def load_rows(model: str, arm: str) -> dict[tuple[str, int], dict]:
    """Last-write-wins dedup on (task_id, seed), matching the runner's resume key."""
    path = ROOT / model / f"{arm}.jsonl"
    rows: dict[tuple[str, int], dict] = {}
    if not path.exists():
        return rows
    for line in path.open():
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        rows[(r["task_id"], r["seed"])] = r
    return rows


def main() -> None:
    lines: list[str] = []
    lines.append("# PersonalWAB (WWW'25) single-turn recommendation -- rebuttal experiment\n")
    lines.append(
        "Task: single-turn personalized recommendation on real PersonalWAB user "
        "profiles/histories (757-row test recommend split, 60 examples x seeds 0,1,2 "
        "per model, bench_seed=42). Success = mechanical ASIN-containment hit@1 "
        "(the ground-truth item the user genuinely interacted with; PersonalWAB's "
        "own containment criterion). All counts below are read from the JSONL "
        "files on disk.\n")

    for model in MODELS:
        lines.append(f"\n## {model}\n")
        per_arm = {arm: load_rows(model, arm) for arm in ARMS}

        lines.append("| arm | n rows | success rate | mean rounds_used | tokens in | tokens out | est. cost ($) |")
        lines.append("|---|---|---|---|---|---|---|")
        for arm in ARMS:
            rows = per_arm[arm]
            n = len(rows)
            if n == 0:
                lines.append(f"| {arm} | 0 | -- | -- | -- | -- | -- |")
                continue
            succ = sum(1 for r in rows.values() if r["success"])
            rounds = sum(r.get("rounds_used", 1) for r in rows.values()) / n
            tin = sum(r.get("tokens_input", 0) for r in rows.values())
            tout = sum(r.get("tokens_output", 0) for r in rows.values())
            pi, po = PRICES.get(model, (0.0, 0.0))
            cost = tin / 1e6 * pi + tout / 1e6 * po
            lines.append(
                f"| {arm} | {n} | {succ}/{n} = {succ / n:.3f} | {rounds:.2f} "
                f"| {tin:,} | {tout:,} | {cost:.3f} |")

        is_rows = per_arm["intro_specter"]
        if is_rows:
            lines.append("\nPaired exact McNemar, intro_specter vs. baseline "
                         "(paired on (task_id, seed); delta = IS - baseline, "
                         "percentage points, with 95% paired-bootstrap CI):\n")
            lines.append("| baseline | n paired | IS wins / baseline wins (discordant) | delta (pp) [95% CI] | McNemar p |")
            lines.append("|---|---|---|---|---|")
            for arm in BASELINE_ARMS:
                bl_rows = per_arm[arm]
                keys = sorted(set(is_rows) & set(bl_rows))
                if not keys:
                    lines.append(f"| {arm} | 0 | -- | -- | -- |")
                    continue
                a = [bool(bl_rows[k]["success"]) for k in keys]   # baseline
                b = [bool(is_rows[k]["success"]) for k in keys]   # intro_specter
                is_wins = sum(1 for x, y in zip(a, b) if y and not x)
                bl_wins = sum(1 for x, y in zip(a, b) if x and not y)
                test = mcnemar(a, b)
                ci = paired_bootstrap_ci([float(x) for x in a], [float(y) for y in b])
                lines.append(
                    f"| {arm} | {len(keys)} | {is_wins} / {bl_wins} "
                    f"| {ci.point * 100:+.1f} [{ci.low * 100:+.1f}, {ci.high * 100:+.1f}] "
                    f"| {test.pvalue:.4f} |")

    out = ROOT / "SUMMARY.md"
    out.write_text("\n".join(lines) + "\n")
    print(f"wrote {out}")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
