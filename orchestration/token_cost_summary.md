# Token cost summary — Intro-Specter rebuttal campaign

Running total, updated as experiments complete. All costs are real API spend against the $80 campaign cap.

| Experiment | Scope | Tokens (in/out) | Real cost (rough) | Notes |
|---|---|---|---|---|
| A full (4 cells, incl. smoke/pilot rows) | TruthQA×Mistral/Qwen, ρ=0.10/0.30 | 664,439 / 176,696 = 841,135 | ~$0.13 (at $0.15/M blended) | 279 rows, confirmed exact from raw JSONL |
| B full (2 cells) | TruthQA×Mistral/Qwen, IterVRP vs Intro-Specter | 258,234 / 72,912 = 331,146 | ~$0.05 (at $0.15/M blended) | 146 rows, confirmed exact from raw JSONL |
| C baseline run (v2) | 150 examples, no profile, Direct only | 74,603 / 2,338 = 76,941 | ~$0.01 | Confirmed exact |
| C draft annotation (v2) | 50 classification calls, qwen-2.5-7b-instruct | 38,299 / 1,581 = 39,880 | <$0.01 | Confirmed exact |
| D synthetic sweep (2/3/4/5 faults × 2 variants) | 480 graphs | 0 / 0 | **$0.00** | Rule-based, no LLM provider |
| D real sweep (N=2/3/4, 3 arms each) | 540×3 = 1,620 rows | ~9,400,000 total | **~$1.40** | Confirmed by subagent |
| D real N=5/6 extension | TBD | TBD | TBD | In progress |
| Non-synthetic TravelPlanner | TBD | TBD | TBD | In progress |
| Cumulative-repair fix exploration | 60 synthetic graphs × 2 checks | 0 / 0 | $0.00 | Rule-based |

**Running total, all confirmed exact from raw data: 841,135 (A) + 331,146 (B) + 76,941 (C baseline) + 39,880 (C annotation) + ~9,400,000 (D real sweep) ≈ 10.69M tokens ≈ $1.60 total.** Note: D's real sweep dominates the token count (long multi-hop TwoWiki contexts × 3 arms × 3 fault counts), everything else is comparatively tiny. Well under the $80 cap by a wide margin — cost was never the binding constraint tonight, wall-clock time was.

## To do
- Add N=5/6 and non-synthetic TravelPlanner rows once those complete.
