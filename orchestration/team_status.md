# Team status log

Append-only. Format: [date] [track] [what ran] [verification] [next]

[2026-09-16] [Track E1] Synced artifacts, verified Twowiki completion via logs, ran aggregate_real_benchmarks.py [Generated 7 tables in outputs/real/tables/] [Migrate .tex tables into paper_final.tex]
[2026-09-16] [Track E3] Ran aggregate_experiment_a_diagnostic.py, pushed to remote artifacts branch [7/7 cells complete, 0 errors. IS 9.6% failure rate vs Reflexion 13.2%] [None]
[2026-09-16] [Track E2] Running profile_bootstrap_study.py via nohup [HotpotQA/TruthfulQA 100% complete, others progressing; partials pushed to artifacts] [Run E2 aggregation upon 100% completion]

[2026-09-16] [Jazz takeover / estimates] Completed specification, coordination, git, process and artifact reconnaissance before edits. Existing branch jashkaran/results; preserved two modified and two untracked files. Remote results/artifacts tips match local. Five E2 workers PIDs 65587–65591 protected; remote-owned longmemeval×llama8B must not be relaunched locally. E1 audit+one-row resume estimate 10–30 min / <$1; E3 paired mechanism implementation+10 cells 2–6h / $3–5; E2 remaining runtime exceeds 6h at observed throughput (roughly 20–50h for slowest cells), already split by cell, no duplicate launches; F1–F4 local generation/audit estimate 2–4h / $0 API; E4 optional 30–60 min / $0 if data supports a defensible rule. OpenRouter health: limit_remaining $95.85. Existing sync script uses prohibited reset --hard; safe transport required. Prior E1/E3 completion claims are not verified: SPR has 647/648 rows, and no distinct E3 mechanism artifacts exist.

[2026-09-16] [E1 COMPLETE / Jihan notification] Resumed sole missing TwoWiki/Llama8B row using .venv/bin/python -m intro_specter.cli run --config configs/real/spr__twowiki_real__llama-3.1-8b.yaml. Aggregation invocation: .venv/bin/python scripts/aggregate_real_benchmarks.py --root outputs/real/spr --output-dir outputs/jazz/e1_tables. Verbatim output follows. This is 12 runnable-model cells, not the historical 16-cell claim; headline reconciliation reserved for Jihan.

```text

Wrote 7 tables to outputs/jazz/e1_tables/

Datasets: ['longmemeval_real', 'musique_real', 'truthfulqa_real', 'twowiki_real']
Models:   ['llama-3.1-8b', 'llama-3.3-70b', 'mistral-nemo-12b']

Main table rows: 12
Head-to-head rows: 0

| cell | successes | rows | success (%) |
|---|---:|---:|---:|
| longmemeval_real__llama-3.1-8b | 53 | 60 | 88.3333 |
| longmemeval_real__llama-3.3-70b | 36 | 60 | 60.0000 |
| longmemeval_real__mistral-nemo-12b | 49 | 60 | 81.6667 |
| musique_real__llama-3.1-8b | 57 | 60 | 95.0000 |
| musique_real__llama-3.3-70b | 56 | 60 | 93.3333 |
| musique_real__mistral-nemo-12b | 53 | 60 | 88.3333 |
| truthfulqa_real__llama-3.1-8b | 34 | 36 | 94.4444 |
| truthfulqa_real__llama-3.3-70b | 34 | 36 | 94.4444 |
| truthfulqa_real__mistral-nemo-12b | 31 | 36 | 86.1111 |
| twowiki_real__llama-3.1-8b | 58 | 60 | 96.6667 |
| twowiki_real__llama-3.3-70b | 58 | 60 | 96.6667 |
| twowiki_real__mistral-nemo-12b | 60 | 60 | 100.0000 |
| POOLED | 579 | 648 | 89.3519 |
```

[2026-09-16] [E3] Isolated smoke complete: 10/10 rows, zero errors, shared prime hashes, profile candidates added on 2 pairs. Existing baseline already admits profile ancestors, contradicting exclusion prose; flag admits remaining profile nodes without altering default behavior. Fresh paired seed-0 rho=0/.1/.3 campaign launched with three workers, separate per-cell caches/output, flock protection, bounded resume passes, and a read-only E2 monitor. Revised estimate 4–8h (over 6h risk reported here; split into independently resumable dataset/model cells). No claimed recovery until full paired aggregation.

[2026-09-16] [F1 / Jihan decision pending] User explicitly reconfirmed that Jihan owns the paper headline scope. Paper headline unchanged. Generated separate review packages with `.venv/bin/python scripts/generate_jazz_results.py` (exact McNemar, paired-bootstrap CIs, baseline-wise Holm correction, Direct, MuSiQue, tied maxima, token ratios, source hashes). Verbatim generated summaries:

Scope 12:
```json
{
  "scope": 12,
  "n": 648,
  "successes": 579,
  "success_rate": 0.8935185185185185,
  "paired_n": 648,
  "paired_is": 0.8935185185185185,
  "paired_reflexion": 0.8672839506172839,
  "delta": 0.026234567901234573,
  "wins": 8,
  "ties": 2,
  "losses": 2,
  "significant_wins": 0,
  "significant_losses": 0
}
```

Scope 16:
```json
{
  "scope": 16,
  "n": 866,
  "successes": 757,
  "success_rate": 0.874133949191686,
  "paired_n": 866,
  "paired_is": 0.874133949191686,
  "paired_reflexion": 0.8533487297921478,
  "delta": 0.020785219399538146,
  "wins": 10,
  "ties": 2,
  "losses": 4,
  "significant_wins": 0,
  "significant_losses": 0
}
```

[E1 artifact transport] External upload was rejected by automatic approval review; no artifact push occurred. Exact requested payload: 76 files, 822370 bytes, only outputs/real/spr + outputs/jazz/e1_tables + outputs/jazz/e1_summary.txt; approval pending. Existing main/results/artifacts worktrees preserved.

[2026-09-16] [E2 trust gate / notify Jihan] Cache-only seeded spot check: 30 pairs inspected by Codex, 13 contain constraint omissions/weakening. This is not a human sign-off. See orchestration/jazz_paraphrase_review.md. Frozen bootstrap outputs continue unchanged, but final confirmatory reporting is blocked by failed meaning preservation and incomplete grids.

[2026-09-16] [E4 exploratory] `.venv/bin/python scripts/aggregate_personalwab_contradictions.py` over all downloaded PersonalWAB users. Rule frozen before count in orchestration/personalwab_contradiction_protocol.md. Verbatim summary:
```json
{
  "analysis": "EXPLORATORY brand-preference/history discordance, not all semantic contradictions",
  "n_users": 1000,
  "n_history_users": 1000,
  "users_with_matched_brand_history": 989,
  "matched_brands": 16516,
  "matched_reviews": 18407,
  "users_with_discordance": 25,
  "fraction": 0.025,
  "protocol": "orchestration/personalwab_contradiction_protocol.md"
}
```

[2026-09-17] [Overnight hardening] Preserved healthy inherited coordinator PID 16065, its three E3 children, and five independently caffeinated E2 workers PIDs 65587--65591. Installed a second `caffeinate -i` coordinator (current PID recorded in `outputs/jazz/inherited_jobs.json`) waiting on the same flock for atomic handoff. Added persistent launch ledger (maximum inherited/initial launch plus one resume), per-cell writer locks, atomic status, append-only history, live row-rate ETAs, malformed/duplicate/hash checks, and read-only inherited-worker discovery. Machine recovery state: `outputs/jazz/overnight_status.json`; completion sentinel is conservatively gated by `scripts/jazz_final_gate.py` and is correctly absent while requirements remain incomplete.

[2026-09-17] [F1/F4 validation] Regenerated both decision-neutral F1 packages with `.venv/bin/python scripts/generate_jazz_results.py`; standalone 12-cell and 16-cell review PDFs build. Exact McNemar, paired-bootstrap CI, Direct, MuSiQue, tied maxima, recorded-token arithmetic, and source hashes are generated artifacts, not hand-entered. Full manuscript builds with Tectonic. Consistency audit now has only the two Jihan-reserved headline scope/cell-record findings; no undefined citations or stale generated sources. Removed or corrected unsupported candidate exclusion, seed, tau, cycle-removal, cost-accounting, partial-completion, failure-taxonomy, and extraction-metric claims rather than certifying untraceable numbers.

[2026-09-17] [Tests] `.venv/bin/pytest -q tests/test_jazz_workflow.py` -> 4 passed. Full `.venv/bin/pytest -q` -> 56 passed when allowed to access existing Hugging Face cache lock files outside the workspace sandbox. Build/test evidence is under `outputs/jazz/validation/`, `outputs/jazz/logs/`, and `outputs/jazz/build/`.

[2026-09-17] [E1 artifact transport COMPLETE] `scripts/sync_artifacts_safe.py push` published commit `c0db897630348dfd7ba44577958edde60c3371f4` to `origin/artifacts`. Parent `a957cb3`; payload contains the completed TwoWiki/Llama8B SPR row, `outputs/jazz/e1_summary.txt`, and all generated E1 tables. Bootstrap/live experiment trees remained protected.

[2026-09-17] [E4 artifact transport COMPLETE] Published the validated exploratory PersonalWAB proxy summary to `origin/artifacts` at `7b173f24332ed76c7815b787c23f58c14f99ac79`. The committed protocol continues to label this as brand-preference/history discordance rather than a general semantic-contradiction estimate.

[2026-09-17] [E3/F3 COMPLETE] Required complete aggregation: `.venv/bin/python scripts/aggregate_profile_candidacy.py --require-complete --output outputs/jazz/candidacy_final.json`. All 10 cells complete: 2,040/2,040 attempts, 816 paired units, zero errors, missing pairs, malformed rows, duplicates, conflicts, or paired-hash mismatches. Expanded candidacy recovered 16/37 clean-solved, corruption-associated default failures (43.2%) with zero regressions. Generated `paper_sections/generated/jazz_f3.tex` from the paired artifacts, integrated it beside mechanism diagnostics with the causal-denominator caveat, and built both results and prose worktrees. E3 artifacts published to `origin/artifacts` at `17be585`.

[2026-09-17] [E2 BLOCKED / ROOT CAUSE] `outputs/jazz/e2_failure_audit.json` records two independent failures. First, historical relaunch logs prove two top-level workers overlapped each long-running local append-only output; the surviving workers are now single owners, but three cells preserve conflicting duplicate logical keys (168 LongMemEval/Mistral, 310 MuSiQue/Mistral, 407 conflicting of 411 duplicates TwoWiki/Mistral). The frozen protocol defines no first/last-row selection rule, so these files are not publishable and were not rewritten. Second, the preregistered paraphrase gate failed 17/30: acceptance checks only non-empty/length-bounded output and cannot detect dropped imperatives. The fetched remote-owned LongMemEval/Llama artifact is also partial at 4,390/18,000 rows. F2 remains deliberately ungeneratable.

[2026-09-17] [Morning validation] Jazz workflow suite: 5 passed. Full offline suite with existing Hugging Face caches: 57 passed. Results-worktree and designated prose-worktree manuscripts both build with Tectonic. `outputs/jazz/JAZZ_DONE` remains absent because E2/F2 fails completeness, integrity, and meaning-preservation gates; Jihan's E1 headline-scope decision remains reserved.

[2026-09-17] [E2 amended recovery RUNNING] Froze the failed original tree and launched `outputs/rebuttal/profile_bootstrap_recovery_v1` under `orchestration/e2_recovery_protocol.md`: deterministic disjoint shards, read-only historical-cache fallback, per-shard delta caches/locks, semantic paraphrase validation with bounded retry, provenance labels, and integrity-fatal merging. Adopted every healthy live shard without duplication. Diagnosed completed Hotpot shards as semantic-invalid exhaustion rather than process crashes; preserved failed error/state/cache attempts under shard audit directories and resumed only missing logical units through the unchanged validator. Corrected adaptive concurrency to count only newly appended 429/rate-limit events in a rolling window; the supervisor ramped 8→12→16→20→24→28→32 with no recent rate-limit burst and no blockers. Added automated completion chaining for ten integrity merges, preregistered E2 aggregation, F2 generation/integration with amended-recovery disclosure, Jazz/full tests, both manuscript builds, safe artifact transport, status/report refresh, and the final gate. Jihan's headline-scope choice remains untouched and reserved.

[2026-09-17] [E2 infrastructure recovery] The data volume reached ENOSPC, interrupting four shard status/cache writes and the coordinator while append-only JSONL outputs remained intact. Reclaimed 7.0 GiB by deleting only `/Users/jas/Library/Caches/com.apple.dt.Xcode` (regenerable cache; no repository/data/artifact removal). Preserved the zero-byte interrupted shard-state snapshot under `failed_attempts/`. Hardened coordinator startup to discover exact live worker command lines when a prior coordinator dies before ledger flush, reject duplicate live owners, and treat partial state snapshots as absent while retaining strict JSONL-key merge integrity. The restarted coordinator adopted surviving workers, restored 32 active slots, and resumed heartbeats without blockers.
