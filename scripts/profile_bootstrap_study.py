#!/usr/bin/env python3
"""Profile bootstrap study (rebuttal campaign).

Reviewers objected that the main results might overfit the ONE profile draw
that `inject_profile(task_id, seed)` happens to produce per example. This
study re-draws every RELEVANT constraint span N times per example (default
100 variants), optionally paraphrases each redrawn span with a cheap LLM
(meaning-preserving), and runs three arms — direct (the prime), reflexion,
intro_specter — against every variant, measuring the distribution of
outcomes over profile draws. Aggregate with
scripts/aggregate_profile_bootstrap.py.

Ground-truth regeneration (the crux of correctness): in all five real
loaders wired here, the ONLY rule component derived from the profile is
`condition_meta["banned_substrings"]`, computed by scanning constraint
texts for the phrase "english only" (e.g. benchmarks/truthfulqa_real.py
lines 177-180; the factual inputs — correct/incorrect answers, gold answer
+ aliases — are profile-independent). So a variant's rules are regenerated
exactly the way the loader built them: recompute banned_substrings from the
variant's CANONICAL (pre-paraphrase) template texts with the loader's own
per-dataset token list, splice the variant constraint dicts into a copy of
condition_meta, and call the loader's own `_make_rule(new_meta)`. The
paraphrased surface form never feeds the rule: ground truth derives from
the canonical template text (the constraint's meaning), while the
paraphrase is what the agent sees in the profile spans and task prompt.
The task-brief fallback (restricting re-draws to text-templated rules) is
therefore unnecessary — every relevant span is safely re-drawable.

Determinism: the re-draw RNG is seeded per (task_id, variant_idx) via
sha256, mirroring rebuttal_experiment_a._corruption_seed; paraphrase calls
are seeded per (task_id, variant_idx, span_id) and cached in the shared
SQLite completion cache. Generation seed for all arms is fixed at 0 — the
variation axis of this study is the profile draw, not the sampling seed.

Usage (smoke = 2 examples x 3 variants; add --dry-run for a zero-API-call
check of variant generation + rule regeneration only):

    python3 scripts/profile_bootstrap_study.py \\
        --dataset truthfulqa_real --model llama-3.1-8b --smoke --dry-run
"""

from __future__ import annotations

import argparse
import fcntl
import functools
import hashlib
import importlib.util
import json
import random
import sqlite3
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from intro_specter.benchmarks import (  # noqa: E402
    hotpotqa_real as _hpq_mod,
    longmemeval_real as _lme_mod,
    musique_real as _msq_mod,
    truthfulqa_real as _tqa_mod,
    twowiki_real as _twk_mod,
)
from intro_specter.benchmarks.base import BenchmarkExample  # noqa: E402
from intro_specter.models import SQLiteCache, build_provider  # noqa: E402
from intro_specter.models.base import CompletionResult  # noqa: E402
from intro_specter.profile_corruption import _same_family_pool  # noqa: E402
from intro_specter.schemas import Trajectory, TrajectoryStep  # noqa: E402


def _load_expa():
    """Import scripts/rebuttal_experiment_a.py as a module (it is a script,
    not a package member) so we reuse its registry/arm functions verbatim."""
    path = Path(__file__).resolve().parent / "rebuttal_experiment_a.py"
    spec = importlib.util.spec_from_file_location("rebuttal_experiment_a", path)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    sys.modules[spec.name] = mod  # type: ignore[union-attr]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


expa = _load_expa()

# Per-dataset banned-substring token lists, copied verbatim from each
# loader's "english only" branch (truthfulqa_real.py:180 uses the short
# 3-token list; the multi-hop/longmem loaders use the 5-token list).
_BANNED_TOKENS: dict[str, list[str]] = {
    "truthfulqa_real": ["hola ", "bonjour", "ciao "],
    "musique_real": ["hola ", "bonjour", "ciao ", "你好", "こんにちは"],
    "twowiki_real": ["hola ", "bonjour", "ciao ", "你好", "こんにちは"],
    "longmemeval_real": ["hola ", "bonjour", "ciao ", "你好", "こんにちは"],
    "hotpotqa_real": ["hola ", "bonjour", "ciao ", "你好", "こんにちは"],
}

# The loader whose _make_rule regenerates the variant's verifier rule.
_RULE_FACTORY: dict[str, Callable[[dict[str, Any]], Any]] = {
    "truthfulqa_real": _tqa_mod._make_rule,
    "musique_real": _msq_mod._make_rule,
    "twowiki_real": _twk_mod._make_rule,
    "longmemeval_real": _lme_mod._make_rule,
    "hotpotqa_real": _hpq_mod._make_rule,
}

ARMS = ("direct", "reflexion", "intro_specter")
GEN_SEED = 0  # fixed generation seed for all arms (see module docstring)

PARAPHRASE_SYSTEM = (
    "You rewrite user-profile constraint sentences. Rewrite the given sentence "
    "with different wording but EXACTLY the same meaning: every constraint "
    "value (diet, language, budget, format, expertise level, etc.) must stay "
    "identical — only the phrasing may change. Keep it one sentence, same "
    "language (English). Respond with JSON only: {\"paraphrase\": \"...\"}"
)


class ReadThroughCache:
    """Read a frozen base cache and write only to a shard-local delta cache."""

    def __init__(self, base: str | Path, delta: str | Path) -> None:
        self.base = Path(base)
        if not self.base.exists():
            raise FileNotFoundError(self.base)
        self.delta = SQLiteCache(delta)

    def get(self, key: str) -> CompletionResult | None:
        hit = self.delta.get(key)
        if hit is not None:
            return hit
        uri = self.base.resolve().as_uri() + "?mode=ro"
        with sqlite3.connect(uri, uri=True) as conn:
            row = conn.execute("SELECT payload FROM completions WHERE key = ?", (key,)).fetchone()
        if row is None:
            return None
        result = CompletionResult(**json.loads(row[0]))
        result.cache_hit = True
        return result

    def put(self, key: str, result: CompletionResult) -> None:
        self.delta.put(key, result)


def _variant_seed(task_id: str, variant_idx: int) -> int:
    h = hashlib.sha256(f"{task_id}|bootstrap|{variant_idx}".encode()).hexdigest()
    return int(h[:8], 16)


def _paraphrase_seed(task_id: str, variant_idx: int, span_id: str) -> int:
    h = hashlib.sha256(f"{task_id}|bootstrap|{variant_idx}|{span_id}".encode()).hexdigest()
    return int(h[:8], 16)


def _profile_hash(profile: Any) -> str:
    blob = json.dumps([(s.id, s.text, s.is_hard) for s in profile.spans], ensure_ascii=False)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def make_paraphraser(
    provider_name: str, model_id: str, cache: SQLiteCache | None
) -> Callable[[str, str, int, str], tuple[str, int, int]]:
    """Returns paraphrase(text, task_id, variant_idx, span_id) ->
    (surface_text, tokens_in, tokens_out). Falls back to the canonical text
    on empty/degenerate output so a flaky paraphrase can never corrupt a run."""
    provider = build_provider(provider_name, cache=cache)

    def paraphrase(text: str, task_id: str, variant_idx: int, span_id: str) -> tuple[str, int, int]:
        payload, completion = provider.complete_json(
            system=PARAPHRASE_SYSTEM,
            user=f"Sentence: {text}",
            model=model_id,
            temperature=0.7,
            seed=_paraphrase_seed(task_id, variant_idx, span_id),
            max_tokens=256,
        )
        out = str(payload.get("paraphrase") or "").strip()
        if not out or len(out) > 4 * max(len(text), 40):
            out = text
        return out, completion.tokens_input, completion.tokens_output

    return paraphrase


def make_variant(
    example: BenchmarkExample,
    dataset: str,
    variant_idx: int,
    paraphrase_fn: Callable[[str, str, int, str], tuple[str, int, int]] | None,
) -> tuple[BenchmarkExample, dict[str, Any]]:
    """Build variant `variant_idx` of `example`: re-draw every RELEVANT span
    from its same-category template pool (prob 1.0), optionally paraphrase the
    redrawn text, and regenerate the profile-derived rule from the CANONICAL
    template texts. Returns (variant_example, info) where info carries the
    redraw log, profile hash, and paraphrase token counts."""
    rng = random.Random(_variant_seed(example.task_id, variant_idx))
    cmeta = expa._constraint_meta(example)

    spans = list(example.profile.spans)
    old_constraints = example.task["condition_meta"]["profile_constraints"]
    new_constraints = [dict(c) for c in old_constraints]
    canonical_texts = [c["text"] for c in new_constraints]  # pre-paraphrase ground truth
    redrawn: list[dict[str, Any]] = []
    para_in = para_out = 0

    for i, span in enumerate(spans):
        meta = cmeta.get(span.id)
        if not meta or not meta["relevant"]:
            continue
        old_text = span.text
        choice = rng.choice(_same_family_pool(meta["category"], old_text))
        surface = choice.text
        if paraphrase_fn is not None:
            surface, t_in, t_out = paraphrase_fn(choice.text, example.task_id, variant_idx, span.id)
            para_in += t_in
            para_out += t_out
        spans[i] = span.model_copy(update={"text": surface, "is_hard": choice.type == "hard"})
        for j, c in enumerate(new_constraints):
            if c["id"] == span.id:
                # `relevant`/`category` keep the SLOT's original values: the
                # slot stays a relevant constraint of that family even if the
                # drawn template object is tagged differently in the bank.
                c["text"] = surface
                c["type"] = choice.type
                canonical_texts[j] = choice.text
        redrawn.append({
            "span_id": span.id,
            "old_text": old_text,
            "canonical_text": choice.text,
            "surface_text": surface,
        })

    variant_profile = example.profile.model_copy(update={"spans": spans}, deep=True)

    # --- rule regeneration (see module docstring) ---
    banned: list[str] = []
    for t in canonical_texts:
        if "english only" in t.lower():
            banned += _BANNED_TOKENS[dataset]
    new_meta = dict(example.task["condition_meta"])
    new_meta["banned_substrings"] = banned
    new_meta["profile_constraints"] = new_constraints
    new_rule = _RULE_FACTORY[dataset](new_meta)

    # --- prompt rebuild: all five loaders render constraints as "- {text}"
    # lines, so a 1:1 line substitution reproduces the loader's prompt. ---
    prompt = example.task["prompt"]
    for r in redrawn:
        needle = f"- {r['old_text']}"
        if prompt.count(needle) != 1:
            print(f"[WARN] {example.task_id} v{variant_idx}: prompt line {needle!r} "
                  f"matched {prompt.count(needle)} times; replacing first occurrence",
                  file=sys.stderr)
        prompt = prompt.replace(needle, f"- {r['surface_text']}", 1)
    new_task = dict(example.task)
    new_task["prompt"] = prompt
    new_task["condition_meta"] = new_meta

    variant_example = replace(example, profile=variant_profile, task=new_task, rules=[new_rule])
    info = {
        "redrawn": redrawn,
        "profile_hash": _profile_hash(variant_profile),
        "banned_substrings": banned,
        "paraphrase_tokens_input": para_in,
        "paraphrase_tokens_output": para_out,
    }
    return variant_example, info


def _dry_run_check(variant_example: BenchmarkExample, info: dict[str, Any]) -> None:
    """Sanity-run the regenerated rule on a dummy trajectory (no provider)."""
    dummy = Trajectory(
        task_id=variant_example.task_id,
        steps=[TrajectoryStep(step_id=1, kind="output", text="dummy")],  # type: ignore[arg-type]
        final_output="dummy answer bonjour",
    )
    ok = expa._true_success(variant_example, dummy)
    print(f"  {variant_example.task_id} hash={info['profile_hash']} "
          f"redrawn={[r['span_id'] for r in info['redrawn']]} "
          f"banned={info['banned_substrings']} dummy_rule_pass={ok}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset", default="truthfulqa_real", choices=list(_RULE_FACTORY))
    ap.add_argument("--model", required=True, choices=list(expa.MODEL_TABLE))
    ap.add_argument("--n-variants", type=int, default=100)
    ap.add_argument("--n-examples", type=int, default=None)
    ap.add_argument("--paraphrase", action=argparse.BooleanOptionalAction, default=True,
                    help="LLM-paraphrase each redrawn span (meaning-preserving); "
                         "--no-paraphrase uses raw template text")
    ap.add_argument("--paraphrase-model", default="llama-3.1-8b", choices=list(expa.MODEL_TABLE),
                    help="cheap model for the paraphrase call")
    ap.add_argument("--tau-abstain", type=float, default=0.0,
                    help="IS abstain threshold; the study protocol fixes 0.0 (clean-run match)")
    ap.add_argument("--cache-path", default="cache/completions.sqlite")
    ap.add_argument("--cache-read-only-base",
                    help="frozen cache consulted before shard-local --cache-path")
    ap.add_argument("--output-dir", default="outputs/rebuttal/profile_bootstrap")
    ap.add_argument("--output-file", help="explicit shard-local JSONL output path")
    ap.add_argument("--base-output", help="frozen base JSONL whose keys are already complete")
    ap.add_argument("--assignment-file",
                    help="JSON list of disjoint {task_id, variant_idx, arms} units")
    ap.add_argument("--conflict-file", help="A1 conflict-key JSON used for recovered labels")
    ap.add_argument("--smoke", action="store_true", help="2 examples x 3 variants, then stop")
    ap.add_argument("--dry-run", action="store_true",
                    help="generate variants + regenerate rules only; zero provider calls "
                         "(paraphrase is skipped), nothing written")
    args = ap.parse_args()

    if args.smoke:
        n_examples, n_variants = 2, 3
    else:
        n_examples = args.n_examples or expa.DATASET_REGISTRY[args.dataset]["n_examples"]
        n_variants = args.n_variants

    provider_name, model_id = expa.MODEL_TABLE[args.model]
    cache = (ReadThroughCache(args.cache_read_only_base, args.cache_path)
             if args.cache_read_only_base and not args.dry_run
             else SQLiteCache(args.cache_path) if not args.dry_run else None)

    paraphrase_fn = None
    if args.paraphrase and not args.dry_run:
        p_provider, p_model = expa.MODEL_TABLE[args.paraphrase_model]
        paraphrase_fn = make_paraphraser(p_provider, p_model, cache)

    examples = expa._load_examples(args.dataset, n_examples)
    print(f"Loaded {len(examples)} examples for {args.dataset}, n_variants={n_variants}, "
          f"paraphrase={args.paraphrase and not args.dry_run}, dry_run={args.dry_run}")

    if args.dry_run:
        for example in examples:
            for v in range(n_variants):
                variant_example, info = make_variant(example, args.dataset, v, None)
                _dry_run_check(variant_example, info)
        print("Dry run complete: variant generation + rule regeneration OK, no provider calls made.")
        return

    out_dir = (Path(args.output_file).parent if args.output_file
               else Path(args.output_dir) / f"{args.dataset}__{args.model}")
    out_dir.mkdir(parents=True, exist_ok=True)
    # One cell has exactly one writer. A mistaken second launch fails before
    # it can append duplicate rows.
    out_path = Path(args.output_file) if args.output_file else out_dir / "variants.jsonl"
    writer_lock = out_path.with_suffix(out_path.suffix + ".writer.lock").open("a")
    try:
        fcntl.flock(writer_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        raise SystemExit(f"writer already active for {out_dir.name}") from exc
    # Amendment A1: keys discarded because multiple historical writers
    # produced conflicting objects are rerun under the single-writer lock and
    # explicitly labeled.  The preparation manifest is immutable audit input;
    # ordinary logically-missing rows remain recovered=false.
    recovered_keys: set[tuple[str, int, str]] = set()
    recovered_path = (Path(args.conflict_file) if args.conflict_file
                      else out_dir / "a1_conflict_keys.json")
    if recovered_path.exists():
        for item in json.loads(recovered_path.read_text()):
            recovered_keys.add((item["task_id"], int(item["variant_idx"]), item["arm"]))

    done: set[tuple[str, int, str]] = set()
    done_sources = [out_path]
    if args.base_output:
        done_sources.insert(0, Path(args.base_output))
    for done_path in done_sources:
        if not done_path.exists():
            continue
        for line in done_path.open():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                # Preserve an unterminated tail after a killed append. The
                # integrity report exposes it and the missing key can resume.
                continue
            done.add((row["task_id"], row["variant_idx"], row["arm"]))
    if done:
        print(f"Resuming: {len(done)} (task_id, variant_idx, arm) rows already present, skipped.")

    assignments: dict[tuple[str, int], set[str]] | None = None
    if args.assignment_file:
        assignments = {}
        for item in json.loads(Path(args.assignment_file).read_text()):
            unit = (str(item["task_id"]), int(item["variant_idx"]))
            if unit in assignments:
                raise SystemExit(f"duplicate assigned unit: {unit}")
            arms = {str(arm) for arm in item["arms"]}
            if not arms or not arms <= set(ARMS):
                raise SystemExit(f"invalid assigned arms for {unit}: {sorted(arms)}")
            assignments[unit] = arms

    out_f = out_path.open("a")
    total_in = total_out = para_total = n_rows = n_errors = 0

    for example in examples:
        for v in range(n_variants):
            if assignments is not None and (example.task_id, v) not in assignments:
                continue
            allowed = assignments[(example.task_id, v)] if assignments is not None else set(ARMS)
            pending = [a for a in ARMS
                       if a in allowed and (example.task_id, v, a) not in done]
            if not pending:
                continue

            variant_example, info = make_variant(example, args.dataset, v, paraphrase_fn)
            para_total += info["paraphrase_tokens_input"] + info["paraphrase_tokens_output"]

            try:
                primed, prime_in, prime_out = expa._with_retry(
                    lambda: expa._prime_trajectory(
                        variant_example, provider_name=provider_name, model=model_id,
                        seed=GEN_SEED, cache=cache,
                    ),
                    label=f"prime task={example.task_id} variant={v}",
                )
            except Exception as e:  # pragma: no cover
                print(f"[ERROR] prime failed task={example.task_id} variant={v}: {e}",
                      file=sys.stderr)
                n_errors += 1
                continue

            arm_runners: dict[str, Callable[[], dict[str, Any]]] = {
                "direct": lambda: {
                    "final_trajectory": primed,
                    "method_believed_success": None,
                    "tokens_input": 0, "tokens_output": 0,
                    "abstained": None, "meta_summary": {},
                },
                "reflexion": lambda: expa._run_reflexion_arm(
                    variant_example, primed, provider_name=provider_name,
                    model=model_id, seed=GEN_SEED, cache=cache,
                ),
                "intro_specter": lambda: expa._run_intro_specter_arm(
                    variant_example, primed, provider_name=provider_name,
                    model=model_id, seed=GEN_SEED, cache=cache,
                    tau_abstain=args.tau_abstain,
                ),
            }

            for arm in pending:
                try:
                    arm_out = expa._with_retry(
                        arm_runners[arm],
                        label=f"{arm} task={example.task_id} variant={v}",
                    )
                except Exception as e:  # pragma: no cover
                    print(f"[ERROR] {arm} failed task={example.task_id} variant={v}: {e}",
                          file=sys.stderr)
                    n_errors += 1
                    continue

                # True success is scored against the VARIANT's regenerated
                # rules + profile: the variant IS the ground truth here (a
                # legitimate re-draw), unlike ExpA's corruption protocol.
                true_success = expa._true_success(variant_example, arm_out["final_trajectory"])
                tokens_input = arm_out["tokens_input"] + prime_in
                tokens_output = arm_out["tokens_output"] + prime_out
                row = {
                    "task_id": example.task_id,
                    "variant_idx": v,
                    "arm": arm,
                    "true_success": true_success,
                    "method_believed_success": arm_out["method_believed_success"],
                    "tokens_input": tokens_input,
                    "tokens_output": tokens_output,
                    "abstained": arm_out["abstained"],
                    "profile_hash": info["profile_hash"],
                    "redrawn_span_ids": [r["span_id"] for r in info["redrawn"]],
                    "banned_substrings": info["banned_substrings"],
                    "paraphrased": paraphrase_fn is not None,
                    "meta_summary": arm_out["meta_summary"],
                    "recovered": (example.task_id, v, arm) in recovered_keys,
                }
                out_f.write(json.dumps(row, default=str) + "\n")
                out_f.flush()
                total_in += tokens_input
                total_out += tokens_output
                n_rows += 1
                print(f"  {example.task_id} v={v} arm={arm}: true_success={true_success} "
                      f"hash={info['profile_hash']} tokens=({tokens_input},{tokens_output})")

    out_f.close()
    print("\n--- run summary ---")
    print(f"rows written: {n_rows}  errors: {n_errors}")
    print(f"total tokens_input={total_in}  tokens_output={total_out}  "
          f"paraphrase_tokens={para_total}  grand_total={total_in + total_out + para_total}")


if __name__ == "__main__":
    main()
