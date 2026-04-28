# Token Accounting

Every `RunResult` row records `tokens_input` and `tokens_output`. This document
states **exactly which LLM calls are summed into those numbers**, per method,
so the headline efficiency comparison ("X% fewer regeneration tokens than Y")
is unambiguous.

The accounting policy is **per-task**, not per-repair-attempt: the totals on
each row are the sum of every LLM call the method made for that task,
including any retried / refused / abstained attempts. Each call's token count
comes from the provider SDK (`usage.input_tokens` / `usage.output_tokens` for
Anthropic; `usage.prompt_tokens` / `usage.completion_tokens` for OpenAI).

| Method | LLM calls counted per task | Notes |
|---|---|---|
| `direct` | 0 | Pass-through; the verifier is the only call, and verifier tokens are *not* counted in this column (see "Verifier tokens" below). |
| `self_refine` | one critique-and-revise call per round, up to `n_rounds`; halts early on verifier pass | Default `n_rounds = 1`. |
| `reflexion` | one reflection + one retry per trial, up to `max_trials`; halts on pass | Default `max_trials = 2`, so up to 4 LLM calls. |
| `full_regen` | benchmark-supplied `regenerate_fn` (synthetic returns deterministic counts; natural benchmarks call the agent prompt) | The synthetic benchmark uses `n_steps × 100` input tokens and `n_steps × 33` output tokens as a stand-in cost. |
| `oracle_repair` | 0 | Receives gold `fault_node_id`; only re-executes via the deterministic `rerun_fn`. Tokens for the rerun are 0 because the synthetic rerun_fn is Python; for natural benchmarks, the rerun's LLM tokens *are* counted. |
| `oracle_detector` | counterfactual_sampler.sample × |candidates|; rerun if executed | The verifier is bypassed (gold violations); attribution and repair otherwise identical to `intro_specter`. |
| `intro_specter` (rule-based sampler) | 0 on the synthetic Tier-C — the sampler is deterministic Python | The verifier is also rule-based; no LLM calls are made. |
| `intro_specter_llm` | `extraction` (1 if no `gold_dag`) + `verifier` (1 if `provider` set) + `counterfactual` (1 per candidate) + `reexecution` (1) | This is the natural-benchmark pipeline. Each of those four prompts is a separate LLM call. |

## Per-stage breakdown for `intro_specter_llm`

For one task, in the worst case (no gold DAG, LLM verifier, K candidate
ancestors of violated steps):

```
total_calls = 1 (build_assumption_dag)
            + 1 (verifier)
            + K (counterfactual_sampler.sample, one per candidate)
            + 1 (rerun_downstream_subgraph_llm)        # only if status="repaired"
```

If the verifier passes on the original trajectory (`status="accepted"`), only
the extraction + verifier calls are made, and the run is essentially a
detection no-op.

If `status="abstain_or_full_regenerate"`, the rerun call is *not* issued;
the stage stops at attribution.

## Verifier tokens

The verifier's LLM tokens are recorded in the per-method `meta.stages` list
(`stage: "verifier"` entry, fields `llm_tokens_input` / `llm_tokens_output`)
but **are not summed into the headline `tokens_input` / `tokens_output`**
columns by default. Rationale: the verifier is the same component for every
method that uses it (Self-Refine, Reflexion, Intro-Specter), so including it
would double-count when comparing methods that share a verifier. To compare
*against* a verifier-token-aware total, sum
`tokens_input + extra.meta_summary['verifier'].llm_tokens_input`.

## What "regeneration tokens" means in the §5 efficiency claim

The claim form "Intro-Specter uses N% fewer regeneration tokens than
full_regen" specifically compares the **rerun stage** of Intro-Specter
against the full agent regeneration of `full_regen`:

```
intro_specter_regen_tokens = sum over tasks of (rerun stage tokens only)
full_regen_tokens          = sum over tasks of (full agent prompt tokens)
```

It does **not** include the extraction, verifier, or counterfactual stages of
Intro-Specter. Those costs are reported separately as "attribution overhead"
in the same table so that net efficiency is honestly visible.

When writing the §5 sentence, distinguish:

* **Total** tokens (everything the method spends on the task).
* **Regeneration** tokens (rerun stage only).

If only one is reported, label which.

## Caching

The SQLite prompt cache (`cache/completions.sqlite`) deduplicates identical
`(provider, model, system, user, temperature, seed, max_tokens)` calls. A
cache hit returns the original `CompletionResult` with `cache_hit=True`; the
**original** call's token counts are kept in the per-row totals so the
headline numbers reflect *first-run* cost, not wall-clock cost on a re-run.
Wall-clock latency is recorded separately in `latency_ms` and is the only
field that benefits from cache hits.
