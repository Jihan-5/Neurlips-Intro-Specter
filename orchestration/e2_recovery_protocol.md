# E2 amended recovery protocol (v2)

Status: frozen before recovery production execution. This is an amended recovery of E2, not the untouched preregistered run. The failed original tree at `outputs/rebuttal/profile_bootstrap/` is immutable audit evidence and is never an analysis input.

## Constants retained

- Datasets: TruthfulQA, HotpotQA, 2WikiMultiHopQA, MuSiQue, LongMemEval real loaders; benchmark seed 42 and their frozen splits.
- Models: Llama-3.1-8B and Mistral-Nemo-12B. Llama-3.1-8B remains the disclosed substitute for unavailable Qwen-2.5-7B.
- Arms: Direct, Reflexion, Intro-Specter; generation seed 0; `tau_abstain=0.0`.
- 100 deterministic profile variants per selected example. Profile redraw seeds and downstream prompts/scoring are unchanged.
- Analysis: per-arm profile-draw distribution and per-example variance, paired IS-minus-Reflexion draw distribution, bottom-decile effect, favorable fraction, and the preregistered Hoeffding bound.

## Amendments

1. All recovery data live under `outputs/rebuttal/profile_bootstrap_recovery_v1/`.
2. Work is assigned by `sha256(task_id + "|" + variant_idx) mod num_shards`; a complete `(task_id, variant_idx)` and all of its arms belong to one shard. Sharding changes scheduling only.
3. Each shard owns one JSONL, one error JSONL, one SQLite delta cache, and one writer lock. Historical caches are read-only fallbacks and are queried only by the repository's complete request hash.
4. Paraphrases are accepted only by deterministic semantic validation against the canonical structured template. Validation covers numbers/ranges, negation, prohibitions, required actions, response format/style, named/categorical values, required clauses, and meaning-bearing domain terms. Generation is deterministic per `(task_id, variant_idx, span_id, retry)` and has three attempts. Exhaustion is an explicit fatal invalid unit; canonical text is never silently substituted.
5. Historical rows are salvageable only when the logical key is unique or every duplicate object is identical; no conflict or profile-hash conflict exists; cache replay recovers the exact effective profile and reproduces the stored profile hash; every recovered paraphrase passes the new validator; frozen task/model/seed/arm inputs match; and the row is well formed. Every output row is labeled `salvaged_verified` or `rerun_recovery` with source provenance.
6. Merge is integrity-fatal on missing/unexpected/overlapping/conflicting/malformed keys, invalid paraphrases, incomplete arm triples, or within-variant profile-hash inconsistency. No first/last-row rule exists.

## Retry-convergence amendment (v2)

Production audit of v1 found that shard relaunches incorrectly granted the same
logical paraphrase span another three-attempt budget, and that provider exceptions
were recorded as semantic exhaustion. V2 therefore makes the following narrow,
prospective corrections while retaining all v1 rows, errors, caches, and states as
audit evidence:

1. The three-attempt paraphrase budget belongs to `(cell, task_id, variant_idx,
   span_id)` across all process and shard restarts. An append-only shard ledger
   records candidate text, deterministic validation labels, and attempt index.
2. A semantic candidate consumes one of the three attempts. A provider exception
   consumes no semantic attempt and is recorded separately with exception type,
   HTTP status, message, and transient/permanent classification.
3. Accepted cached candidates are reused after revalidation. Three persisted
   semantic failures are terminal and are never regenerated merely because a
   shard process restarts.
4. The validator now recognizes only audited, demonstrably equivalent wording:
   English-only/no-language-switch phrasing; commonly/generally accepted public
   opinion plus explicit lack of strict accuracy; orthographic hyphen/space forms;
   and narrow synonyms for public transportation/taxis, citation, clinical
   relevance, accessibility negation, plain language, verbal image description,
   and the other explicit clauses listed in regression tests. The high-school-
   teacher and no-preamble checks are intentionally not weakened: omitting the
   teacher identity or any of the three direct/no-preamble/no-restatement clauses
   remains a real semantic loss.
   Accepted-row preflight also recognizes the audited word-order and surface-form
   equivalents "accessible route with no stairs or uneven surfaces" and
   "refrains from food and drink discussions during fasting periods." Directional
   preferences remain strict: "taxis over public transit" is not equivalent to
   "public transit over taxis" and affected rows are regenerated rather than
   grandfathered.
5. Every cached v1 candidate is reconstructed and revalidated under v2 before it
   can be imported. Existing accepted rows are retained byte-for-byte only when
   every effective redraw passes the complete v2 semantic validator. A failing
   source file is first archived byte-for-byte; only its failing logical-arm rows
   are removed from the active source and become missing work for their owning
   shard. The integrity merge accepts a recorded legacy protocol hash only after
   applying the complete v2 validator to every effective redraw.

## Completion and disclosure

F2 may be generated only from a complete merged recovery root passing the recovery integrity gate. F2 provenance and manuscript text must state that execution and paraphrase validation were amended after duplicate-writer corruption and semantic-loss detection in the original run.
