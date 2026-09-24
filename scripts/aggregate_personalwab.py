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
import argparse
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


def load_rows(model: str, arm: str, root: Path = ROOT, strict: bool = False) -> dict[tuple[str, int], dict]:
    """Last-write-wins dedup on (task_id, seed), matching the runner's resume key."""
    path = root / model / f"{arm}.jsonl"
    rows: dict[tuple[str, int], dict] = {}
    if not path.exists():
        return rows
    for line in path.open():
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        key = (r["task_id"], r["seed"])
        if strict and (key in rows or r.get("arm") != arm or type(r.get("success")) is not bool):
            raise ValueError(f"Duplicate or invalid row in {path}: {key}")
        rows[key] = r
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT,
                        help="experiment output root (default: historical contaminated root)")
    parser.add_argument("--models", default=",".join(MODELS),
                        help="comma-separated model directory names")
    parser.add_argument("--output", type=Path, default=None,
                        help="summary path (default: ROOT/SUMMARY.md)")
    parser.add_argument("--pooled-only", action="store_true",
                        help="pool pairs matched within model without regenerating per-model tables")
    parser.add_argument("--require-complete", action="store_true",
                        help="require 60 tasks x seeds 0,1,2 in every cell, identical keys, no duplicates")
    args = parser.parse_args()
    root = args.root
    models = [m.strip() for m in args.models.split(",") if m.strip()]
    out = args.output or root / "SUMMARY.md"

    if not models or len(models) != len(set(models)):
        raise ValueError("Models must be nonempty and unique")
    if args.require_complete:
        reference = None
        for model in models:
            for arm in ARMS:
                rows = load_rows(model, arm, root, strict=True)
                keys = set(rows)
                tasks = {t for t, _ in keys}
                expected = {(t, seed) for t in tasks for seed in (0, 1, 2)}
                if len(tasks) != 60 or keys != expected:
                    raise ValueError(f"Incomplete task/seed coverage: {model}/{arm}")
                if reference is not None and keys != reference:
                    raise ValueError(f"Different task/seed sets: {model}/{arm}")
                reference = keys

    lines: list[str] = []
    lines.append("# PersonalWAB (WWW'25) single-turn recommendation -- rebuttal experiment\n")
    lines.append(
        "Task: single-turn personalized recommendation on real PersonalWAB user "
        "profiles/histories (757-row test recommend split, 60 examples x seeds 0,1,2 "
        "per model, bench_seed=42). Success = mechanical ASIN-containment hit@1 "
        "(the ground-truth item the user genuinely interacted with; PersonalWAB's "
        "own containment criterion). All counts below are read from the JSONL "
        "files on disk.\n")

    if args.pooled_only:
        lines.append("\n## Pooled requested models\n")
        lines.append("Requested models: " + ", ".join(models) + ".\n")
        pooled = {arm: {} for arm in ARMS}
        lines.append("| model | " + " | ".join(ARMS) + " |")
        lines.append("|---|" + "---|" * len(ARMS))
        for model in models:
            per_arm = {arm: load_rows(model, arm, root) for arm in ARMS}
            lines.append("| " + model + " | " + " | ".join(str(len(per_arm[arm])) for arm in ARMS) + " |")
            for arm, rows in per_arm.items():
                pooled[arm].update({(model, *key): row for key, row in rows.items()})
        lines.append("\nZero-row cells contribute no observations; this is not a complete requested grid if any cell is short.\n")
        lines.append("| arm | rows | successes | success rate |")
        lines.append("|---|---|---|---|")
        for arm, rows in pooled.items():
            n = len(rows)
            successes = sum(bool(row["success"]) for row in rows.values())
            rate = f"{successes / n:.6f}" if n else "--"
            lines.append(f"| {arm} | {n} | {successes} | {rate} |")
        lines.append("\nPairs are matched within model on (task_id, seed), then pooled; delta = IS − baseline.\n")
        lines.append("| baseline | pairs | IS wins / baseline wins | delta (pp) [95% paired-bootstrap CI] | exact McNemar p |")
        lines.append("|---|---|---|---|---|")
        for arm in BASELINE_ARMS:
            keys = sorted(set(pooled["intro_specter"]) & set(pooled[arm]))
            if not keys:
                lines.append(f"| {arm} | 0 | -- | -- | -- |")
                continue
            baseline = [bool(pooled[arm][key]["success"]) for key in keys]
            method = [bool(pooled["intro_specter"][key]["success"]) for key in keys]
            wins = sum(y and not x for x, y in zip(baseline, method))
            losses = sum(x and not y for x, y in zip(baseline, method))
            test = mcnemar(baseline, method)
            ci = paired_bootstrap_ci(list(map(float, baseline)), list(map(float, method)))
            lines.append(f"| {arm} | {len(keys)} | {wins} / {losses} | {ci.point * 100:+.6f} [{ci.low * 100:+.6f}, {ci.high * 100:+.6f}] | {test.pvalue:.8g} |")

    for model in ([] if args.pooled_only else models):
        lines.append(f"\n## {model}\n")
        per_arm = {arm: load_rows(model, arm, root) for arm in ARMS}

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
                    f"| {ci.point * 100:+.6f} [{ci.low * 100:+.6f}, {ci.high * 100:+.6f}] "
                    f"| {test.pvalue:.8g} |")

    out.write_text("\n".join(lines) + "\n")
    print(f"wrote {out}")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
