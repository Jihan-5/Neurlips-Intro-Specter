# E2 amended recovery protocol (v1)

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

## Completion and disclosure

F2 may be generated only from a complete merged recovery root passing the recovery integrity gate. F2 provenance and manuscript text must state that execution and paraphrase validation were amended after duplicate-writer corruption and semantic-loss detection in the original run.
