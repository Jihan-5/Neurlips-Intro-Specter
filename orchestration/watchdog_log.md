# Watchdog Log

Ground-truth verification log. All numbers below are directly measured
(`find | xargs cat | wc -l`, `ps aux`, `uptime`, `top -l 1`) by the watchdog
agent — never taken from other agents' self-reports.

---

## Cycle 1 — 2026-07-26 02:03 (local, macOS `date` at time of check)

### Row counts (`find <dir> -name "*.jsonl" | xargs cat | wc -l`)

| Directory | Rows | Files |
|---|---|---|
| experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 |
| experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 |
| experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 |
| experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 |
| experiment_d/full_matrix_hotpotqa | 753 | 84 |
| experiment_d/full_matrix_musique | 9131 | 112 |
| experiment_d/full_matrix_longmemeval | 11933 | 72 |
| experiment_d/full_matrix_travelplanner_synthetic | 2397 | 84 |
| experiment_c/nonsynthetic_multifault | 3749 | 112 |
| experiment_recipes | 1112 | 28 |
| experiment_amazon | 1684 | 28 |

### Real process count

58 live `Python.framework` processes directly executing `scripts/rebuttal_experiment_*.py`
(resource_tracker helper processes and `bash -c` wrapper shells excluded from this count).
4 `bash -c` wrapper loops also present (amazon x3 models via for-loops + musique sequential loop),
which sequentially re-spawn the python workers above — not counted as separate experiment processes.

Breakdown:
- amazon: 4 running (1 each: llama31-8b, llama70b, mistral, qwen)
- experiment_c nonsynthetic_multifault: 16 running (4 each: llama31-8b, llama70b, mistral, qwen)
- experiment_d hotpotqa: 12 running (3 each: llama31-8b, llama70b, mistral, qwen)
- experiment_d longmemeval_matrix: 9 running
- experiment_d musique: 1 running (mistral) — bash wrapper will chain qwen/llama31-8b next
- experiment_d travelplanner: 12 running (3 each: llama31-8b, llama70b, mistral, qwen)
- recipes: 4 running (1 each: llama31-8b, llama70b, mistral, qwen)

### System load

- `uptime`: load averages 2.39 2.30 2.10 (up 42 days)
- `top -l 1`: CPU 3.63% user / 10.19% sys / 86.17% idle; PhysMem 17G used (2743M wired, 7963M compressor), 80M unused
- Assessment: NOT concerning. Load avg well under typical core count for this machine, plenty of CPU idle. "80M unused" physical RAM looks tight in isolation but 7963M is in the compressor (reclaimable) — not a hard low-memory condition. Will keep watching trend.

### Discrepancies found this cycle
None — this is the baseline cycle, no prior data to compare against yet. No notification sent.

---

## Cycle 3 — 2026-07-26 02:09:00 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 1302 | 84 | 753 | 549 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 9173 | 112 | 9131 | 42 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 12151 | 73 | 11933 | 218 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 2561 | 84 | 2397 | 164 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 3958 | 112 | 3749 | 209 |
| outputs/rebuttal/experiment_recipes | 1211 | 28 | 1112 | 99 |
| outputs/rebuttal/experiment_amazon | 1825 | 28 | 1684 | 141 |

### Real process count

58 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_amazon_llama70b.py
scripts/rebuttal_experiment_amazon_mistral.py
scripts/rebuttal_experiment_amazon_qwen.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama31_8b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama70b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen.py
scripts/rebuttal_experiment_d_real_hotpotqa_llama31_8b.py
scripts/rebuttal_experiment_d_real_hotpotqa_llama70b.py
scripts/rebuttal_experiment_d_real_hotpotqa_mistral.py
scripts/rebuttal_experiment_d_real_hotpotqa_qwen.py
scripts/rebuttal_experiment_d_real_longmemeval_matrix.py
scripts/rebuttal_experiment_d_real_musique_mistral.py
scripts/rebuttal_experiment_d_real_travelplanner_llama31_8b.py
scripts/rebuttal_experiment_d_real_travelplanner_llama70b.py
scripts/rebuttal_experiment_d_real_travelplanner_mistral.py
scripts/rebuttal_experiment_d_real_travelplanner_qwen.py
scripts/rebuttal_experiment_recipes_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

-  2:09  up 42 days,  1:25, 1 user, load averages: 2.02 1.96 1.97
- CPU usage: 9.91% user, 17.23% sys, 72.84% idle 
PhysMem: 17G used (2657M wired, 8905M compressor), 116M unused.
- Assessment: not concerning

---

## Cycle 4 — 2026-07-26 02:09:15 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 1323 | 84 | 1302 | 21 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 9174 | 112 | 9173 | 1 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 12164 | 73 | 12151 | 13 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 2564 | 84 | 2561 | 3 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 3966 | 112 | 3958 | 8 |
| outputs/rebuttal/experiment_recipes | 1216 | 28 | 1211 | 5 |
| outputs/rebuttal/experiment_amazon | 1829 | 28 | 1825 | 4 |

### Real process count

58 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_amazon_llama70b.py
scripts/rebuttal_experiment_amazon_mistral.py
scripts/rebuttal_experiment_amazon_qwen.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama31_8b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama70b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen.py
scripts/rebuttal_experiment_d_real_hotpotqa_llama31_8b.py
scripts/rebuttal_experiment_d_real_hotpotqa_llama70b.py
scripts/rebuttal_experiment_d_real_hotpotqa_mistral.py
scripts/rebuttal_experiment_d_real_hotpotqa_qwen.py
scripts/rebuttal_experiment_d_real_longmemeval_matrix.py
scripts/rebuttal_experiment_d_real_musique_mistral.py
scripts/rebuttal_experiment_d_real_travelplanner_llama31_8b.py
scripts/rebuttal_experiment_d_real_travelplanner_llama70b.py
scripts/rebuttal_experiment_d_real_travelplanner_mistral.py
scripts/rebuttal_experiment_d_real_travelplanner_qwen.py
scripts/rebuttal_experiment_recipes_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

-  2:09  up 42 days,  1:25, 1 user, load averages: 2.34 2.03 2.00
- CPU usage: 8.45% user, 13.78% sys, 77.76% idle 
PhysMem: 17G used (2614M wired, 8854M compressor), 87M unused.
- Assessment: not concerning

---

## Cycle 5 — 2026-07-26 02:26:16 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 2955 | 84 | 1323 | 1632 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 9306 | 112 | 9174 | 132 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 12926 | 76 | 12164 | 762 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 3100 | 84 | 2564 | 536 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 4583 | 112 | 3966 | 617 |
| outputs/rebuttal/experiment_recipes | 1473 | 28 | 1216 | 257 |
| outputs/rebuttal/experiment_amazon | 2283 | 28 | 1829 | 454 |

### Real process count

58 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_amazon_llama70b.py
scripts/rebuttal_experiment_amazon_mistral.py
scripts/rebuttal_experiment_amazon_qwen.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama31_8b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama70b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen.py
scripts/rebuttal_experiment_d_real_hotpotqa_llama31_8b.py
scripts/rebuttal_experiment_d_real_hotpotqa_llama70b.py
scripts/rebuttal_experiment_d_real_hotpotqa_mistral.py
scripts/rebuttal_experiment_d_real_hotpotqa_qwen.py
scripts/rebuttal_experiment_d_real_longmemeval_matrix.py
scripts/rebuttal_experiment_d_real_musique_mistral.py
scripts/rebuttal_experiment_d_real_travelplanner_llama31_8b.py
scripts/rebuttal_experiment_d_real_travelplanner_llama70b.py
scripts/rebuttal_experiment_d_real_travelplanner_mistral.py
scripts/rebuttal_experiment_d_real_travelplanner_qwen.py
scripts/rebuttal_experiment_recipes_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

-  2:26  up 42 days,  1:42, 1 user, load averages: 3.14 2.89 2.62
- CPU usage: 13.51% user, 28.96% sys, 57.51% idle 
PhysMem: 17G used (2610M wired, 8130M compressor), 153M unused.
- Assessment: not concerning

---

## Cycle 6 — 2026-07-26 02:43:17 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 4671 | 84 | 2955 | 1716 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 9453 | 112 | 9306 | 147 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 13512 | 79 | 12926 | 586 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 3688 | 84 | 3100 | 588 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 5251 | 112 | 4583 | 668 |
| outputs/rebuttal/experiment_recipes | 1678 | 28 | 1473 | 205 |
| outputs/rebuttal/experiment_amazon | 2541 | 28 | 2283 | 258 |

### Real process count

50 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama31_8b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama70b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen.py
scripts/rebuttal_experiment_d_real_hotpotqa_llama31_8b.py
scripts/rebuttal_experiment_d_real_hotpotqa_llama70b.py
scripts/rebuttal_experiment_d_real_hotpotqa_mistral.py
scripts/rebuttal_experiment_d_real_hotpotqa_qwen.py
scripts/rebuttal_experiment_d_real_longmemeval_matrix.py
scripts/rebuttal_experiment_d_real_musique_mistral.py
scripts/rebuttal_experiment_d_real_travelplanner_llama31_8b.py
scripts/rebuttal_experiment_d_real_travelplanner_llama70b.py
scripts/rebuttal_experiment_d_real_travelplanner_mistral.py
scripts/rebuttal_experiment_d_real_travelplanner_qwen.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

-  2:43  up 42 days,  1:59, 1 user, load averages: 7.25 4.78 3.54
- CPU usage: 3.16% user, 9.74% sys, 87.8% idle 
PhysMem: 17G used (2885M wired, 7035M compressor), 93M unused.
- Assessment: not concerning

---

## Cycle 7 — 2026-07-26 03:00:19 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 6221 | 84 | 4671 | 1550 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 9600 | 112 | 9453 | 147 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 13824 | 80 | 13512 | 312 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 4385 | 84 | 3688 | 697 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 5913 | 112 | 5251 | 662 |
| outputs/rebuttal/experiment_recipes | 1854 | 28 | 1678 | 176 |
| outputs/rebuttal/experiment_amazon | 2693 | 35 | 2541 | 152 |

### Real process count

50 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama31_8b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama70b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen.py
scripts/rebuttal_experiment_d_real_hotpotqa_llama31_8b.py
scripts/rebuttal_experiment_d_real_hotpotqa_llama70b.py
scripts/rebuttal_experiment_d_real_hotpotqa_mistral.py
scripts/rebuttal_experiment_d_real_hotpotqa_qwen.py
scripts/rebuttal_experiment_d_real_longmemeval_matrix.py
scripts/rebuttal_experiment_d_real_musique_mistral.py
scripts/rebuttal_experiment_d_real_travelplanner_llama31_8b.py
scripts/rebuttal_experiment_d_real_travelplanner_llama70b.py
scripts/rebuttal_experiment_d_real_travelplanner_mistral.py
scripts/rebuttal_experiment_d_real_travelplanner_qwen.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

-  3:00  up 42 days,  2:16, 1 user, load averages: 1.16 1.96 2.65
- CPU usage: 4.52% user, 14.6% sys, 81.40% idle 
PhysMem: 17G used (2535M wired, 7464M compressor), 83M unused.
- Assessment: not concerning

---

## Cycle 8 — 2026-07-26 03:17:20 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 7872 | 84 | 6221 | 1651 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 9758 | 112 | 9600 | 158 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 14033 | 80 | 13824 | 209 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 4922 | 84 | 4385 | 537 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 6550 | 112 | 5913 | 637 |
| outputs/rebuttal/experiment_recipes | 2032 | 28 | 1854 | 178 |
| outputs/rebuttal/experiment_amazon | 2838 | 35 | 2693 | 145 |

### Real process count

50 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama31_8b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama70b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen.py
scripts/rebuttal_experiment_d_real_hotpotqa_llama31_8b.py
scripts/rebuttal_experiment_d_real_hotpotqa_llama70b.py
scripts/rebuttal_experiment_d_real_hotpotqa_mistral.py
scripts/rebuttal_experiment_d_real_hotpotqa_qwen.py
scripts/rebuttal_experiment_d_real_longmemeval_matrix.py
scripts/rebuttal_experiment_d_real_musique_mistral.py
scripts/rebuttal_experiment_d_real_travelplanner_llama31_8b.py
scripts/rebuttal_experiment_d_real_travelplanner_llama70b.py
scripts/rebuttal_experiment_d_real_travelplanner_mistral.py
scripts/rebuttal_experiment_d_real_travelplanner_qwen.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

-  3:17  up 42 days,  2:33, 1 user, load averages: 2.01 2.27 2.48
- CPU usage: 15.48% user, 14.14% sys, 70.36% idle 
PhysMem: 17G used (2536M wired, 7725M compressor), 155M unused.
- Assessment: not concerning

---

## Cycle 9 — 2026-07-26 03:34:21 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 9497 | 84 | 7872 | 1625 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 9893 | 112 | 9758 | 135 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 14283 | 81 | 14033 | 250 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 5472 | 84 | 4922 | 550 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 7150 | 112 | 6550 | 600 |
| outputs/rebuttal/experiment_recipes | 2209 | 28 | 2032 | 177 |
| outputs/rebuttal/experiment_amazon | 2979 | 35 | 2838 | 141 |

### Real process count

48 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama31_8b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama70b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen.py
scripts/rebuttal_experiment_d_real_hotpotqa_llama31_8b.py
scripts/rebuttal_experiment_d_real_hotpotqa_llama70b.py
scripts/rebuttal_experiment_d_real_hotpotqa_mistral.py
scripts/rebuttal_experiment_d_real_hotpotqa_qwen.py
scripts/rebuttal_experiment_d_real_longmemeval_matrix.py
scripts/rebuttal_experiment_d_real_musique_mistral.py
scripts/rebuttal_experiment_d_real_travelplanner_llama31_8b.py
scripts/rebuttal_experiment_d_real_travelplanner_llama70b.py
scripts/rebuttal_experiment_d_real_travelplanner_mistral.py
scripts/rebuttal_experiment_d_real_travelplanner_qwen.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

-  3:34  up 42 days,  2:50, 1 user, load averages: 2.66 2.41 2.35
- CPU usage: 9.63% user, 10.26% sys, 80.10% idle 
PhysMem: 17G used (2501M wired, 7304M compressor), 130M unused.
- Assessment: not concerning

---

## Cycle 10 — 2026-07-26 03:51:22 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 10784 | 84 | 9497 | 1287 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 10029 | 112 | 9893 | 136 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 14488 | 82 | 14283 | 205 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 6041 | 84 | 5472 | 569 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 7832 | 112 | 7150 | 682 |
| outputs/rebuttal/experiment_recipes | 2415 | 28 | 2209 | 206 |
| outputs/rebuttal/experiment_amazon | 3144 | 35 | 2979 | 165 |

### Real process count

44 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama31_8b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama70b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen.py
scripts/rebuttal_experiment_d_real_hotpotqa_llama31_8b.py
scripts/rebuttal_experiment_d_real_hotpotqa_llama70b.py
scripts/rebuttal_experiment_d_real_hotpotqa_mistral.py
scripts/rebuttal_experiment_d_real_longmemeval_matrix.py
scripts/rebuttal_experiment_d_real_musique_mistral.py
scripts/rebuttal_experiment_d_real_travelplanner_llama31_8b.py
scripts/rebuttal_experiment_d_real_travelplanner_llama70b.py
scripts/rebuttal_experiment_d_real_travelplanner_mistral.py
scripts/rebuttal_experiment_d_real_travelplanner_qwen.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

-  3:51  up 42 days,  3:07, 1 user, load averages: 4.41 3.70 3.08
- CPU usage: 25.47% user, 13.11% sys, 61.41% idle 
PhysMem: 17G used (2480M wired, 6580M compressor), 170M unused.
- Assessment: not concerning

---

## Cycle 11 — 2026-07-26 04:08:24 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 11648 | 84 | 10784 | 864 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 10158 | 112 | 10029 | 129 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 14559 | 82 | 14488 | 71 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 6515 | 84 | 6041 | 474 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 8440 | 112 | 7832 | 608 |
| outputs/rebuttal/experiment_recipes | 2599 | 28 | 2415 | 184 |
| outputs/rebuttal/experiment_amazon | 3279 | 35 | 3144 | 135 |

### Real process count

42 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama31_8b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama70b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen.py
scripts/rebuttal_experiment_d_real_hotpotqa_llama31_8b.py
scripts/rebuttal_experiment_d_real_hotpotqa_llama70b.py
scripts/rebuttal_experiment_d_real_hotpotqa_mistral.py
scripts/rebuttal_experiment_d_real_longmemeval_matrix.py
scripts/rebuttal_experiment_d_real_musique_mistral.py
scripts/rebuttal_experiment_d_real_travelplanner_llama31_8b.py
scripts/rebuttal_experiment_d_real_travelplanner_llama70b.py
scripts/rebuttal_experiment_d_real_travelplanner_mistral.py
scripts/rebuttal_experiment_d_real_travelplanner_qwen.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

-  4:08  up 42 days,  3:24, 1 user, load averages: 2.26 2.73 3.08
- CPU usage: 8.71% user, 11.18% sys, 80.10% idle 
PhysMem: 17G used (2498M wired, 6597M compressor), 146M unused.
- Assessment: not concerning

---

## Cycle 12 — 2026-07-26 04:25:25 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 12334 | 84 | 11648 | 686 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 10342 | 112 | 10158 | 184 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 14635 | 82 | 14559 | 76 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 7046 | 84 | 6515 | 531 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 9031 | 112 | 8440 | 591 |
| outputs/rebuttal/experiment_recipes | 2770 | 28 | 2599 | 171 |
| outputs/rebuttal/experiment_amazon | 3405 | 35 | 3279 | 126 |

### Real process count

40 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama31_8b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama70b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen.py
scripts/rebuttal_experiment_d_real_hotpotqa_llama31_8b.py
scripts/rebuttal_experiment_d_real_hotpotqa_llama70b.py
scripts/rebuttal_experiment_d_real_longmemeval_matrix.py
scripts/rebuttal_experiment_d_real_musique_mistral.py
scripts/rebuttal_experiment_d_real_travelplanner_llama31_8b.py
scripts/rebuttal_experiment_d_real_travelplanner_llama70b.py
scripts/rebuttal_experiment_d_real_travelplanner_mistral.py
scripts/rebuttal_experiment_d_real_travelplanner_qwen.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

-  4:25  up 42 days,  3:41, 1 user, load averages: 2.76 2.62 2.66
- CPU usage: 3.22% user, 10.58% sys, 86.19% idle 
PhysMem: 17G used (2576M wired, 6173M compressor), 102M unused.
- Assessment: not concerning

---

## Cycle 13 — 2026-07-26 04:42:26 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 12738 | 84 | 12334 | 404 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 10470 | 112 | 10342 | 128 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 14675 | 82 | 14635 | 40 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 7553 | 84 | 7046 | 507 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 9568 | 112 | 9031 | 537 |
| outputs/rebuttal/experiment_recipes | 2941 | 28 | 2770 | 171 |
| outputs/rebuttal/experiment_amazon | 3547 | 35 | 3405 | 142 |

### Real process count

40 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama31_8b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama70b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen.py
scripts/rebuttal_experiment_d_real_hotpotqa_llama31_8b.py
scripts/rebuttal_experiment_d_real_hotpotqa_llama70b.py
scripts/rebuttal_experiment_d_real_longmemeval_matrix.py
scripts/rebuttal_experiment_d_real_musique_mistral.py
scripts/rebuttal_experiment_d_real_travelplanner_llama31_8b.py
scripts/rebuttal_experiment_d_real_travelplanner_llama70b.py
scripts/rebuttal_experiment_d_real_travelplanner_mistral.py
scripts/rebuttal_experiment_d_real_travelplanner_qwen.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

-  4:42  up 42 days,  3:58, 1 user, load averages: 1.66 1.59 1.83
- CPU usage: 2.53% user, 9.26% sys, 88.19% idle 
PhysMem: 17G used (2499M wired, 7296M compressor), 110M unused.
- Assessment: not concerning

---

## Cycle 14 — 2026-07-26 04:59:28 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 13217 | 84 | 12738 | 479 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 10620 | 112 | 10470 | 150 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 14847 | 83 | 14675 | 172 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 8072 | 84 | 7553 | 519 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 10139 | 112 | 9568 | 571 |
| outputs/rebuttal/experiment_recipes | 3086 | 35 | 2941 | 145 |
| outputs/rebuttal/experiment_amazon | 3664 | 35 | 3547 | 117 |

### Real process count

40 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama31_8b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama70b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen.py
scripts/rebuttal_experiment_d_real_hotpotqa_llama31_8b.py
scripts/rebuttal_experiment_d_real_hotpotqa_llama70b.py
scripts/rebuttal_experiment_d_real_longmemeval_matrix.py
scripts/rebuttal_experiment_d_real_musique_mistral.py
scripts/rebuttal_experiment_d_real_travelplanner_llama31_8b.py
scripts/rebuttal_experiment_d_real_travelplanner_llama70b.py
scripts/rebuttal_experiment_d_real_travelplanner_mistral.py
scripts/rebuttal_experiment_d_real_travelplanner_qwen.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

-  4:59  up 42 days,  4:15, 1 user, load averages: 2.79 2.45 2.16
- CPU usage: 10.12% user, 14.68% sys, 75.18% idle 
PhysMem: 17G used (2483M wired, 7557M compressor), 110M unused.
- Assessment: not concerning

---

## Cycle 15 — 2026-07-26 05:16:29 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 13734 | 84 | 13217 | 517 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 10738 | 112 | 10620 | 118 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 14950 | 84 | 14847 | 103 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 8546 | 84 | 8072 | 474 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 10757 | 112 | 10139 | 618 |
| outputs/rebuttal/experiment_recipes | 3238 | 35 | 3086 | 152 |
| outputs/rebuttal/experiment_amazon | 3757 | 42 | 3664 | 93 |

### Real process count

38 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama31_8b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama70b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen.py
scripts/rebuttal_experiment_d_real_hotpotqa_llama31_8b.py
scripts/rebuttal_experiment_d_real_hotpotqa_llama70b.py
scripts/rebuttal_experiment_d_real_longmemeval_matrix.py
scripts/rebuttal_experiment_d_real_musique_mistral.py
scripts/rebuttal_experiment_d_real_travelplanner_llama31_8b.py
scripts/rebuttal_experiment_d_real_travelplanner_llama70b.py
scripts/rebuttal_experiment_d_real_travelplanner_mistral.py
scripts/rebuttal_experiment_d_real_travelplanner_qwen.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

-  5:16  up 42 days,  4:32, 1 user, load averages: 3.48 2.77 2.47
- CPU usage: 10.61% user, 11.50% sys, 77.87% idle 
PhysMem: 17G used (2487M wired, 7756M compressor), 113M unused.
- Assessment: not concerning

---

## Cycle 16 — 2026-07-26 05:33:31 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 14128 | 84 | 13734 | 394 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 10825 | 112 | 10738 | 87 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15001 | 84 | 14950 | 51 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 9087 | 84 | 8546 | 541 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 11363 | 112 | 10757 | 606 |
| outputs/rebuttal/experiment_recipes | 3387 | 42 | 3238 | 149 |
| outputs/rebuttal/experiment_amazon | 3820 | 42 | 3757 | 63 |

### Real process count

36 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama31_8b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama70b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen.py
scripts/rebuttal_experiment_d_real_hotpotqa_llama31_8b.py
scripts/rebuttal_experiment_d_real_hotpotqa_llama70b.py
scripts/rebuttal_experiment_d_real_longmemeval_matrix.py
scripts/rebuttal_experiment_d_real_musique_mistral.py
scripts/rebuttal_experiment_d_real_travelplanner_llama31_8b.py
scripts/rebuttal_experiment_d_real_travelplanner_llama70b.py
scripts/rebuttal_experiment_d_real_travelplanner_mistral.py
scripts/rebuttal_experiment_d_real_travelplanner_qwen.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

-  5:33  up 42 days,  4:49, 1 user, load averages: 2.79 2.85 2.72
- CPU usage: 10.99% user, 9.53% sys, 79.47% idle 
PhysMem: 17G used (2469M wired, 6861M compressor), 98M unused.
- Assessment: not concerning

---

## Cycle 17 — 2026-07-26 05:50:32 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 14203 | 84 | 14128 | 75 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 10913 | 112 | 10825 | 88 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15031 | 84 | 15001 | 30 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 9685 | 84 | 9087 | 598 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 11928 | 112 | 11363 | 565 |
| outputs/rebuttal/experiment_recipes | 3570 | 42 | 3387 | 183 |
| outputs/rebuttal/experiment_amazon | 3891 | 42 | 3820 | 71 |

### Real process count

35 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama31_8b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama70b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen.py
scripts/rebuttal_experiment_d_real_hotpotqa_llama31_8b.py
scripts/rebuttal_experiment_d_real_longmemeval_matrix.py
scripts/rebuttal_experiment_d_real_musique_mistral.py
scripts/rebuttal_experiment_d_real_travelplanner_llama31_8b.py
scripts/rebuttal_experiment_d_real_travelplanner_llama70b.py
scripts/rebuttal_experiment_d_real_travelplanner_mistral.py
scripts/rebuttal_experiment_d_real_travelplanner_qwen.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

-  5:50  up 42 days,  5:06, 1 user, load averages: 2.47 2.23 2.32
- CPU usage: 10.58% user, 10.45% sys, 78.95% idle 
PhysMem: 17G used (2476M wired, 7148M compressor), 104M unused.
- Assessment: not concerning

---

## Cycle 18 — 2026-07-26 06:07:33 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 14290 | 84 | 14203 | 87 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 10988 | 112 | 10913 | 75 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15072 | 84 | 15031 | 41 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 10226 | 84 | 9685 | 541 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 12551 | 112 | 11928 | 623 |
| outputs/rebuttal/experiment_recipes | 3713 | 42 | 3570 | 143 |
| outputs/rebuttal/experiment_amazon | 3951 | 42 | 3891 | 60 |

### Real process count

35 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama31_8b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama70b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen.py
scripts/rebuttal_experiment_d_real_hotpotqa_llama31_8b.py
scripts/rebuttal_experiment_d_real_longmemeval_matrix.py
scripts/rebuttal_experiment_d_real_musique_mistral.py
scripts/rebuttal_experiment_d_real_travelplanner_llama31_8b.py
scripts/rebuttal_experiment_d_real_travelplanner_llama70b.py
scripts/rebuttal_experiment_d_real_travelplanner_mistral.py
scripts/rebuttal_experiment_d_real_travelplanner_qwen.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

-  6:07  up 42 days,  5:23, 1 user, load averages: 1.37 1.87 1.93
- CPU usage: 1.54% user, 9.38% sys, 89.7% idle 
PhysMem: 17G used (2536M wired, 7344M compressor), 87M unused.
- Assessment: not concerning

---

## Cycle 19 — 2026-07-26 06:24:35 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 14479 | 84 | 14290 | 189 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 11083 | 112 | 10988 | 95 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15072 | 25 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 10656 | 84 | 10226 | 430 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 13077 | 112 | 12551 | 526 |
| outputs/rebuttal/experiment_recipes | 3841 | 42 | 3713 | 128 |
| outputs/rebuttal/experiment_amazon | 4018 | 42 | 3951 | 67 |

### Real process count

34 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama31_8b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama70b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen.py
scripts/rebuttal_experiment_d_real_hotpotqa_llama31_8b.py
scripts/rebuttal_experiment_d_real_musique_mistral.py
scripts/rebuttal_experiment_d_real_travelplanner_llama31_8b.py
scripts/rebuttal_experiment_d_real_travelplanner_llama70b.py
scripts/rebuttal_experiment_d_real_travelplanner_mistral.py
scripts/rebuttal_experiment_d_real_travelplanner_qwen.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

-  6:24  up 42 days,  5:40, 1 user, load averages: 1.74 1.67 1.73
- CPU usage: 1.69% user, 8.74% sys, 89.55% idle 
PhysMem: 17G used (2474M wired, 7105M compressor), 81M unused.
- Assessment: not concerning

---

## Cycle 20 — 2026-07-26 06:41:36 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 14629 | 84 | 14479 | 150 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 11181 | 112 | 11083 | 98 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 11140 | 84 | 10656 | 484 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 13664 | 112 | 13077 | 587 |
| outputs/rebuttal/experiment_recipes | 3999 | 42 | 3841 | 158 |
| outputs/rebuttal/experiment_amazon | 4098 | 42 | 4018 | 80 |

### Real process count

33 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama31_8b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama70b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen.py
scripts/rebuttal_experiment_d_real_hotpotqa_llama31_8b.py
scripts/rebuttal_experiment_d_real_musique_mistral.py
scripts/rebuttal_experiment_d_real_travelplanner_llama31_8b.py
scripts/rebuttal_experiment_d_real_travelplanner_llama70b.py
scripts/rebuttal_experiment_d_real_travelplanner_mistral.py
scripts/rebuttal_experiment_d_real_travelplanner_qwen.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

-  6:41  up 42 days,  5:57, 1 user, load averages: 1.15 1.34 1.49
- CPU usage: 2.51% user, 9.17% sys, 88.31% idle 
PhysMem: 17G used (2630M wired, 7622M compressor), 108M unused.
- Assessment: not concerning

---

## Cycle 21 — 2026-07-26 06:58:37 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 14750 | 84 | 14629 | 121 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 11267 | 112 | 11181 | 86 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 11643 | 84 | 11140 | 503 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 14225 | 112 | 13664 | 561 |
| outputs/rebuttal/experiment_recipes | 4137 | 42 | 3999 | 138 |
| outputs/rebuttal/experiment_amazon | 4147 | 42 | 4098 | 49 |

### Real process count

32 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama31_8b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama70b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen.py
scripts/rebuttal_experiment_d_real_hotpotqa_llama31_8b.py
scripts/rebuttal_experiment_d_real_musique_mistral.py
scripts/rebuttal_experiment_d_real_travelplanner_llama31_8b.py
scripts/rebuttal_experiment_d_real_travelplanner_llama70b.py
scripts/rebuttal_experiment_d_real_travelplanner_mistral.py
scripts/rebuttal_experiment_d_real_travelplanner_qwen.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

-  6:58  up 42 days,  6:15, 1 user, load averages: 1.00 1.25 1.34
- CPU usage: 1.46% user, 8.36% sys, 90.17% idle 
PhysMem: 17G used (2462M wired, 6677M compressor), 95M unused.
- Assessment: not concerning

---

## Cycle 22 — 2026-07-26 07:15:39 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 14791 | 84 | 14750 | 41 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 11346 | 112 | 11267 | 79 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 12182 | 84 | 11643 | 539 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 14718 | 112 | 14225 | 493 |
| outputs/rebuttal/experiment_recipes | 4278 | 42 | 4137 | 141 |
| outputs/rebuttal/experiment_amazon | 4230 | 42 | 4147 | 83 |

### Real process count

32 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama31_8b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama70b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen.py
scripts/rebuttal_experiment_d_real_hotpotqa_llama31_8b.py
scripts/rebuttal_experiment_d_real_musique_mistral.py
scripts/rebuttal_experiment_d_real_travelplanner_llama31_8b.py
scripts/rebuttal_experiment_d_real_travelplanner_llama70b.py
scripts/rebuttal_experiment_d_real_travelplanner_mistral.py
scripts/rebuttal_experiment_d_real_travelplanner_qwen.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

-  7:15  up 42 days,  6:32, 1 user, load averages: 1.45 1.51 1.54
- CPU usage: 1.84% user, 8.57% sys, 89.57% idle 
PhysMem: 17G used (2486M wired, 7386M compressor), 84M unused.
- Assessment: not concerning

---

## Cycle 23 — 2026-07-26 07:32:40 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 14862 | 84 | 14791 | 71 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 11459 | 112 | 11346 | 113 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 12662 | 84 | 12182 | 480 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 15224 | 112 | 14718 | 506 |
| outputs/rebuttal/experiment_recipes | 4412 | 42 | 4278 | 134 |
| outputs/rebuttal/experiment_amazon | 4306 | 42 | 4230 | 76 |

### Real process count

30 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama31_8b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama70b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen.py
scripts/rebuttal_experiment_d_real_hotpotqa_llama31_8b.py
scripts/rebuttal_experiment_d_real_musique_mistral.py
scripts/rebuttal_experiment_d_real_travelplanner_llama31_8b.py
scripts/rebuttal_experiment_d_real_travelplanner_llama70b.py
scripts/rebuttal_experiment_d_real_travelplanner_mistral.py
scripts/rebuttal_experiment_d_real_travelplanner_qwen.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

-  7:32  up 42 days,  6:49, 1 user, load averages: 1.69 1.67 1.60
- CPU usage: 4.96% user, 9.93% sys, 85.9% idle 
PhysMem: 17G used (2462M wired, 7184M compressor), 101M unused.
- Assessment: not concerning

---

## Cycle 24 — 2026-07-26 07:49:42 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 14956 | 84 | 14862 | 94 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 11525 | 112 | 11459 | 66 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 12958 | 84 | 12662 | 296 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 15674 | 112 | 15224 | 450 |
| outputs/rebuttal/experiment_recipes | 4531 | 42 | 4412 | 119 |
| outputs/rebuttal/experiment_amazon | 4365 | 42 | 4306 | 59 |

### Real process count

24 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama31_8b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama70b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen.py
scripts/rebuttal_experiment_d_real_hotpotqa_llama31_8b.py
scripts/rebuttal_experiment_d_real_musique_mistral.py
scripts/rebuttal_experiment_d_real_travelplanner_llama31_8b.py
scripts/rebuttal_experiment_d_real_travelplanner_llama70b.py
scripts/rebuttal_experiment_d_real_travelplanner_qwen.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

-  7:49  up 42 days,  7:06, 1 user, load averages: 1.65 1.57 1.50
- CPU usage: 1.87% user, 9.38% sys, 88.73% idle 
PhysMem: 17G used (2478M wired, 6459M compressor), 106M unused.
- Assessment: not concerning

---

## Cycle 25 — 2026-07-26 08:06:43 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 15009 | 84 | 14956 | 53 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 11598 | 112 | 11525 | 73 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 13179 | 84 | 12958 | 221 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 16040 | 112 | 15674 | 366 |
| outputs/rebuttal/experiment_recipes | 4636 | 42 | 4531 | 105 |
| outputs/rebuttal/experiment_amazon | 4441 | 42 | 4365 | 76 |

### Real process count

22 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama31_8b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama70b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen.py
scripts/rebuttal_experiment_d_real_hotpotqa_llama31_8b.py
scripts/rebuttal_experiment_d_real_musique_mistral.py
scripts/rebuttal_experiment_d_real_travelplanner_llama31_8b.py
scripts/rebuttal_experiment_d_real_travelplanner_llama70b.py
scripts/rebuttal_experiment_d_real_travelplanner_qwen.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

-  8:06  up 42 days,  7:23, 1 user, load averages: 1.31 1.68 1.76
- CPU usage: 2.59% user, 9.7% sys, 88.32% idle 
PhysMem: 17G used (2515M wired, 6488M compressor), 388M unused.
- Assessment: not concerning

---

## Cycle 26 — 2026-07-26 08:23:44 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 15053 | 84 | 15009 | 44 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 11668 | 112 | 11598 | 70 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 13422 | 84 | 13179 | 243 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 16374 | 112 | 16040 | 334 |
| outputs/rebuttal/experiment_recipes | 4747 | 42 | 4636 | 111 |
| outputs/rebuttal/experiment_amazon | 4501 | 42 | 4441 | 60 |

### Real process count

20 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama31_8b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama70b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen.py
scripts/rebuttal_experiment_d_real_hotpotqa_llama31_8b.py
scripts/rebuttal_experiment_d_real_musique_mistral.py
scripts/rebuttal_experiment_d_real_travelplanner_llama31_8b.py
scripts/rebuttal_experiment_d_real_travelplanner_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

-  8:23  up 42 days,  7:40, 1 user, load averages: 1.02 1.34 1.53
- CPU usage: 1.56% user, 8.62% sys, 89.80% idle 
PhysMem: 17G used (2478M wired, 6035M compressor), 201M unused.
- Assessment: not concerning

---

## Cycle 27 — 2026-07-26 08:40:46 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 15056 | 84 | 15053 | 3 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 11810 | 112 | 11668 | 142 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 13596 | 84 | 13422 | 174 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 16668 | 112 | 16374 | 294 |
| outputs/rebuttal/experiment_recipes | 4880 | 42 | 4747 | 133 |
| outputs/rebuttal/experiment_amazon | 4566 | 42 | 4501 | 65 |

### Real process count

18 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama31_8b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama70b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen.py
scripts/rebuttal_experiment_d_real_musique_qwen.py
scripts/rebuttal_experiment_d_real_travelplanner_llama31_8b.py
scripts/rebuttal_experiment_d_real_travelplanner_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

-  8:40  up 42 days,  7:57, 1 user, load averages: 1.55 1.54 1.50
- CPU usage: 3.10% user, 9.81% sys, 87.8% idle 
PhysMem: 17G used (2476M wired, 5809M compressor), 104M unused.
- Assessment: not concerning

---

## Cycle 28 — 2026-07-26 08:57:47 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 11983 | 112 | 11810 | 173 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 13732 | 84 | 13596 | 136 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 16974 | 112 | 16668 | 306 |
| outputs/rebuttal/experiment_recipes | 5025 | 42 | 4880 | 145 |
| outputs/rebuttal/experiment_amazon | 4623 | 42 | 4566 | 57 |

### Real process count

18 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama31_8b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama70b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen.py
scripts/rebuttal_experiment_d_real_musique_qwen.py
scripts/rebuttal_experiment_d_real_travelplanner_llama31_8b.py
scripts/rebuttal_experiment_d_real_travelplanner_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

-  8:57  up 42 days,  8:14, 1 user, load averages: 1.32 1.27 1.33
- CPU usage: 1.30% user, 8.86% sys, 89.83% idle 
PhysMem: 17G used (2476M wired, 6047M compressor), 126M unused.
- Assessment: not concerning

---

## Cycle 29 — 2026-07-26 09:14:49 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 12156 | 112 | 11983 | 173 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 13846 | 84 | 13732 | 114 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 17266 | 112 | 16974 | 292 |
| outputs/rebuttal/experiment_recipes | 5142 | 42 | 5025 | 117 |
| outputs/rebuttal/experiment_amazon | 4684 | 42 | 4623 | 61 |

### Real process count

17 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama31_8b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama70b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen.py
scripts/rebuttal_experiment_d_real_musique_qwen.py
scripts/rebuttal_experiment_d_real_travelplanner_llama31_8b.py
scripts/rebuttal_experiment_d_real_travelplanner_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

-  9:14  up 42 days,  8:31, 1 user, load averages: 1.48 1.45 1.40
- CPU usage: 2.62% user, 9.85% sys, 87.51% idle 
PhysMem: 17G used (2476M wired, 5884M compressor), 228M unused.
- Assessment: not concerning

---

## Cycle 30 — 2026-07-26 09:31:50 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 12347 | 112 | 12156 | 191 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 13998 | 84 | 13846 | 152 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 17521 | 112 | 17266 | 255 |
| outputs/rebuttal/experiment_recipes | 5273 | 42 | 5142 | 131 |
| outputs/rebuttal/experiment_amazon | 4756 | 49 | 4684 | 72 |

### Real process count

14 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama31_8b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama70b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen.py
scripts/rebuttal_experiment_d_real_musique_qwen.py
scripts/rebuttal_experiment_d_real_travelplanner_llama31_8b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

-  9:31  up 42 days,  8:48, 1 user, load averages: 1.19 1.42 1.39
- CPU usage: 2.14% user, 9.53% sys, 88.32% idle 
PhysMem: 17G used (2480M wired, 5564M compressor), 311M unused.
- Assessment: not concerning

---

## Cycle 31 — 2026-07-26 09:48:51 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 12555 | 112 | 12347 | 208 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 14073 | 84 | 13998 | 75 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 17669 | 112 | 17521 | 148 |
| outputs/rebuttal/experiment_recipes | 5394 | 49 | 5273 | 121 |
| outputs/rebuttal/experiment_amazon | 4798 | 49 | 4756 | 42 |

### Real process count

12 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama31_8b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen.py
scripts/rebuttal_experiment_d_real_musique_qwen.py
scripts/rebuttal_experiment_d_real_travelplanner_llama31_8b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

-  9:48  up 42 days,  9:05, 1 user, load averages: 1.26 1.40 1.37
- CPU usage: 2.79% user, 9.44% sys, 87.76% idle 
PhysMem: 17G used (2477M wired, 5330M compressor), 202M unused.
- Assessment: not concerning

---

## Cycle 32 — 2026-07-26 10:05:53 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 12721 | 112 | 12555 | 166 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 14143 | 84 | 14073 | 70 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 17771 | 112 | 17669 | 102 |
| outputs/rebuttal/experiment_recipes | 5507 | 49 | 5394 | 113 |
| outputs/rebuttal/experiment_amazon | 4870 | 49 | 4798 | 72 |

### Real process count

12 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama31_8b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen.py
scripts/rebuttal_experiment_d_real_musique_qwen.py
scripts/rebuttal_experiment_d_real_travelplanner_llama31_8b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

- 10:05  up 42 days,  9:22, 1 user, load averages: 1.62 1.45 1.38
- CPU usage: 2.40% user, 8.81% sys, 88.78% idle 
PhysMem: 17G used (2477M wired, 5616M compressor), 197M unused.
- Assessment: not concerning

---

## Cycle 33 — 2026-07-26 10:22:54 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 12911 | 112 | 12721 | 190 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 14220 | 84 | 14143 | 77 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 17843 | 112 | 17771 | 72 |
| outputs/rebuttal/experiment_recipes | 5618 | 49 | 5507 | 111 |
| outputs/rebuttal/experiment_amazon | 4932 | 49 | 4870 | 62 |

### Real process count

11 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama31_8b.py
scripts/rebuttal_experiment_d_real_musique_qwen.py
scripts/rebuttal_experiment_d_real_travelplanner_llama31_8b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

- 10:22  up 42 days,  9:39, 1 user, load averages: 2.15 1.47 1.40
- CPU usage: 1.59% user, 8.76% sys, 89.64% idle 
PhysMem: 17G used (2564M wired, 5228M compressor), 90M unused.
- Assessment: not concerning

---

## Cycle 34 — 2026-07-26 10:39:56 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 13140 | 112 | 12911 | 229 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 14278 | 84 | 14220 | 58 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 17898 | 112 | 17843 | 55 |
| outputs/rebuttal/experiment_recipes | 5701 | 49 | 5618 | 83 |
| outputs/rebuttal/experiment_amazon | 4982 | 49 | 4932 | 50 |

### Real process count

11 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama31_8b.py
scripts/rebuttal_experiment_d_real_musique_qwen.py
scripts/rebuttal_experiment_d_real_travelplanner_llama31_8b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

- 10:39  up 42 days,  9:56, 1 user, load averages: 1.92 2.00 1.74
- CPU usage: 2.51% user, 8.88% sys, 88.59% idle 
PhysMem: 17G used (2609M wired, 5443M compressor), 134M unused.
- Assessment: not concerning

---

## Cycle 35 — 2026-07-26 10:56:57 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 13339 | 112 | 13140 | 199 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 14352 | 84 | 14278 | 74 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 17961 | 112 | 17898 | 63 |
| outputs/rebuttal/experiment_recipes | 5800 | 49 | 5701 | 99 |
| outputs/rebuttal/experiment_amazon | 5040 | 49 | 4982 | 58 |

### Real process count

11 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama31_8b.py
scripts/rebuttal_experiment_d_real_musique_qwen.py
scripts/rebuttal_experiment_d_real_travelplanner_llama31_8b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

- 10:56  up 42 days, 10:13, 1 user, load averages: 2.36 2.81 2.55
- CPU usage: 1.81% user, 9.58% sys, 88.60% idle 
PhysMem: 17G used (2633M wired, 5920M compressor), 101M unused.
- Assessment: not concerning

---

## Cycle 36 — 2026-07-26 11:13:58 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 13538 | 112 | 13339 | 199 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 14407 | 84 | 14352 | 55 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 18024 | 112 | 17961 | 63 |
| outputs/rebuttal/experiment_recipes | 5916 | 49 | 5800 | 116 |
| outputs/rebuttal/experiment_amazon | 5090 | 49 | 5040 | 50 |

### Real process count

13 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama31_8b.py
scripts/rebuttal_experiment_d_real_musique_llama31_8b.py
scripts/rebuttal_experiment_d_real_musique_llama70b.py
scripts/rebuttal_experiment_d_real_musique_qwen.py
scripts/rebuttal_experiment_d_real_travelplanner_llama31_8b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

- 11:13  up 42 days, 10:30, 1 user, load averages: 2.26 2.66 2.70
- CPU usage: 6.25% user, 13.45% sys, 80.28% idle 
PhysMem: 17G used (2609M wired, 4835M compressor), 303M unused.
- Assessment: not concerning

---

## Cycle 37 — 2026-07-26 11:31:00 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 13787 | 112 | 13538 | 249 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 14479 | 84 | 14407 | 72 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 18104 | 112 | 18024 | 80 |
| outputs/rebuttal/experiment_recipes | 6007 | 49 | 5916 | 91 |
| outputs/rebuttal/experiment_amazon | 5148 | 49 | 5090 | 58 |

### Real process count

12 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama31_8b.py
scripts/rebuttal_experiment_d_real_musique_llama31_8b.py
scripts/rebuttal_experiment_d_real_musique_llama70b.py
scripts/rebuttal_experiment_d_real_travelplanner_llama31_8b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

- 11:31  up 42 days, 10:47, 1 user, load averages: 2.87 2.54 2.59
- CPU usage: 2.62% user, 8.80% sys, 88.56% idle 
PhysMem: 17G used (2595M wired, 4132M compressor), 132M unused.
- Assessment: not concerning

---

## Cycle 38 — 2026-07-26 11:48:01 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 14002 | 112 | 13787 | 215 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 14562 | 84 | 14479 | 83 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 18199 | 112 | 18104 | 95 |
| outputs/rebuttal/experiment_recipes | 6118 | 49 | 6007 | 111 |
| outputs/rebuttal/experiment_amazon | 5202 | 49 | 5148 | 54 |

### Real process count

12 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama31_8b.py
scripts/rebuttal_experiment_d_real_musique_llama31_8b.py
scripts/rebuttal_experiment_d_real_musique_llama70b.py
scripts/rebuttal_experiment_d_real_travelplanner_llama31_8b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

- 11:48  up 42 days, 11:04, 1 user, load averages: 2.09 2.42 2.59
- CPU usage: 3.91% user, 9.70% sys, 86.38% idle 
PhysMem: 17G used (2592M wired, 4492M compressor), 374M unused.
- Assessment: not concerning

---

## Cycle 39 — 2026-07-26 12:05:02 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 14207 | 112 | 14002 | 205 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 14631 | 84 | 14562 | 69 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 18296 | 112 | 18199 | 97 |
| outputs/rebuttal/experiment_recipes | 6210 | 56 | 6118 | 92 |
| outputs/rebuttal/experiment_amazon | 5253 | 49 | 5202 | 51 |

### Real process count

12 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama31_8b.py
scripts/rebuttal_experiment_d_real_musique_llama31_8b.py
scripts/rebuttal_experiment_d_real_musique_llama70b.py
scripts/rebuttal_experiment_d_real_travelplanner_llama31_8b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

- 12:05  up 42 days, 11:21, 1 user, load averages: 2.08 1.99 2.23
- CPU usage: 2.43% user, 8.89% sys, 88.66% idle 
PhysMem: 17G used (2445M wired, 5308M compressor), 108M unused.
- Assessment: not concerning

---

## Cycle 40 — 2026-07-26 12:22:04 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 14332 | 112 | 14207 | 125 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 14735 | 84 | 14631 | 104 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 18369 | 112 | 18296 | 73 |
| outputs/rebuttal/experiment_recipes | 6315 | 56 | 6210 | 105 |
| outputs/rebuttal/experiment_amazon | 5300 | 49 | 5253 | 47 |

### Real process count

12 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama31_8b.py
scripts/rebuttal_experiment_d_real_musique_llama31_8b.py
scripts/rebuttal_experiment_d_real_musique_llama70b.py
scripts/rebuttal_experiment_d_real_travelplanner_llama31_8b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

- 12:22  up 42 days, 11:38, 1 user, load averages: 2.16 2.14 2.15
- CPU usage: 1.89% user, 8.79% sys, 89.30% idle 
PhysMem: 17G used (2566M wired, 5972M compressor), 92M unused.
- Assessment: not concerning

---

## Cycle 41 — 2026-07-26 12:39:05 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 14524 | 112 | 14332 | 192 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 14808 | 84 | 14735 | 73 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 18452 | 112 | 18369 | 83 |
| outputs/rebuttal/experiment_recipes | 6427 | 56 | 6315 | 112 |
| outputs/rebuttal/experiment_amazon | 5349 | 49 | 5300 | 49 |

### Real process count

11 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama31_8b.py
scripts/rebuttal_experiment_d_real_musique_llama31_8b.py
scripts/rebuttal_experiment_d_real_musique_llama70b.py
scripts/rebuttal_experiment_d_real_travelplanner_llama31_8b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

- 12:39  up 42 days, 11:55, 1 user, load averages: 2.72 2.42 2.31
- CPU usage: 3.69% user, 10.3% sys, 86.26% idle 
PhysMem: 17G used (2609M wired, 6863M compressor), 550M unused.
- Assessment: not concerning

---

## Cycle 42 — 2026-07-26 12:56:07 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 14677 | 112 | 14524 | 153 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 14861 | 84 | 14808 | 53 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 18552 | 112 | 18452 | 100 |
| outputs/rebuttal/experiment_recipes | 6520 | 56 | 6427 | 93 |
| outputs/rebuttal/experiment_amazon | 5402 | 49 | 5349 | 53 |

### Real process count

10 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama31_8b.py
scripts/rebuttal_experiment_d_real_musique_llama31_8b.py
scripts/rebuttal_experiment_d_real_musique_llama70b.py
scripts/rebuttal_experiment_d_real_travelplanner_llama31_8b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

- 12:56  up 42 days, 12:12, 1 user, load averages: 2.63 2.46 2.39
- CPU usage: 2.3% user, 9.80% sys, 88.15% idle 
PhysMem: 17G used (2493M wired, 6506M compressor), 85M unused.
- Assessment: not concerning

---

## Cycle 43 — 2026-07-26 13:13:08 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 14938 | 112 | 14677 | 261 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 14876 | 84 | 14861 | 15 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 18628 | 112 | 18552 | 76 |
| outputs/rebuttal/experiment_recipes | 6618 | 56 | 6520 | 98 |
| outputs/rebuttal/experiment_amazon | 5448 | 49 | 5402 | 46 |

### Real process count

10 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama31_8b.py
scripts/rebuttal_experiment_d_real_musique_llama31_8b.py
scripts/rebuttal_experiment_d_real_musique_llama70b.py
scripts/rebuttal_experiment_d_real_travelplanner_llama31_8b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

- 13:13  up 42 days, 12:29, 1 user, load averages: 2.48 1.88 1.90
- CPU usage: 2.18% user, 9.26% sys, 88.54% idle 
PhysMem: 17G used (2428M wired, 6389M compressor), 92M unused.
- Assessment: not concerning

---

## Cycle 44 — 2026-07-26 13:30:10 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 15118 | 112 | 14938 | 180 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 14889 | 84 | 14876 | 13 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 18709 | 112 | 18628 | 81 |
| outputs/rebuttal/experiment_recipes | 6713 | 56 | 6618 | 95 |
| outputs/rebuttal/experiment_amazon | 5505 | 49 | 5448 | 57 |

### Real process count

10 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama31_8b.py
scripts/rebuttal_experiment_d_real_musique_llama31_8b.py
scripts/rebuttal_experiment_d_real_musique_llama70b.py
scripts/rebuttal_experiment_d_real_travelplanner_llama31_8b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

- 13:30  up 42 days, 12:46, 1 user, load averages: 1.24 1.80 1.95
- CPU usage: 3.13% user, 9.41% sys, 87.45% idle 
PhysMem: 17G used (2729M wired, 6423M compressor), 82M unused.
- Assessment: not concerning

---

## Cycle 45 — 2026-07-26 13:47:11 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 15392 | 112 | 15118 | 274 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 14907 | 84 | 14889 | 18 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 18764 | 112 | 18709 | 55 |
| outputs/rebuttal/experiment_recipes | 6797 | 56 | 6713 | 84 |
| outputs/rebuttal/experiment_amazon | 5536 | 49 | 5505 | 31 |

### Real process count

10 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_mistral.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama31_8b.py
scripts/rebuttal_experiment_d_real_musique_llama31_8b.py
scripts/rebuttal_experiment_d_real_musique_llama70b.py
scripts/rebuttal_experiment_d_real_travelplanner_llama31_8b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

- 13:47  up 42 days, 13:03, 1 user, load averages: 1.82 2.15 2.01
- CPU usage: 2.6% user, 8.79% sys, 89.13% idle 
PhysMem: 17G used (2624M wired, 6770M compressor), 287M unused.
- Assessment: not concerning

---

## Cycle 46 — 2026-07-26 14:04:13 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 15599 | 112 | 15392 | 207 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 14921 | 84 | 14907 | 14 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 18829 | 112 | 18764 | 65 |
| outputs/rebuttal/experiment_recipes | 6893 | 56 | 6797 | 96 |
| outputs/rebuttal/experiment_amazon | 5725 | 49 | 5536 | 189 |

### Real process count

13 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_amazon_llama70b.py
scripts/rebuttal_experiment_amazon_mistral.py
scripts/rebuttal_experiment_amazon_qwen.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama31_8b.py
scripts/rebuttal_experiment_d_real_musique_llama31_8b.py
scripts/rebuttal_experiment_d_real_musique_llama70b.py
scripts/rebuttal_experiment_d_real_travelplanner_llama31_8b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

- 14:04  up 42 days, 13:20, 1 user, load averages: 2.50 2.24 2.07
- CPU usage: 2.26% user, 9.20% sys, 88.52% idle 
PhysMem: 17G used (2812M wired, 7492M compressor), 123M unused.
- Assessment: not concerning

---

## Cycle 47 — 2026-07-26 14:21:14 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 15765 | 112 | 15599 | 166 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 14924 | 84 | 14921 | 3 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 18871 | 112 | 18829 | 42 |
| outputs/rebuttal/experiment_recipes | 6998 | 56 | 6893 | 105 |
| outputs/rebuttal/experiment_amazon | 6020 | 56 | 5725 | 295 |

### Real process count

12 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_amazon_llama70b.py
scripts/rebuttal_experiment_amazon_mistral.py
scripts/rebuttal_experiment_amazon_qwen.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama31_8b.py
scripts/rebuttal_experiment_d_real_musique_llama31_8b.py
scripts/rebuttal_experiment_d_real_musique_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

- 14:21  up 42 days, 13:37, 1 user, load averages: 1.87 1.94 1.96
- CPU usage: 3.73% user, 10.46% sys, 85.80% idle 
PhysMem: 17G used (2723M wired, 6806M compressor), 82M unused.
- Assessment: not concerning

---

## Cycle 48 — 2026-07-26 14:38:16 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 15829 | 112 | 15765 | 64 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 18969 | 119 | 18871 | 98 |
| outputs/rebuttal/experiment_recipes | 7100 | 56 | 6998 | 102 |
| outputs/rebuttal/experiment_amazon | 6324 | 56 | 6020 | 304 |

### Real process count

13 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_amazon_llama70b.py
scripts/rebuttal_experiment_amazon_mistral.py
scripts/rebuttal_experiment_amazon_qwen.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama31_8b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen72b.py
scripts/rebuttal_experiment_d_real_musique_llama31_8b.py
scripts/rebuttal_experiment_d_real_musique_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

- 14:38  up 42 days, 13:54, 1 user, load averages: 2.52 2.89 2.56
- CPU usage: 4.47% user, 10.48% sys, 85.4% idle 
PhysMem: 17G used (2820M wired, 7635M compressor), 89M unused.
- Assessment: not concerning

---

## Cycle 49 — 2026-07-26 14:55:17 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 16068 | 112 | 15829 | 239 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 19057 | 119 | 18969 | 88 |
| outputs/rebuttal/experiment_recipes | 7200 | 56 | 7100 | 100 |
| outputs/rebuttal/experiment_amazon | 6702 | 56 | 6324 | 378 |

### Real process count

12 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_amazon_llama70b.py
scripts/rebuttal_experiment_amazon_qwen.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama31_8b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen72b.py
scripts/rebuttal_experiment_d_real_musique_llama31_8b.py
scripts/rebuttal_experiment_d_real_musique_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

- 14:55  up 42 days, 14:11, 1 user, load averages: 1.78 2.36 2.50
- CPU usage: 8.17% user, 11.57% sys, 80.24% idle 
PhysMem: 17G used (2574M wired, 6181M compressor), 117M unused.
- Assessment: not concerning

---

## Cycle 50 — 2026-07-26 15:12:19 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 16287 | 112 | 16068 | 219 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 19154 | 119 | 19057 | 97 |
| outputs/rebuttal/experiment_recipes | 7301 | 56 | 7200 | 101 |
| outputs/rebuttal/experiment_amazon | 7005 | 56 | 6702 | 303 |

### Real process count

12 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_amazon_llama70b.py
scripts/rebuttal_experiment_amazon_qwen.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama31_8b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen72b.py
scripts/rebuttal_experiment_d_real_musique_llama31_8b.py
scripts/rebuttal_experiment_d_real_musique_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

- 15:12  up 42 days, 14:28, 1 user, load averages: 2.08 2.10 2.20
- CPU usage: 6.5% user, 9.97% sys, 83.96% idle 
PhysMem: 17G used (2455M wired, 6623M compressor), 203M unused.
- Assessment: not concerning

---

## Cycle 51 — 2026-07-26 15:29:21 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 16541 | 112 | 16287 | 254 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 19265 | 119 | 19154 | 111 |
| outputs/rebuttal/experiment_recipes | 7411 | 56 | 7301 | 110 |
| outputs/rebuttal/experiment_amazon | 7301 | 56 | 7005 | 296 |

### Real process count

12 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_amazon_llama70b.py
scripts/rebuttal_experiment_amazon_qwen.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama31_8b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen72b.py
scripts/rebuttal_experiment_d_real_musique_llama31_8b.py
scripts/rebuttal_experiment_d_real_musique_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

- 15:29  up 42 days, 14:45, 1 user, load averages: 1.92 1.92 2.06
- CPU usage: 13.89% user, 12.67% sys, 73.42% idle 
PhysMem: 17G used (2671M wired, 7465M compressor), 143M unused.
- Assessment: not concerning

---

## Cycle 52 — 2026-07-26 15:46:22 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 16787 | 112 | 16541 | 246 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 19357 | 119 | 19265 | 92 |
| outputs/rebuttal/experiment_recipes | 7526 | 63 | 7411 | 115 |
| outputs/rebuttal/experiment_amazon | 7648 | 63 | 7301 | 347 |

### Real process count

12 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_amazon_llama70b.py
scripts/rebuttal_experiment_amazon_qwen.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama31_8b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen72b.py
scripts/rebuttal_experiment_d_real_musique_llama31_8b.py
scripts/rebuttal_experiment_d_real_musique_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

- 15:46  up 42 days, 15:02, 1 user, load averages: 1.69 1.89 1.93
- CPU usage: 5.20% user, 10.87% sys, 83.91% idle 
PhysMem: 17G used (2790M wired, 7891M compressor), 102M unused.
- Assessment: not concerning

---

## Cycle 53 — 2026-07-26 16:03:24 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 16993 | 112 | 16787 | 206 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 19433 | 119 | 19357 | 76 |
| outputs/rebuttal/experiment_recipes | 7635 | 63 | 7526 | 109 |
| outputs/rebuttal/experiment_amazon | 7919 | 63 | 7648 | 271 |

### Real process count

12 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_amazon_llama70b.py
scripts/rebuttal_experiment_amazon_qwen.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama31_8b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen72b.py
scripts/rebuttal_experiment_d_real_musique_llama31_8b.py
scripts/rebuttal_experiment_d_real_musique_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

- 16:03  up 42 days, 15:19, 1 user, load averages: 1.48 1.81 1.91
- CPU usage: 3.22% user, 9.18% sys, 87.58% idle 
PhysMem: 17G used (2445M wired, 7513M compressor), 84M unused.
- Assessment: not concerning

---

## Cycle 54 — 2026-07-26 16:20:26 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 17256 | 112 | 16993 | 263 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 19534 | 119 | 19433 | 101 |
| outputs/rebuttal/experiment_recipes | 7738 | 63 | 7635 | 103 |
| outputs/rebuttal/experiment_amazon | 8214 | 63 | 7919 | 295 |

### Real process count

11 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_amazon_llama70b.py
scripts/rebuttal_experiment_amazon_qwen.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama31_8b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen72b.py
scripts/rebuttal_experiment_d_real_musique_llama31_8b.py
scripts/rebuttal_experiment_d_real_musique_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

- 16:20  up 42 days, 15:36, 1 user, load averages: 2.19 2.36 2.14
- CPU usage: 10.35% user, 10.70% sys, 78.94% idle 
PhysMem: 17G used (2653M wired, 7856M compressor), 139M unused.
- Assessment: not concerning

---

## Cycle 55 — 2026-07-26 16:37:27 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 17507 | 112 | 17256 | 251 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 19611 | 119 | 19534 | 77 |
| outputs/rebuttal/experiment_recipes | 7840 | 63 | 7738 | 102 |
| outputs/rebuttal/experiment_amazon | 8487 | 70 | 8214 | 273 |

### Real process count

10 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_amazon_llama70b.py
scripts/rebuttal_experiment_amazon_qwen.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama31_8b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen72b.py
scripts/rebuttal_experiment_d_real_musique_llama31_8b.py
scripts/rebuttal_experiment_d_real_musique_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

- 16:37  up 42 days, 15:53, 1 user, load averages: 2.33 2.68 2.58
- CPU usage: 10.48% user, 12.18% sys, 77.32% idle 
PhysMem: 17G used (2609M wired, 8066M compressor), 88M unused.
- Assessment: not concerning

---

## Cycle 56 — 2026-07-26 16:54:29 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 17751 | 112 | 17507 | 244 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 19706 | 119 | 19611 | 95 |
| outputs/rebuttal/experiment_recipes | 7946 | 63 | 7840 | 106 |
| outputs/rebuttal/experiment_amazon | 8753 | 70 | 8487 | 266 |

### Real process count

10 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_amazon_llama70b.py
scripts/rebuttal_experiment_amazon_qwen.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_llama31_8b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen72b.py
scripts/rebuttal_experiment_d_real_musique_llama31_8b.py
scripts/rebuttal_experiment_d_real_musique_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

- 16:54  up 42 days, 16:10, 1 user, load averages: 1.67 2.26 2.44
- CPU usage: 3.49% user, 9.50% sys, 86.99% idle 
PhysMem: 17G used (2543M wired, 6856M compressor), 134M unused.
- Assessment: not concerning

---

## Cycle 57 — 2026-07-26 17:11:31 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 17975 | 112 | 17751 | 224 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 19766 | 119 | 19706 | 60 |
| outputs/rebuttal/experiment_recipes | 8022 | 63 | 7946 | 76 |
| outputs/rebuttal/experiment_amazon | 9023 | 77 | 8753 | 270 |

### Real process count

8 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_amazon_llama70b.py
scripts/rebuttal_experiment_amazon_qwen.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen72b.py
scripts/rebuttal_experiment_d_real_musique_llama31_8b.py
scripts/rebuttal_experiment_d_real_musique_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

- 17:11  up 42 days, 16:27, 1 user, load averages: 1.99 1.87 2.00
- CPU usage: 4.24% user, 10.34% sys, 85.40% idle 
PhysMem: 17G used (2457M wired, 6578M compressor), 93M unused.
- Assessment: not concerning

---

## Cycle 58 — 2026-07-26 17:28:32 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 18132 | 112 | 17975 | 157 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 19777 | 119 | 19766 | 11 |
| outputs/rebuttal/experiment_recipes | 8098 | 63 | 8022 | 76 |
| outputs/rebuttal/experiment_amazon | 9225 | 77 | 9023 | 202 |

### Real process count

8 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_amazon_llama70b.py
scripts/rebuttal_experiment_amazon_qwen.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen72b.py
scripts/rebuttal_experiment_d_real_musique_llama31_8b.py
scripts/rebuttal_experiment_d_real_musique_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

- 17:28  up 42 days, 16:44, 1 user, load averages: 2.22 2.37 2.53
- CPU usage: 3.18% user, 9.43% sys, 87.38% idle 
PhysMem: 17G used (2892M wired, 7642M compressor), 83M unused.
- Assessment: not concerning

---

## Cycle 59 — 2026-07-26 17:45:34 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 18359 | 112 | 18132 | 227 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 19786 | 119 | 19777 | 9 |
| outputs/rebuttal/experiment_recipes | 8200 | 63 | 8098 | 102 |
| outputs/rebuttal/experiment_amazon | 9491 | 77 | 9225 | 266 |

### Real process count

8 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_amazon_llama70b.py
scripts/rebuttal_experiment_amazon_qwen.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen72b.py
scripts/rebuttal_experiment_d_real_musique_llama31_8b.py
scripts/rebuttal_experiment_d_real_musique_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

- 17:45  up 42 days, 17:01, 1 user, load averages: 2.12 2.11 2.22
- CPU usage: 1.89% user, 8.83% sys, 89.27% idle 
PhysMem: 17G used (2502M wired, 7492M compressor), 151M unused.
- Assessment: not concerning

---

## Cycle 60 — 2026-07-26 18:02:36 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 18591 | 112 | 18359 | 232 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 19800 | 119 | 19786 | 14 |
| outputs/rebuttal/experiment_recipes | 8297 | 63 | 8200 | 97 |
| outputs/rebuttal/experiment_amazon | 9767 | 77 | 9491 | 276 |

### Real process count

7 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_amazon_llama70b.py
scripts/rebuttal_experiment_amazon_qwen.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen72b.py
scripts/rebuttal_experiment_d_real_musique_llama31_8b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

- 18:02  up 42 days, 17:18, 1 user, load averages: 1.28 1.88 2.03
- CPU usage: 1.97% user, 8.82% sys, 89.20% idle 
PhysMem: 17G used (2477M wired, 7353M compressor), 92M unused.
- Assessment: not concerning

---

## Cycle 61 — 2026-07-26 18:19:38 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 18714 | 112 | 18591 | 123 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 19809 | 119 | 19800 | 9 |
| outputs/rebuttal/experiment_recipes | 8393 | 63 | 8297 | 96 |
| outputs/rebuttal/experiment_amazon | 9981 | 84 | 9767 | 214 |

### Real process count

7 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_amazon_llama70b.py
scripts/rebuttal_experiment_amazon_qwen.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen72b.py
scripts/rebuttal_experiment_d_real_musique_llama31_8b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

- 18:19  up 42 days, 17:36, 1 user, load averages: 1.70 2.68 2.31
- CPU usage: 3.97% user, 9.93% sys, 86.9% idle 
PhysMem: 17G used (2750M wired, 7808M compressor), 99M unused.
- Assessment: not concerning

---

## Cycle 62 — 2026-07-26 18:36:39 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 18814 | 112 | 18714 | 100 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 19857 | 140 | 19809 | 48 |
| outputs/rebuttal/experiment_recipes | 8530 | 63 | 8393 | 137 |
| outputs/rebuttal/experiment_amazon | 10206 | 84 | 9981 | 225 |

### Real process count

12 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_amazon_llama70b.py
scripts/rebuttal_experiment_amazon_qwen.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen72b.py
scripts/rebuttal_experiment_d_real_musique_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

- 18:36  up 42 days, 17:53, 1 user, load averages: 2.32 2.29 2.24
- CPU usage: 2.3% user, 9.23% sys, 88.73% idle 
PhysMem: 17G used (2480M wired, 8401M compressor), 96M unused.
- Assessment: not concerning

---

## Cycle 63 — 2026-07-26 18:53:41 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 18917 | 112 | 18814 | 103 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 19897 | 140 | 19857 | 40 |
| outputs/rebuttal/experiment_recipes | 8692 | 63 | 8530 | 162 |
| outputs/rebuttal/experiment_amazon | 10397 | 84 | 10206 | 191 |

### Real process count

12 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_amazon_llama70b.py
scripts/rebuttal_experiment_amazon_qwen.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen72b.py
scripts/rebuttal_experiment_d_real_musique_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

- 18:53  up 42 days, 18:10, 1 user, load averages: 1.54 1.76 2.04
- CPU usage: 14.19% user, 12.38% sys, 73.41% idle 
PhysMem: 17G used (2900M wired, 8801M compressor), 118M unused.
- Assessment: not concerning

---

## Cycle 64 — 2026-07-26 19:10:43 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 19016 | 112 | 18917 | 99 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 19914 | 140 | 19897 | 17 |
| outputs/rebuttal/experiment_recipes | 8900 | 63 | 8692 | 208 |
| outputs/rebuttal/experiment_amazon | 10601 | 84 | 10397 | 204 |

### Real process count

12 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_amazon_llama70b.py
scripts/rebuttal_experiment_amazon_qwen.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen72b.py
scripts/rebuttal_experiment_d_real_musique_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

- 19:10  up 42 days, 18:27, 1 user, load averages: 2.20 2.39 2.25
- CPU usage: 4.16% user, 11.62% sys, 84.20% idle 
PhysMem: 17G used (2611M wired, 7151M compressor), 83M unused.
- Assessment: not concerning

---

## Cycle 65 — 2026-07-26 19:27:45 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 19094 | 112 | 19016 | 78 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 19955 | 140 | 19914 | 41 |
| outputs/rebuttal/experiment_recipes | 9158 | 63 | 8900 | 258 |
| outputs/rebuttal/experiment_amazon | 10844 | 91 | 10601 | 243 |

### Real process count

12 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_amazon_llama70b.py
scripts/rebuttal_experiment_amazon_qwen.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen72b.py
scripts/rebuttal_experiment_d_real_musique_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

- 19:27  up 42 days, 18:44, 1 user, load averages: 3.30 3.29 2.78
- CPU usage: 5.48% user, 12.63% sys, 81.87% idle 
PhysMem: 17G used (2597M wired, 8117M compressor), 89M unused.
- Assessment: not concerning

---

## Cycle 66 — 2026-07-26 19:44:47 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 19115 | 112 | 19094 | 21 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20006 | 140 | 19955 | 51 |
| outputs/rebuttal/experiment_recipes | 9439 | 63 | 9158 | 281 |
| outputs/rebuttal/experiment_amazon | 11137 | 91 | 10844 | 293 |

### Real process count

12 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_amazon_llama70b.py
scripts/rebuttal_experiment_amazon_qwen.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen72b.py
scripts/rebuttal_experiment_d_real_musique_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

- 19:44  up 42 days, 19:01, 1 user, load averages: 3.53 3.18 2.74
- CPU usage: 4.85% user, 13.20% sys, 81.94% idle 
PhysMem: 17G used (2715M wired, 7984M compressor), 103M unused.
- Assessment: not concerning

---

## Cycle 67 — 2026-07-26 20:01:49 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 19192 | 112 | 19115 | 77 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20045 | 140 | 20006 | 39 |
| outputs/rebuttal/experiment_recipes | 9719 | 63 | 9439 | 280 |
| outputs/rebuttal/experiment_amazon | 11430 | 91 | 11137 | 293 |

### Real process count

12 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_amazon_llama70b.py
scripts/rebuttal_experiment_amazon_qwen.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen72b.py
scripts/rebuttal_experiment_d_real_musique_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

- 20:01  up 42 days, 19:18, 1 user, load averages: 1.95 2.01 2.43
- CPU usage: 6.14% user, 11.30% sys, 82.54% idle 
PhysMem: 17G used (2950M wired, 8579M compressor), 102M unused.
- Assessment: not concerning

---

## Cycle 68 — 2026-07-26 20:18:51 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 19291 | 112 | 19192 | 99 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20096 | 140 | 20045 | 51 |
| outputs/rebuttal/experiment_recipes | 9941 | 63 | 9719 | 222 |
| outputs/rebuttal/experiment_amazon | 11653 | 91 | 11430 | 223 |

### Real process count

12 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_amazon_llama70b.py
scripts/rebuttal_experiment_amazon_qwen.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen72b.py
scripts/rebuttal_experiment_d_real_musique_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

- 20:18  up 42 days, 19:35, 1 user, load averages: 2.54 2.25 2.21
- CPU usage: 4.57% user, 12.32% sys, 83.10% idle 
PhysMem: 17G used (2768M wired, 7580M compressor), 91M unused.
- Assessment: not concerning

---

## Cycle 69 — 2026-07-26 20:35:54 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 19338 | 112 | 19291 | 47 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20161 | 140 | 20096 | 65 |
| outputs/rebuttal/experiment_recipes | 10211 | 63 | 9941 | 270 |
| outputs/rebuttal/experiment_amazon | 11897 | 91 | 11653 | 244 |

### Real process count

14 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_amazon_llama70b.py
scripts/rebuttal_experiment_amazon_qwen.py
scripts/rebuttal_experiment_b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen72b.py
scripts/rebuttal_experiment_d_real_musique_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

- 20:35  up 42 days, 19:52, 1 user, load averages: 1.62 2.78 2.90
- CPU usage: 2.64% user, 10.13% sys, 87.21% idle 
PhysMem: 17G used (2938M wired, 7887M compressor), 89M unused.
- Assessment: not concerning

---

## Cycle 70 — 2026-07-26 20:52:56 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 19441 | 112 | 19338 | 103 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20207 | 140 | 20161 | 46 |
| outputs/rebuttal/experiment_recipes | 10462 | 70 | 10211 | 251 |
| outputs/rebuttal/experiment_amazon | 12139 | 91 | 11897 | 242 |

### Real process count

14 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_amazon_llama70b.py
scripts/rebuttal_experiment_amazon_qwen.py
scripts/rebuttal_experiment_b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen72b.py
scripts/rebuttal_experiment_d_real_musique_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

- 20:52  up 42 days, 20:09, 1 user, load averages: 2.75 3.19 2.99
- CPU usage: 12.16% user, 11.26% sys, 76.56% idle 
PhysMem: 17G used (2723M wired, 7752M compressor), 85M unused.
- Assessment: not concerning

---

## Cycle 71 — 2026-07-26 21:09:59 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 19509 | 112 | 19441 | 68 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20256 | 140 | 20207 | 49 |
| outputs/rebuttal/experiment_recipes | 10700 | 70 | 10462 | 238 |
| outputs/rebuttal/experiment_amazon | 12400 | 91 | 12139 | 261 |

### Real process count

14 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_amazon_llama70b.py
scripts/rebuttal_experiment_amazon_qwen.py
scripts/rebuttal_experiment_b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen72b.py
scripts/rebuttal_experiment_d_real_musique_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

- 21:10  up 42 days, 20:26, 1 user, load averages: 2.80 2.81 2.82
- CPU usage: 13.72% user, 10.77% sys, 75.49% idle 
PhysMem: 17G used (2759M wired, 8311M compressor), 123M unused.
- Assessment: not concerning

---

## Cycle 72 — 2026-07-26 21:27:01 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 19559 | 112 | 19509 | 50 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20310 | 140 | 20256 | 54 |
| outputs/rebuttal/experiment_recipes | 10939 | 70 | 10700 | 239 |
| outputs/rebuttal/experiment_amazon | 12661 | 98 | 12400 | 261 |

### Real process count

14 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_amazon_llama70b.py
scripts/rebuttal_experiment_amazon_qwen.py
scripts/rebuttal_experiment_b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen72b.py
scripts/rebuttal_experiment_d_real_musique_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

- 21:27  up 42 days, 20:43, 1 user, load averages: 3.50 3.34 3.16
- CPU usage: 3.10% user, 10.38% sys, 86.51% idle 
PhysMem: 17G used (2697M wired, 8724M compressor), 101M unused.
- Assessment: not concerning

---

## Cycle 73 — 2026-07-26 21:44:04 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 19649 | 112 | 19559 | 90 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20371 | 140 | 20310 | 61 |
| outputs/rebuttal/experiment_recipes | 11247 | 84 | 10939 | 308 |
| outputs/rebuttal/experiment_amazon | 12926 | 98 | 12661 | 265 |

### Real process count

13 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_amazon_llama70b.py
scripts/rebuttal_experiment_amazon_qwen.py
scripts/rebuttal_experiment_b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen72b.py
scripts/rebuttal_experiment_d_real_musique_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

- 21:44  up 42 days, 21 hrs, 1 user, load averages: 2.97 2.88 2.91
- CPU usage: 7.74% user, 13.69% sys, 78.56% idle 
PhysMem: 17G used (2999M wired, 8730M compressor), 91M unused.
- Assessment: not concerning

---

## Cycle 74 — 2026-07-26 22:01:07 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 19721 | 112 | 19649 | 72 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20407 | 140 | 20371 | 36 |
| outputs/rebuttal/experiment_recipes | 11490 | 84 | 11247 | 243 |
| outputs/rebuttal/experiment_amazon | 13174 | 98 | 12926 | 248 |

### Real process count

13 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_amazon_llama70b.py
scripts/rebuttal_experiment_amazon_qwen.py
scripts/rebuttal_experiment_b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen72b.py
scripts/rebuttal_experiment_d_real_musique_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

- 22:01  up 42 days, 21:17, 1 user, load averages: 3.08 3.65 3.36
- CPU usage: 14.83% user, 11.47% sys, 73.69% idle 
PhysMem: 17G used (2800M wired, 7605M compressor), 115M unused.
- Assessment: not concerning

---

## Cycle 75 — 2026-07-26 22:18:09 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 19798 | 112 | 19721 | 77 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20466 | 140 | 20407 | 59 |
| outputs/rebuttal/experiment_recipes | 11732 | 84 | 11490 | 242 |
| outputs/rebuttal/experiment_amazon | 13301 | 98 | 13174 | 127 |

### Real process count

11 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_amazon_llama70b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen72b.py
scripts/rebuttal_experiment_d_real_musique_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

- 22:18  up 42 days, 21:34, 1 user, load averages: 2.65 2.58 2.89
- CPU usage: 15.95% user, 14.39% sys, 69.65% idle 
PhysMem: 17G used (2793M wired, 8293M compressor), 123M unused.
- Assessment: not concerning

---

## Cycle 76 — 2026-07-26 22:35:12 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 19906 | 112 | 19798 | 108 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20534 | 140 | 20466 | 68 |
| outputs/rebuttal/experiment_recipes | 11992 | 84 | 11732 | 260 |
| outputs/rebuttal/experiment_amazon | 13426 | 98 | 13301 | 125 |

### Real process count

11 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_amazon_llama70b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen72b.py
scripts/rebuttal_experiment_d_real_musique_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

- 22:35  up 42 days, 21:51, 1 user, load averages: 2.14 3.22 3.26
- CPU usage: 6.66% user, 13.11% sys, 80.22% idle 
PhysMem: 17G used (2985M wired, 8097M compressor), 84M unused.
- Assessment: not concerning

---

## Cycle 77 — 2026-07-26 22:52:15 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 19972 | 112 | 19906 | 66 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20585 | 140 | 20534 | 51 |
| outputs/rebuttal/experiment_recipes | 12227 | 84 | 11992 | 235 |
| outputs/rebuttal/experiment_amazon | 13533 | 105 | 13426 | 107 |

### Real process count

11 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_amazon_llama70b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen72b.py
scripts/rebuttal_experiment_d_real_musique_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

- 22:52  up 42 days, 22:08, 1 user, load averages: 2.31 2.54 2.79
- CPU usage: 9.72% user, 17.63% sys, 72.63% idle 
PhysMem: 17G used (2824M wired, 8790M compressor), 92M unused.
- Assessment: not concerning

---

## Cycle 78 — 2026-07-26 23:09:17 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 19994 | 112 | 19972 | 22 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20638 | 140 | 20585 | 53 |
| outputs/rebuttal/experiment_recipes | 12441 | 84 | 12227 | 214 |
| outputs/rebuttal/experiment_amazon | 13669 | 105 | 13533 | 136 |

### Real process count

12 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_amazon_llama70b.py
scripts/rebuttal_experiment_c_nonsynthetic_multifault_qwen72b.py
scripts/rebuttal_experiment_d_real_musique_llama31_8b.py
scripts/rebuttal_experiment_personalwab.py
scripts/rebuttal_experiment_recipes_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

- 23:09  up 42 days, 22:25, 1 user, load averages: 3.04 2.90 2.75
- CPU usage: 10.16% user, 18.62% sys, 71.21% idle 
PhysMem: 17G used (2817M wired, 8346M compressor), 89M unused.
- Assessment: not concerning

---

## Cycle 79 — 2026-07-26 23:26:20 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 20014 | 112 | 19994 | 20 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20638 | 38 |
| outputs/rebuttal/experiment_recipes | 12625 | 91 | 12441 | 184 |
| outputs/rebuttal/experiment_amazon | 13764 | 105 | 13669 | 95 |

### Real process count

2 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama70b.py
scripts/rebuttal_experiment_recipes_llama70b.py
```

### System load

- 23:26  up 42 days, 22:42, 1 user, load averages: 2.25 2.52 2.59
- CPU usage: 7.34% user, 12.63% sys, 80.1% idle 
PhysMem: 17G used (2780M wired, 7611M compressor), 99M unused.
- Assessment: not concerning

### DISCREPANCY FLAGGED this cycle
- STALL: outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b has NOT grown (3294 -> 3294 rows) since previous cycle, and no live process pattern-matches this directory (checked: find "outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b" -name '*.jsonl' | xargs cat | wc -l ; ps aux | grep rebuttal_experiment).
- STALL: outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b has NOT grown (4620 -> 4620 rows) since previous cycle, and no live process pattern-matches this directory (checked: find "outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b" -name '*.jsonl' | xargs cat | wc -l ; ps aux | grep rebuttal_experiment).
- STALL: outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b has NOT grown (4609 -> 4609 rows) since previous cycle, and no live process pattern-matches this directory (checked: find "outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b" -name '*.jsonl' | xargs cat | wc -l ; ps aux | grep rebuttal_experiment).
- STALL: outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b has NOT grown (3765 -> 3765 rows) since previous cycle, and no live process pattern-matches this directory (checked: find "outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b" -name '*.jsonl' | xargs cat | wc -l ; ps aux | grep rebuttal_experiment).
- STALL: outputs/rebuttal/experiment_d/full_matrix_hotpotqa has NOT grown (15056 -> 15056 rows) since previous cycle, and no live process pattern-matches this directory (checked: find "outputs/rebuttal/experiment_d/full_matrix_hotpotqa" -name '*.jsonl' | xargs cat | wc -l ; ps aux | grep rebuttal_experiment).
- STALL: outputs/rebuttal/experiment_d/full_matrix_longmemeval has NOT grown (15097 -> 15097 rows) since previous cycle, and no live process pattern-matches this directory (checked: find "outputs/rebuttal/experiment_d/full_matrix_longmemeval" -name '*.jsonl' | xargs cat | wc -l ; ps aux | grep rebuttal_experiment).
- STALL: outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic has NOT grown (14924 -> 14924 rows) since previous cycle, and no live process pattern-matches this directory (checked: find "outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic" -name '*.jsonl' | xargs cat | wc -l ; ps aux | grep rebuttal_experiment).

### Cycle 79 ADDENDUM — direct verification of the 7 stall alerts (23:26-23:35 EDT)

Verdicts after checking file inventories, per-file row counts, log endings, and mtimes:

**NOT stalls — verified COMPLETE (orderly log endings, symmetric grids):**
- full_matrix/{qwen-2.5-7b, llama-3.1-8b, llama-3.3-70b}: 28 files each (7 methods x N=2-5), last writes Jul 25 21:06 - Jul 26 01:52.
- full_matrix_hotpotqa, full_matrix_longmemeval, full_matrix_travelplanner_synthetic: 21 files x 4 models each (7 methods x N=2-4), 3701-3780 rows/model, last writes 06:12-14:06 Jul 26.
- full_matrix_musique: 28 files x 4 models; 5040 rows (full) for mistral/qwen/llama70b. Finished 23:23-23:24.

**REAL discrepancies found:**
1. MASS 403 DIE-OFF at ~23:24:56 EDT: OpenRouter "Key limit exceeded (total limit)" (key 2b579e7f...) killed multiple runs simultaneously. Evidence: identical 403 retry-exhaustion endings, all logs last modified 23:24:56.
   - experiment_c qwen-2.5-72b extension: 28 files but only 1076 rows (~5040 expected) — died mid-run across all N levels.
   - experiment_recipes llama-3.1-8b: only N=1 done (7/35 files, 1063 rows); n1 log ends in 403 failure. No process, no wrapper -> will NOT resume on its own.
   - experiment_amazon llama-3.1-8b: N=1,2 complete with run summaries; N=3 log ends in 403 retries with NO run summary (21/28 files); N=4 never started. No process, no wrapper -> will NOT resume.
   - full_matrix_musique llama-3.1-8b: 4894/5040 rows — n5 truncated by 403s (~146 rows lost).
   - recipes mistral.log and qwen.log also contain 403s (grids show 35/35 files but mistral 4040 rows, qwen 5461 rows vs 6300 theoretical max — possible row shortfall).
2. full_matrix/mistral-nemo-12b (2wiki): only 20/28 files — intro_specter and reflexion arms ABSENT at all N levels (siblings have them); n5 files 120 rows vs 180 elsewhere. Logs end with clean per-arm summaries, so what ran finished — but the matrix is structurally incomplete vs the other 3 models.

**Still alive and writing (verified via ps + fresh mtimes 23:27+):**
- recipes llama70b N=2 (PID 35067; zsh wrapper 62782 will chain N=3-5)
- amazon llama70b N=4 (PID 24883)
- personalwab qwen-2.5-7b-together (PID 10035, Together API — not affected by the OpenRouter key limit; NEW dir outputs/rebuttal/experiment_personalwab/ now added to tracking)
Note: the two OpenRouter-based survivors were still writing rows at 23:27, after the 23:24:56 die-off — the key limit appears to bite intermittently; watch for 403s in their logs.

Watchdog updated: complete dirs suppressed from repeat stall alerts, stall alerts now fire on transition only (with recovery notices), personalwab tracked, ps pattern fixed to catch "Python -u", and a 403-storm detector added.

---

## Cycle 80 — 2026-07-26 23:32:21 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20014 | 112 | 20014 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 12654 | 91 | 12625 | 29 |
| outputs/rebuttal/experiment_amazon | 13794 | 105 | 13764 | 30 |
| outputs/rebuttal/experiment_personalwab | 542 | 20 | n/a | n/a |

### Real process count

3 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama70b.py
scripts/rebuttal_experiment_personalwab.py
scripts/rebuttal_experiment_recipes_llama70b.py
```

### System load

- 23:32  up 42 days, 22:48, 1 user, load averages: 2.07 2.35 2.50
- CPU usage: 3.81% user, 10.27% sys, 85.90% idle 
PhysMem: 17G used (2661M wired, 6253M compressor), 89M unused.
- Assessment: not concerning
- 403s active in: outputs/rebuttal/experiment_amazon/logs/llama31_8b_n3.log outputs/rebuttal/experiment_recipes/logs/qwen.log outputs/rebuttal/experiment_recipes/logs/llama31_8b_n1.log outputs/rebuttal/experiment_recipes/logs/mistral.log outputs/rebuttal/experiment_c/nonsynthetic_multifault/logs_qwen72b_n4.log outputs/rebuttal/experiment_c/nonsynthetic_multifault/logs_qwen72b_n5.log outputs/rebuttal/experiment_c/nonsynthetic_multifault/logs_qwen72b_n2.log outputs/rebuttal/experiment_c/nonsynthetic_multifault/logs_qwen72b_n3.log outputs/rebuttal/experiment_d/logs_musique/llama31_8b_n5.log outputs/rebuttal/experiment_personalwab/llama-3.1-8b.log outputs/rebuttal/experiment_personalwab/mistral-nemo-12b.log outputs/rebuttal/experiment_personalwab/qwen-2.5-7b.log 

### DISCREPANCY FLAGGED this cycle
- 403 STORM STARTED: OpenRouter 'Key limit exceeded' appearing in recently-active logs: outputs/rebuttal/experiment_amazon/logs/llama31_8b_n3.log outputs/rebuttal/experiment_recipes/logs/qwen.log outputs/rebuttal/experiment_recipes/logs/llama31_8b_n1.log outputs/rebuttal/experiment_recipes/logs/mistral.log outputs/rebuttal/experiment_c/nonsynthetic_multifault/logs_qwen72b_n4.log outputs/rebuttal/experiment_c/nonsynthetic_multifault/logs_qwen72b_n5.log outputs/rebuttal/experiment_c/nonsynthetic_multifault/logs_qwen72b_n2.log outputs/rebuttal/experiment_c/nonsynthetic_multifault/logs_qwen72b_n3.log outputs/rebuttal/experiment_d/logs_musique/llama31_8b_n5.log outputs/rebuttal/experiment_personalwab/llama-3.1-8b.log outputs/rebuttal/experiment_personalwab/mistral-nemo-12b.log outputs/rebuttal/experiment_personalwab/qwen-2.5-7b.log 

---

## Cycle 81 — 2026-07-26 23:49:24 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20014 | 112 | 20014 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 12760 | 91 | 12654 | 106 |
| outputs/rebuttal/experiment_amazon | 13889 | 105 | 13794 | 95 |
| outputs/rebuttal/experiment_personalwab | 908 | 20 | 542 | 366 |

### Real process count

3 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama70b.py
scripts/rebuttal_experiment_personalwab.py
scripts/rebuttal_experiment_recipes_llama70b.py
```

### System load

- 23:49  up 42 days, 23:05, 1 user, load averages: 10.41 8.94 6.22
- CPU usage: 21.2% user, 11.27% sys, 67.69% idle 
PhysMem: 17G used (2837M wired, 8002M compressor), 88M unused.
- Assessment: not concerning
- 403s active in: outputs/rebuttal/experiment_amazon/logs/llama31_8b_n3.log outputs/rebuttal/experiment_recipes/logs/llama31_8b_n1.log outputs/rebuttal/experiment_recipes/logs/mistral.log outputs/rebuttal/experiment_c/nonsynthetic_multifault/logs_qwen72b_n4.log outputs/rebuttal/experiment_c/nonsynthetic_multifault/logs_qwen72b_n5.log outputs/rebuttal/experiment_c/nonsynthetic_multifault/logs_qwen72b_n2.log outputs/rebuttal/experiment_c/nonsynthetic_multifault/logs_qwen72b_n3.log 

---

## Cycle 82 — 2026-07-27 00:06:27 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20014 | 112 | 20014 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 12844 | 91 | 12760 | 84 |
| outputs/rebuttal/experiment_amazon | 13954 | 105 | 13889 | 65 |
| outputs/rebuttal/experiment_personalwab | 1188 | 20 | 908 | 280 |

### Real process count

2 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama70b.py
scripts/rebuttal_experiment_recipes_llama70b.py
```

### System load

-  0:06  up 42 days, 23:22, 1 user, load averages: 4.52 4.77 4.76
- CPU usage: 9.73% user, 12.70% sys, 77.55% idle 
PhysMem: 17G used (2908M wired, 7394M compressor), 183M unused.
- Assessment: not concerning

### DISCREPANCY FLAGGED this cycle
- 403 storm cleared: no 'Key limit exceeded' in logs modified in last 25 min.

### Cycle 82 ADDENDUM — 403 clearance independently verified (00:06 EDT Jul 27)

Watchdog claimed "403 storm cleared". Verified directly, NOT trusting the claim:
- 0 logs under outputs/rebuttal modified in last 30 min contain "Key limit exceeded".
- Fresh SUCCESSFUL rows written 00:05-00:06: experiment_amazon/llama-3.3-70b n4 files (all 7 arms) and experiment_recipes/llama-3.3-70b n2 files — actual completed API round-trips, not just retries.
- Survivor log tails show clean per-task progress lines (resolved faults, token counts), no 403s.
- Live: amazon llama70b N=4 (PID 24883), recipes llama70b N=2 (PID 35067, wrapper chains N=3-5), personalwab qwen-together (PID 10035).

CONCLUSION: OpenRouter key is genuinely working again as of ~23:27 Jul 26 onward (survivors never fully stopped). The 4 dead runs from the 23:24:56 die-off (experiment_c qwen-2.5-72b; recipes llama-3.1-8b N=2-5; amazon llama-3.1-8b N=3-4; musique llama-3.1-8b n5 tail) remain dead and still need manual relaunch.

---

## Cycle 83 — 2026-07-27 00:23:29 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20014 | 112 | 20014 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 12938 | 91 | 12844 | 94 |
| outputs/rebuttal/experiment_amazon | 14039 | 105 | 13954 | 85 |
| outputs/rebuttal/experiment_personalwab | 1188 | 20 | 1188 | 0 |

### Real process count

2 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama70b.py
scripts/rebuttal_experiment_recipes_llama70b.py
```

### System load

-  0:23  up 42 days, 23:39, 1 user, load averages: 1.59 1.90 2.82
- CPU usage: 4.84% user, 10.27% sys, 84.88% idle 
PhysMem: 17G used (2699M wired, 7692M compressor), 95M unused.
- Assessment: not concerning

### DISCREPANCY FLAGGED this cycle
- STALL: outputs/rebuttal/experiment_personalwab has NOT grown (1188 -> 1188 rows) since previous cycle, and no live process pattern-matches this directory (checked: find + ps aux).

### Cycle 83 ADDENDUM — personalwab "stall" verified as COMPLETION (00:23 EDT Jul 27)

- Runner PID 10035 (qwen-2.5-7b-together) exited; log ends with clean "--- run summary --- rows written: 890 errors: 0" (log shows 890 written; dir contains 900 rows across 5 files — 60 tasks x 3 seeds x 5 arms = 900 full grid; small delta likely pre-existing rows).
- Watcher PID 10245 fired as designed: aggregate_personalwab.py ran at 00:08:43, aggregate_run.log contains final per-arm result tables (direct/reflexion/violation_reprompt/iter_vrp, n=180 each).
- The three OpenRouter-based personalwab subdirs (llama-3.1-8b 53 rows, mistral-nemo-12b 100, qwen-2.5-7b 135; last writes 23:18-23:19 Jul 26) remain small/partial from the 403 era — superseded by the Together rerun for qwen; llama31/mistral personalwab runs are incomplete if anyone intends to use them.
- Verdict: NOT a stall. experiment_personalwab added to verified-complete suppress list.

---

## Cycle 84 — 2026-07-27 00:40:32 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20014 | 112 | 20014 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 13046 | 91 | 12938 | 108 |
| outputs/rebuttal/experiment_amazon | 14134 | 105 | 14039 | 95 |
| outputs/rebuttal/experiment_personalwab (complete) | 1188 | 20 | 1188 | 0 |

### Real process count

2 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama70b.py
scripts/rebuttal_experiment_recipes_llama70b.py
```

### System load

-  0:40  up 42 days, 23:56, 1 user, load averages: 7.62 5.04 3.67
- CPU usage: 10.61% user, 15.77% sys, 73.61% idle 
PhysMem: 17G used (3011M wired, 8171M compressor), 141M unused.
- Assessment: not concerning

---

## Cycle 85 — 2026-07-27 00:57:35 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20060 | 112 | 20014 | 46 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 13227 | 98 | 13046 | 181 |
| outputs/rebuttal/experiment_amazon | 14222 | 105 | 14134 | 88 |
| outputs/rebuttal/experiment_personalwab (complete) | 1473 | 20 | 1188 | 285 |

### Real process count

7 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_d_real_musique_llama31_8b.py
scripts/rebuttal_experiment_personalwab.py
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

-  0:57  up 43 days, 13 mins, 1 user, load averages: 4.36 4.33 4.29
- CPU usage: 7.68% user, 14.66% sys, 77.64% idle 
PhysMem: 17G used (2805M wired, 8104M compressor), 91M unused.
- Assessment: not concerning
- 403s active in: outputs/rebuttal/experiment_d/logs_musique/llama31_8b_n5.log outputs/rebuttal/experiment_personalwab/llama-3.1-8b.log outputs/rebuttal/experiment_personalwab/mistral-nemo-12b.log 

### DISCREPANCY FLAGGED this cycle
- 403 STORM STARTED: OpenRouter 'Key limit exceeded' appearing in recently-active logs: outputs/rebuttal/experiment_d/logs_musique/llama31_8b_n5.log outputs/rebuttal/experiment_personalwab/llama-3.1-8b.log outputs/rebuttal/experiment_personalwab/mistral-nemo-12b.log 

### Cycle 85 ADDENDUM — 403 alert verified: RELAUNCHES DETECTED, detector partly false-positive (00:57 EDT Jul 27)

Direct verification of the "403 STORM STARTED" alert:
- The flagged personalwab llama-3.1-8b / mistral-nemo-12b logs contain 0 "Key limit exceeded" in their last 100 lines — the alert matched OLD 403 lines from the 23:24 die-off era in logs that are now being appended to again. Detector flaw, fixed in v3 (per-file count-increase detection).
- musique llama31_8b_n5.log: REAL intermittent 403s (23 of last 100 lines) BUT retries are succeeding — tail shows completed tasks (e.g. intro_specter 5/5 resolved).

MAJOR STATUS CHANGE verified via ps: the dead runs have been RELAUNCHED. 7 live processes:
- recipes llama70b N=3 (chain progressing), recipes qwen N=5, recipes mistral N=5
- musique llama31_8b N=5 (the truncated tail rerun)
- amazon llama31_8b N=3 (writing fresh rows 00:55-00:56, verified)
- personalwab llama-3.1-8b and mistral-nemo-12b (both writing successful tasks)
Still NOT relaunched: experiment_c qwen-2.5-72b (no process, 1076/5040 rows).
Survivors amazon llama70b N=4 + recipes runs: 0 403s in last 50 log lines.

full_matrix_musique and experiment_personalwab removed from the verified-complete suppress list (active again). Watchdog restarted as v3.

---

## Cycle 86 — 2026-07-27 00:59:33 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 20073 | 112 | 20060 | 13 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 13258 | 98 | 13227 | 31 |
| outputs/rebuttal/experiment_amazon | 14231 | 105 | 14222 | 9 |
| outputs/rebuttal/experiment_personalwab | 1530 | 20 | 1473 | 57 |

### Real process count

7 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_d_real_musique_llama31_8b.py
scripts/rebuttal_experiment_personalwab.py
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

-  0:59  up 43 days, 15 mins, 1 user, load averages: 3.24 3.95 4.14
- CPU usage: 6.83% user, 14.55% sys, 78.61% idle 
PhysMem: 17G used (2781M wired, 7607M compressor), 89M unused.
- Assessment: not concerning

### DISCREPANCY FLAGGED this cycle
- RECOVERED: outputs/rebuttal/experiment_personalwab is growing again (1473 -> 1530 rows).

---

## Cycle 87 — 2026-07-27 01:16:36 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 20142 | 112 | 20073 | 69 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 13396 | 98 | 13258 | 138 |
| outputs/rebuttal/experiment_amazon | 14267 | 105 | 14231 | 36 |
| outputs/rebuttal/experiment_personalwab | 1963 | 20 | 1530 | 433 |

### Real process count

7 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_d_real_musique_llama31_8b.py
scripts/rebuttal_experiment_personalwab.py
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

-  1:16  up 43 days, 32 mins, 1 user, load averages: 2.84 3.52 3.70
- CPU usage: 11.18% user, 16.95% sys, 71.86% idle 
PhysMem: 17G used (2840M wired, 8037M compressor), 95M unused.
- Assessment: not concerning

---

## Cycle 88 — 2026-07-27 01:33:39 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 20158 | 112 | 20142 | 16 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 13539 | 98 | 13396 | 143 |
| outputs/rebuttal/experiment_amazon | 14325 | 105 | 14267 | 58 |
| outputs/rebuttal/experiment_personalwab | 2339 | 20 | 1963 | 376 |

### Real process count

6 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_personalwab.py
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

-  1:33  up 43 days, 50 mins, 1 user, load averages: 3.12 2.82 3.03
- CPU usage: 7.85% user, 15.12% sys, 77.2% idle 
PhysMem: 17G used (2806M wired, 7375M compressor), 90M unused.
- Assessment: not concerning

---

## Cycle 89 — 2026-07-27 01:50:41 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 13721 | 98 | 13539 | 182 |
| outputs/rebuttal/experiment_amazon | 14364 | 105 | 14325 | 39 |
| outputs/rebuttal/experiment_personalwab | 2599 | 20 | 2339 | 260 |

### Real process count

5 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_personalwab.py
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

-  1:50  up 43 days,  1:07, 1 user, load averages: 4.51 3.63 3.16
- CPU usage: 8.15% user, 14.51% sys, 77.33% idle 
PhysMem: 17G used (2793M wired, 7992M compressor), 95M unused.
- Assessment: not concerning

### DISCREPANCY FLAGGED this cycle
- STALL: outputs/rebuttal/experiment_d/full_matrix_musique has NOT grown (20158 -> 20158 rows) since previous cycle, and no live process pattern-matches this directory (checked: find + ps aux).

### Cycle 89 ADDENDUM — musique "stall" verified as COMPLETION of the rerun (01:50 EDT Jul 27)

- full_matrix_musique/llama-3.1-8b now 5038/5040 rows; n5 grid full (6 files x 180, selfcheckgpt 179 — matches "errors: 1" in run summary).
- logs_musique/llama31_8b_n5.log ends with clean "--- run summary (N=5) --- rows written: 144 errors: 1" at 01:18:54 — the 403-truncated tail was successfully backfilled by the rerun.
- Verdict: NOT a stall. full_matrix_musique re-added to verified-complete list (all 4 models now at/near 5040).
- BONUS verification: personalwab mistral-nemo-12b rerun also finished cleanly at 01:47:43 ("rows written: 800 errors: 0"; dir now at full 900-row grid). personalwab llama-3.1-8b still running.

---

## Cycle 90 — 2026-07-27 02:07:44 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 13926 | 98 | 13721 | 205 |
| outputs/rebuttal/experiment_amazon | 14404 | 105 | 14364 | 40 |
| outputs/rebuttal/experiment_personalwab | 2734 | 20 | 2599 | 135 |

### Real process count

5 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_personalwab.py
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

-  2:07  up 43 days,  1:24, 1 user, load averages: 1.81 1.94 2.38
- CPU usage: 1.91% user, 9.18% sys, 88.89% idle 
PhysMem: 17G used (2685M wired, 7587M compressor), 88M unused.
- Assessment: not concerning

---

## Cycle 91 — 2026-07-27 02:24:47 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 14104 | 98 | 13926 | 178 |
| outputs/rebuttal/experiment_amazon | 14446 | 105 | 14404 | 42 |
| outputs/rebuttal/experiment_personalwab | 2835 | 20 | 2734 | 101 |

### Real process count

4 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

-  2:24  up 43 days,  1:41, 1 user, load averages: 1.48 1.74 1.97
- CPU usage: 2.68% user, 9.78% sys, 87.52% idle 
PhysMem: 17G used (2666M wired, 7809M compressor), 101M unused.
- Assessment: not concerning

---

## Cycle 92 — 2026-07-27 02:41:49 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 14235 | 98 | 14104 | 131 |
| outputs/rebuttal/experiment_amazon | 14487 | 105 | 14446 | 41 |
| outputs/rebuttal/experiment_personalwab | 2835 | 20 | 2835 | 0 |

### Real process count

4 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

-  2:41  up 43 days,  1:58, 1 user, load averages: 1.58 1.92 2.04
- CPU usage: 5.97% user, 12.80% sys, 81.21% idle 
PhysMem: 17G used (2664M wired, 8408M compressor), 144M unused.
- Assessment: not concerning

### DISCREPANCY FLAGGED this cycle
- STALL: outputs/rebuttal/experiment_personalwab has NOT grown (2835 -> 2835 rows) since previous cycle, and no live process pattern-matches this directory (checked: find + ps aux).

### Cycle 92 ADDENDUM — personalwab "stall" verified as COMPLETION (02:42 EDT Jul 27)

- personalwab llama-3.1-8b run ended cleanly at 02:13:50: "--- run summary --- rows written: 847 errors: 0"; dir at full 900-row grid.
- personalwab now: llama-3.1-8b 900, mistral-nemo-12b 900, qwen-2.5-7b-together 900 — all complete. qwen-2.5-7b (OpenRouter) remains partial at 135 rows, superseded by the Together rerun.
- NOTE for coordinator: aggregate_run.log was last generated 00:08:43 — BEFORE the llama31 and mistral completions. The aggregated personalwab tables cover only the qwen-together run; aggregate_personalwab.py needs a rerun to include the two new models. (Watchdog will not run it — observation only.)
- Verdict: NOT a stall. experiment_personalwab re-added to verified-complete list.

---

## Cycle 93 — 2026-07-27 02:58:52 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 14375 | 98 | 14235 | 140 |
| outputs/rebuttal/experiment_amazon | 14529 | 105 | 14487 | 42 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

4 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

-  2:58  up 43 days,  2:15, 1 user, load averages: 2.06 1.98 2.06
- CPU usage: 3.38% user, 10.22% sys, 86.39% idle 
PhysMem: 17G used (2671M wired, 8434M compressor), 102M unused.
- Assessment: not concerning

---

## Cycle 94 — 2026-07-27 03:15:55 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 14558 | 98 | 14375 | 183 |
| outputs/rebuttal/experiment_amazon | 14578 | 105 | 14529 | 49 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

4 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

-  3:15  up 43 days,  2:32, 1 user, load averages: 2.04 2.03 2.00
- CPU usage: 2.61% user, 9.51% sys, 87.86% idle 
PhysMem: 17G used (2760M wired, 8622M compressor), 101M unused.
- Assessment: not concerning

---

## Cycle 95 — 2026-07-27 03:32:57 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 14735 | 98 | 14558 | 177 |
| outputs/rebuttal/experiment_amazon | 14613 | 105 | 14578 | 35 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

4 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

-  3:32  up 43 days,  2:49, 1 user, load averages: 1.68 1.88 1.93
- CPU usage: 4.5% user, 11.50% sys, 84.43% idle 
PhysMem: 17G used (2886M wired, 8870M compressor), 88M unused.
- Assessment: not concerning

---

## Cycle 96 — 2026-07-27 03:50:00 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 14911 | 98 | 14735 | 176 |
| outputs/rebuttal/experiment_amazon | 14632 | 105 | 14613 | 19 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

4 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

-  3:50  up 43 days,  3:06, 1 user, load averages: 2.13 2.15 2.21
- CPU usage: 2.98% user, 9.68% sys, 87.33% idle 
PhysMem: 17G used (2672M wired, 8804M compressor), 107M unused.
- Assessment: not concerning

---

## Cycle 97 — 2026-07-27 04:07:03 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 15056 | 98 | 14911 | 145 |
| outputs/rebuttal/experiment_amazon | 14661 | 105 | 14632 | 29 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

4 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

-  4:07  up 43 days,  3:23, 1 user, load averages: 2.45 2.09 2.26
- CPU usage: 2.50% user, 9.59% sys, 87.89% idle 
PhysMem: 17G used (2660M wired, 8899M compressor), 90M unused.
- Assessment: not concerning

---

## Cycle 98 — 2026-07-27 04:24:05 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 15217 | 98 | 15056 | 161 |
| outputs/rebuttal/experiment_amazon | 14698 | 105 | 14661 | 37 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

4 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

-  4:24  up 43 days,  3:40, 1 user, load averages: 2.37 2.35 2.41
- CPU usage: 3.1% user, 10.6% sys, 86.92% idle 
PhysMem: 17G used (2733M wired, 8549M compressor), 88M unused.
- Assessment: not concerning

---

## Cycle 99 — 2026-07-27 04:41:08 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 15393 | 98 | 15217 | 176 |
| outputs/rebuttal/experiment_amazon | 14741 | 105 | 14698 | 43 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

4 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
scripts/rebuttal_experiment_recipes_qwen.py
```

### System load

-  4:41  up 43 days,  3:57, 1 user, load averages: 1.38 1.62 1.86
- CPU usage: 2.9% user, 9.26% sys, 88.64% idle 
PhysMem: 17G used (2673M wired, 8928M compressor), 92M unused.
- Assessment: not concerning

---

## Cycle 100 — 2026-07-27 04:58:11 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 15549 | 98 | 15393 | 156 |
| outputs/rebuttal/experiment_amazon | 14784 | 105 | 14741 | 43 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

3 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
```

### System load

-  4:58  up 43 days,  4:14, 1 user, load averages: 4.06 2.83 2.38
- CPU usage: 2.26% user, 10.39% sys, 87.34% idle 
PhysMem: 17G used (2648M wired, 8481M compressor), 92M unused.
- Assessment: not concerning

---

## Cycle 101 — 2026-07-27 05:15:13 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 15628 | 98 | 15549 | 79 |
| outputs/rebuttal/experiment_amazon | 14819 | 105 | 14784 | 35 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

3 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
```

### System load

-  5:15  up 43 days,  4:31, 1 user, load averages: 2.03 2.13 2.07
- CPU usage: 2.68% user, 9.56% sys, 87.75% idle 
PhysMem: 17G used (2731M wired, 8621M compressor), 97M unused.
- Assessment: not concerning

---

## Cycle 102 — 2026-07-27 05:32:16 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 15727 | 98 | 15628 | 99 |
| outputs/rebuttal/experiment_amazon | 14849 | 105 | 14819 | 30 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

3 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
```

### System load

-  5:32  up 43 days,  4:48, 1 user, load averages: 2.05 1.92 2.05
- CPU usage: 2.81% user, 9.56% sys, 87.61% idle 
PhysMem: 17G used (2663M wired, 8513M compressor), 102M unused.
- Assessment: not concerning

---

## Cycle 103 — 2026-07-27 05:49:19 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 15840 | 105 | 15727 | 113 |
| outputs/rebuttal/experiment_amazon | 14913 | 105 | 14849 | 64 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

3 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
```

### System load

-  5:49  up 43 days,  5:05, 1 user, load averages: 2.25 3.25 2.74
- CPU usage: 10.63% user, 22.32% sys, 67.3% idle 
PhysMem: 17G used (2669M wired, 8727M compressor), 101M unused.
- Assessment: not concerning

---

## Cycle 104 — 2026-07-27 06:06:22 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 15932 | 105 | 15840 | 92 |
| outputs/rebuttal/experiment_amazon | 14947 | 105 | 14913 | 34 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

3 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
```

### System load

-  6:06  up 43 days,  5:22, 1 user, load averages: 1.72 1.90 2.21
- CPU usage: 2.38% user, 9.94% sys, 87.66% idle 
PhysMem: 17G used (2677M wired, 8372M compressor), 107M unused.
- Assessment: not concerning

---

## Cycle 105 — 2026-07-27 06:23:25 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 15991 | 105 | 15932 | 59 |
| outputs/rebuttal/experiment_amazon | 14987 | 105 | 14947 | 40 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

3 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
```

### System load

-  6:23  up 43 days,  5:39, 1 user, load averages: 2.03 1.95 2.02
- CPU usage: 2.41% user, 9.49% sys, 88.8% idle 
PhysMem: 17G used (2653M wired, 8246M compressor), 93M unused.
- Assessment: not concerning

---

## Cycle 106 — 2026-07-27 06:40:27 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 16112 | 105 | 15991 | 121 |
| outputs/rebuttal/experiment_amazon | 15029 | 105 | 14987 | 42 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

3 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
```

### System load

-  6:40  up 43 days,  5:56, 1 user, load averages: 1.82 1.59 1.73
- CPU usage: 2.38% user, 9.68% sys, 87.92% idle 
PhysMem: 17G used (2672M wired, 8379M compressor), 95M unused.
- Assessment: not concerning

---

## Cycle 107 — 2026-07-27 06:57:30 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 16247 | 105 | 16112 | 135 |
| outputs/rebuttal/experiment_amazon | 15076 | 105 | 15029 | 47 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

3 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
```

### System load

-  6:57  up 43 days,  6:13, 1 user, load averages: 1.36 1.74 1.80
- CPU usage: 2.28% user, 9.91% sys, 87.80% idle 
PhysMem: 17G used (2671M wired, 8710M compressor), 93M unused.
- Assessment: not concerning

---

## Cycle 108 — 2026-07-27 07:14:33 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 16351 | 105 | 16247 | 104 |
| outputs/rebuttal/experiment_amazon | 15098 | 105 | 15076 | 22 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

3 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
```

### System load

-  7:14  up 43 days,  6:30, 1 user, load averages: 1.54 1.88 1.88
- CPU usage: 2.55% user, 9.59% sys, 87.85% idle 
PhysMem: 17G used (2675M wired, 8589M compressor), 97M unused.
- Assessment: not concerning

---

## Cycle 109 — 2026-07-27 07:31:35 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 16461 | 105 | 16351 | 110 |
| outputs/rebuttal/experiment_amazon | 15141 | 112 | 15098 | 43 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

3 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
```

### System load

-  7:31  up 43 days,  6:47, 1 user, load averages: 1.76 1.69 1.71
- CPU usage: 2.45% user, 9.36% sys, 88.17% idle 
PhysMem: 17G used (2654M wired, 8297M compressor), 93M unused.
- Assessment: not concerning

---

## Cycle 110 — 2026-07-27 07:48:38 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 16564 | 105 | 16461 | 103 |
| outputs/rebuttal/experiment_amazon | 15167 | 112 | 15141 | 26 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

3 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
```

### System load

-  7:48  up 43 days,  7:05, 1 user, load averages: 3.70 2.92 2.26
- CPU usage: 3.82% user, 10.16% sys, 86.1% idle 
PhysMem: 17G used (2754M wired, 8411M compressor), 91M unused.
- Assessment: not concerning

---

## Cycle 111 — 2026-07-27 08:05:41 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 16640 | 105 | 16564 | 76 |
| outputs/rebuttal/experiment_amazon | 15224 | 112 | 15167 | 57 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

3 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
```

### System load

-  8:05  up 43 days,  7:22, 1 user, load averages: 1.58 2.21 2.17
- CPU usage: 2.73% user, 9.50% sys, 87.75% idle 
PhysMem: 17G used (2661M wired, 8016M compressor), 90M unused.
- Assessment: not concerning

---

## Cycle 112 — 2026-07-27 08:22:44 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 16716 | 105 | 16640 | 76 |
| outputs/rebuttal/experiment_amazon | 15264 | 112 | 15224 | 40 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

3 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
```

### System load

-  8:22  up 43 days,  7:39, 1 user, load averages: 2.09 2.58 2.34
- CPU usage: 2.14% user, 9.53% sys, 88.32% idle 
PhysMem: 17G used (2660M wired, 8443M compressor), 95M unused.
- Assessment: not concerning

---

## Cycle 113 — 2026-07-27 08:39:46 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 16805 | 105 | 16716 | 89 |
| outputs/rebuttal/experiment_amazon | 15301 | 112 | 15264 | 37 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

3 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
```

### System load

-  8:39  up 43 days,  7:56, 1 user, load averages: 1.80 2.07 2.16
- CPU usage: 5.61% user, 10.73% sys, 83.65% idle 
PhysMem: 17G used (2672M wired, 8355M compressor), 89M unused.
- Assessment: not concerning

---

## Cycle 114 — 2026-07-27 08:56:49 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 16888 | 105 | 16805 | 83 |
| outputs/rebuttal/experiment_amazon | 15328 | 112 | 15301 | 27 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

3 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
```

### System load

-  8:56  up 43 days,  8:13, 1 user, load averages: 2.34 2.59 2.45
- CPU usage: 3.31% user, 10.12% sys, 86.55% idle 
PhysMem: 17G used (2658M wired, 8094M compressor), 147M unused.
- Assessment: not concerning

---

## Cycle 115 — 2026-07-27 09:13:52 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 16986 | 105 | 16888 | 98 |
| outputs/rebuttal/experiment_amazon | 15370 | 112 | 15328 | 42 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

3 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
```

### System load

-  9:13  up 43 days,  8:30, 1 user, load averages: 1.72 2.31 2.32
- CPU usage: 2.34% user, 9.55% sys, 88.9% idle 
PhysMem: 17G used (2671M wired, 8670M compressor), 101M unused.
- Assessment: not concerning

---

## Cycle 116 — 2026-07-27 09:30:55 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 17072 | 105 | 16986 | 86 |
| outputs/rebuttal/experiment_amazon | 15398 | 112 | 15370 | 28 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

3 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
```

### System load

-  9:30  up 43 days,  8:47, 1 user, load averages: 1.98 1.77 1.88
- CPU usage: 2.87% user, 10.0% sys, 87.11% idle 
PhysMem: 17G used (2660M wired, 8535M compressor), 95M unused.
- Assessment: not concerning

---

## Cycle 117 — 2026-07-27 11:13:29 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 17123 | 105 | 17072 | 51 |
| outputs/rebuttal/experiment_amazon | 15424 | 112 | 15398 | 26 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

6 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_amazon_llama31_8b.py
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
```

### System load

- 11:13  up 43 days, 10:29, 1 user, load averages: 1.88 4.75 4.16
- CPU usage: 2.47% user, 10.43% sys, 87.8% idle 
PhysMem: 17G used (3024M wired, 8417M compressor), 99M unused.
- Assessment: not concerning

---

## Cycle 118 — 2026-07-27 11:30:31 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 17255 | 105 | 17123 | 132 |
| outputs/rebuttal/experiment_amazon | 15450 | 112 | 15424 | 26 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

2 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_recipes_llama70b.py
```

### System load

- 11:30  up 43 days, 10:46, 1 user, load averages: 1.70 1.81 2.58
- CPU usage: 5.70% user, 10.31% sys, 83.98% idle 
PhysMem: 17G used (2997M wired, 8146M compressor), 450M unused.
- Assessment: not concerning

---

## Cycle 119 — 2026-07-27 11:47:34 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 17410 | 105 | 17255 | 155 |
| outputs/rebuttal/experiment_amazon | 15450 | 112 | 15450 | 0 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

2 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_recipes_llama70b.py
```

### System load

- 11:47  up 43 days, 11:03, 1 user, load averages: 5.08 3.49 3.08
- CPU usage: 2.60% user, 14.4% sys, 83.35% idle 
PhysMem: 17G used (2758M wired, 8336M compressor), 123M unused.
- Assessment: not concerning

### DISCREPANCY FLAGGED this cycle
- STALL: outputs/rebuttal/experiment_amazon has NOT grown (15450 -> 15450 rows) since previous cycle, and no live process pattern-matches this directory (checked: find + ps aux).

### Cycle 119 ADDENDUM — amazon "stall" verified; TWO REAL DISCREPANCIES (11:47 EDT Jul 27)

1. amazon llama-3.1-8b N=4 DIED SILENTLY at 331/1008 rows (~11:16). Log ends with normal task lines (last: amz_nonsynth_mf4_000017 seed=1, task 17 of 48) then only resource_tracker warnings — NO run summary, NO traceback, NO 403s. No live process, no wrapper: will not resume. N=1-3 verified complete (1007/1008/1008). Amazon otherwise complete: mistral/qwen/llama70b all 4032 rows with clean run summaries.

2. DUPLICATE-PROCESS DOUBLE-WRITING on recipes llama-3.3-70b N=4. PID 97031 (original chain, running since 05:47) and PID 7767 (relaunched 11:10 via caffeinate wrapper "for n in 4 5", PIDs 7761/7764) are BOTH running identical n4 commands and appending to the same jsonl files. PROOF: n4__direct.jsonl has 138 rows but only 119 unique (task,seed) keys — 19 duplicated keys. Contamination grows while both live; n4 files will need dedup by (task,seed,arm) after resolution. Whoever relaunched at 11:10 did not check ps first.

Recipes status: qwen 6293 rows (~complete), mistral 5321 (n2-n4 gaps from 403 era not backfilled; only n5 was rerun), llama-3.1-8b STILL only N=1 (7 files, 1063 rows — never relaunched), llama70b n1-n3 complete + contaminated n4 in progress.

---

## Cycle 120 — 2026-07-27 12:04:37 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 17491 | 105 | 17410 | 81 |
| outputs/rebuttal/experiment_amazon | 15450 | 112 | 15450 | 0 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

2 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
```

### System load

- 12:04  up 43 days, 11:20, 1 user, load averages: 1.30 1.62 2.10
- CPU usage: 2.34% user, 9.47% sys, 88.18% idle 
PhysMem: 17G used (2683M wired, 7427M compressor), 105M unused.
- Assessment: not concerning

---

## Cycle 121 — 2026-07-27 12:21:39 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 17612 | 105 | 17491 | 121 |
| outputs/rebuttal/experiment_amazon | 15450 | 112 | 15450 | 0 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

2 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
```

### System load

- 12:21  up 43 days, 11:38, 1 user, load averages: 1.60 2.39 2.40
- CPU usage: 4.9% user, 10.24% sys, 85.65% idle 
PhysMem: 17G used (2682M wired, 8053M compressor), 101M unused.
- Assessment: not concerning

---

## Cycle 122 — 2026-07-27 12:38:42 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 17689 | 105 | 17612 | 77 |
| outputs/rebuttal/experiment_amazon | 15450 | 112 | 15450 | 0 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

2 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
```

### System load

- 12:38  up 43 days, 11:55, 1 user, load averages: 1.08 1.64 1.94
- CPU usage: 2.23% user, 9.93% sys, 87.82% idle 
PhysMem: 17G used (2684M wired, 8559M compressor), 96M unused.
- Assessment: not concerning

---

## Cycle 123 — 2026-07-27 12:55:45 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 17785 | 105 | 17689 | 96 |
| outputs/rebuttal/experiment_amazon | 15450 | 112 | 15450 | 0 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

2 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
```

### System load

- 12:55  up 43 days, 12:12, 1 user, load averages: 1.87 1.75 1.80
- CPU usage: 5.41% user, 10.32% sys, 84.25% idle 
PhysMem: 17G used (2677M wired, 8538M compressor), 99M unused.
- Assessment: not concerning

---

## Cycle 124 — 2026-07-27 14:17:39 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 17871 | 105 | 17785 | 86 |
| outputs/rebuttal/experiment_amazon | 15450 | 112 | 15450 | 0 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

2 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
```

### System load

- 14:17  up 43 days, 13:34, 1 user, load averages: 3.68 2.77 2.31
- CPU usage: 26.12% user, 48.73% sys, 25.13% idle 
PhysMem: 17G used (4062M wired, 8140M compressor), 239M unused.
- Assessment: not concerning

---

## Cycle 125 — 2026-07-27 14:37:52 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 17920 | 105 | 17871 | 49 |
| outputs/rebuttal/experiment_amazon | 15450 | 112 | 15450 | 0 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

2 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
```

### System load

- 14:37  up 43 days, 13:54, 1 user, load averages: 1.92 1.94 2.61
- CPU usage: 2.67% user, 9.52% sys, 87.79% idle 
PhysMem: 17G used (2672M wired, 6785M compressor), 106M unused.
- Assessment: not concerning

---

## Cycle 126 — 2026-07-27 14:54:55 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 17989 | 105 | 17920 | 69 |
| outputs/rebuttal/experiment_amazon | 15450 | 112 | 15450 | 0 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

2 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
```

### System load

- 14:54  up 43 days, 14:11, 1 user, load averages: 1.20 1.87 2.30
- CPU usage: 2.57% user, 9.84% sys, 87.57% idle 
PhysMem: 17G used (2678M wired, 7596M compressor), 100M unused.
- Assessment: not concerning

---

## Cycle 127 — 2026-07-27 15:11:57 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 18053 | 105 | 17989 | 64 |
| outputs/rebuttal/experiment_amazon | 15450 | 112 | 15450 | 0 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

2 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
```

### System load

- 15:11  up 43 days, 14:28, 1 user, load averages: 1.39 1.45 1.81
- CPU usage: 2.84% user, 10.79% sys, 86.35% idle 
PhysMem: 17G used (2788M wired, 7881M compressor), 87M unused.
- Assessment: not concerning

---

## Cycle 128 — 2026-07-27 15:29:00 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 18142 | 105 | 18053 | 89 |
| outputs/rebuttal/experiment_amazon | 15450 | 112 | 15450 | 0 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

2 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
```

### System load

- 15:29  up 43 days, 14:45, 1 user, load averages: 5.07 4.65 3.12
- CPU usage: 10.38% user, 14.62% sys, 74.98% idle 
PhysMem: 17G used (2663M wired, 8194M compressor), 123M unused.
- Assessment: not concerning

---

## Cycle 129 — 2026-07-27 15:46:03 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 18255 | 112 | 18142 | 113 |
| outputs/rebuttal/experiment_amazon | 15450 | 112 | 15450 | 0 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

2 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
```

### System load

- 15:46  up 43 days, 15:02, 1 user, load averages: 2.34 2.79 2.64
- CPU usage: 4.41% user, 11.17% sys, 84.41% idle 
PhysMem: 17G used (3078M wired, 7019M compressor), 89M unused.
- Assessment: not concerning

---

## Cycle 130 — 2026-07-27 16:03:06 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 18339 | 112 | 18255 | 84 |
| outputs/rebuttal/experiment_amazon | 15450 | 112 | 15450 | 0 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

2 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
```

### System load

- 16:03  up 43 days, 15:19, 1 user, load averages: 3.91 2.44 2.36
- CPU usage: 10.97% user, 14.77% sys, 74.25% idle 
PhysMem: 17G used (3026M wired, 6648M compressor), 114M unused.
- Assessment: not concerning

---

## Cycle 131 — 2026-07-27 16:20:08 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 18416 | 112 | 18339 | 77 |
| outputs/rebuttal/experiment_amazon | 15450 | 112 | 15450 | 0 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

2 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
```

### System load

- 16:20  up 43 days, 15:36, 1 user, load averages: 1.67 1.83 2.13
- CPU usage: 2.32% user, 9.50% sys, 88.17% idle 
PhysMem: 17G used (2850M wired, 6719M compressor), 91M unused.
- Assessment: not concerning

---

## Cycle 132 — 2026-07-27 19:33:34 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 18468 | 112 | 18416 | 52 |
| outputs/rebuttal/experiment_amazon | 15450 | 112 | 15450 | 0 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

2 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```
scripts/rebuttal_experiment_recipes_llama70b.py
scripts/rebuttal_experiment_recipes_mistral.py
```

### System load

- 19:33  up 43 days, 18:49, 1 user, load averages: 18.09 13.14 7.76
- CPU usage: 4.58% user, 12.66% sys, 82.75% idle 
PhysMem: 17G used (2711M wired, 8574M compressor), 93M unused.
- Assessment: not concerning

---

## Cycle 133 — 2026-07-27 20:05:05 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 18323 | 112 | 18468 | -145 |
| outputs/rebuttal/experiment_amazon | 15450 | 112 | 15450 | 0 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

0 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```

```

### System load

- 20:05  up 43 days, 19:21, 1 user, load averages: 2.62 2.94 4.14
- CPU usage: 5.6% user, 10.52% sys, 84.41% idle 
PhysMem: 17G used (2993M wired, 8550M compressor), 91M unused.
- Assessment: not concerning

### DISCREPANCY FLAGGED this cycle
- ZERO live rebuttal_experiment processes found via ps aux. Campaign fully idle (verify whether all remaining work is done or died).

### Cycle 133 ADDENDUM — CAMPAIGN FULLY IDLE, final inventory verified (20:05 EDT Jul 27)

Zero live experiment processes (ps: 0 Python.framework processes). This is NOT a clean finish — verified final state:

RESOLVED since cycle 119:
- recipes llama-3.3-70b N=4 duplicate contamination was cleaned up: n4__direct.jsonl now 180 rows / 180 unique (task,seed) keys / 0 dups. N=1-4 complete.
- recipes mistral partially backfilled: 5321 -> 5770 rows (still 530 short of 6300 theoretical).

INCOMPLETE at idle (dead, will not resume without relaunch):
1. recipes llama-3.3-70b N=5: DIED SILENTLY ~19:56 mid-task (task 7 of 60, seed 1) — no run summary, n5 files ~23 rows each vs 180 target.
2. amazon llama-3.1-8b N=4: still 331/1008 (died 11:16, never relaunched). N=1-3 complete.
3. recipes llama-3.1-8b: still N=1 only (7/35 files, 1063 rows) — N=2-5 never relaunched.
4. experiment_c qwen-2.5-72b: still 1076/~5040 — never relaunched after the 23:24:56 Jul 26 die-off.
5. full_matrix (2wiki) mistral-nemo-12b: still 20/28 files — intro_specter + reflexion arms absent.
6. personalwab qwen-2.5-7b (OpenRouter): partial 135 rows — superseded by Together rerun, presumed abandoned.
7. personalwab aggregate_run.log still dated 00:08:43 — does NOT include the later llama31/mistral completions.

COMPLETE (verified): full_matrix 2wiki qwen/llama31/llama70b; hotpotqa, longmemeval, travelplanner, musique matrices (4 models each); experiment_c 4 core models; amazon mistral/qwen/llama70b (4032 each) + llama31 N=1-3; recipes qwen (6293) + llama70b N=1-4; personalwab llama31/mistral/qwen-together (900 each).

Final totals: full_matrix 3294/4620/4609/3765; hotpotqa 15056; musique 20158; longmemeval 15097; travelplanner 14924; exp_c 20676; recipes 18323; amazon 15450; personalwab 2835.

---

## Cycle 134 — 2026-07-27 20:22:08 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 18323 | 112 | 18323 | 0 |
| outputs/rebuttal/experiment_amazon | 15450 | 112 | 15450 | 0 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

0 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```

```

### System load

- 20:22  up 43 days, 19:38, 1 user, load averages: 3.30 2.96 3.30
- CPU usage: 5.28% user, 13.16% sys, 81.55% idle 
PhysMem: 17G used (2832M wired, 6977M compressor), 94M unused.
- Assessment: not concerning

### DISCREPANCY FLAGGED this cycle
- STALL: outputs/rebuttal/experiment_recipes has NOT grown (18323 -> 18323 rows) since previous cycle, and no live process pattern-matches this directory (checked: find + ps aux).

---

## Cycle 135 — 2026-07-27 20:39:11 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 18323 | 112 | 18323 | 0 |
| outputs/rebuttal/experiment_amazon | 15450 | 112 | 15450 | 0 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

0 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```

```

### System load

- 20:39  up 43 days, 19:55, 1 user, load averages: 4.25 4.04 3.54
- CPU usage: 24.56% user, 16.49% sys, 58.93% idle 
PhysMem: 17G used (3326M wired, 8381M compressor), 134M unused.
- Assessment: not concerning

---

## Cycle 136 — 2026-07-27 20:56:14 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 18323 | 112 | 18323 | 0 |
| outputs/rebuttal/experiment_amazon | 15450 | 112 | 15450 | 0 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

0 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```

```

### System load

- 20:56  up 43 days, 20:12, 1 user, load averages: 2.36 2.77 3.07
- CPU usage: 5.79% user, 13.31% sys, 80.89% idle 
PhysMem: 17G used (2819M wired, 7874M compressor), 91M unused.
- Assessment: not concerning

---

## Cycle 137 — 2026-07-27 21:13:16 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 18323 | 112 | 18323 | 0 |
| outputs/rebuttal/experiment_amazon | 15450 | 112 | 15450 | 0 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

0 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```

```

### System load

- 21:13  up 43 days, 20:29, 1 user, load averages: 2.63 2.45 2.58
- CPU usage: 2.99% user, 9.82% sys, 87.17% idle 
PhysMem: 17G used (2787M wired, 7858M compressor), 88M unused.
- Assessment: not concerning

---

## Cycle 138 — 2026-07-27 21:30:19 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 18323 | 112 | 18323 | 0 |
| outputs/rebuttal/experiment_amazon | 15450 | 112 | 15450 | 0 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

0 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```

```

### System load

- 21:30  up 43 days, 20:46, 1 user, load averages: 3.83 3.49 3.07
- CPU usage: 3.10% user, 9.86% sys, 87.2% idle 
PhysMem: 17G used (2799M wired, 7518M compressor), 96M unused.
- Assessment: not concerning

---

## Cycle 139 — 2026-07-27 21:47:22 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 18323 | 112 | 18323 | 0 |
| outputs/rebuttal/experiment_amazon | 15450 | 112 | 15450 | 0 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

0 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```

```

### System load

- 21:47  up 43 days, 21:03, 1 user, load averages: 1.87 2.25 2.51
- CPU usage: 3.75% user, 10.21% sys, 86.2% idle 
PhysMem: 17G used (2766M wired, 7815M compressor), 98M unused.
- Assessment: not concerning

---

## Cycle 140 — 2026-07-27 22:04:24 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 18323 | 112 | 18323 | 0 |
| outputs/rebuttal/experiment_amazon | 15450 | 112 | 15450 | 0 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

0 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```

```

### System load

- 22:04  up 43 days, 21:20, 1 user, load averages: 3.57 3.74 3.14
- CPU usage: 7.92% user, 13.67% sys, 78.40% idle 
PhysMem: 17G used (2789M wired, 7335M compressor), 132M unused.
- Assessment: not concerning

---

## Cycle 141 — 2026-07-27 22:21:27 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 18323 | 112 | 18323 | 0 |
| outputs/rebuttal/experiment_amazon | 15450 | 112 | 15450 | 0 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

0 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```

```

### System load

- 22:21  up 43 days, 21:37, 1 user, load averages: 2.27 2.38 2.68
- CPU usage: 4.14% user, 11.61% sys, 84.23% idle 
PhysMem: 17G used (2733M wired, 8021M compressor), 92M unused.
- Assessment: not concerning

---

## Cycle 142 — 2026-07-27 22:38:29 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 18323 | 112 | 18323 | 0 |
| outputs/rebuttal/experiment_amazon | 15450 | 112 | 15450 | 0 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

0 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```

```

### System load

- 22:38  up 43 days, 21:54, 1 user, load averages: 2.34 2.95 2.90
- CPU usage: 4.83% user, 10.91% sys, 84.24% idle 
PhysMem: 17G used (2792M wired, 8142M compressor), 91M unused.
- Assessment: not concerning

---

## Cycle 143 — 2026-07-27 22:55:32 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 18323 | 112 | 18323 | 0 |
| outputs/rebuttal/experiment_amazon | 15450 | 112 | 15450 | 0 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

0 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```

```

### System load

- 22:55  up 43 days, 22:11, 1 user, load averages: 2.98 2.65 2.73
- CPU usage: 7.58% user, 16.5% sys, 76.35% idle 
PhysMem: 17G used (2917M wired, 7985M compressor), 92M unused.
- Assessment: not concerning

---

## Cycle 144 — 2026-07-27 23:12:35 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 18323 | 112 | 18323 | 0 |
| outputs/rebuttal/experiment_amazon | 15450 | 112 | 15450 | 0 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

0 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```

```

### System load

- 23:12  up 43 days, 22:28, 1 user, load averages: 4.63 3.93 3.33
- CPU usage: 8.81% user, 13.19% sys, 77.98% idle 
PhysMem: 17G used (2755M wired, 8414M compressor), 104M unused.
- Assessment: not concerning

---

## Cycle 145 — 2026-07-27 23:29:37 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 18323 | 112 | 18323 | 0 |
| outputs/rebuttal/experiment_amazon | 15450 | 112 | 15450 | 0 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

0 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```

```

### System load

- 23:29  up 43 days, 22:46, 1 user, load averages: 2.08 2.18 2.59
- CPU usage: 2.16% user, 9.32% sys, 88.51% idle 
PhysMem: 17G used (2765M wired, 8477M compressor), 94M unused.
- Assessment: not concerning

---

## Cycle 146 — 2026-07-27 23:46:40 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 18323 | 112 | 18323 | 0 |
| outputs/rebuttal/experiment_amazon | 15450 | 112 | 15450 | 0 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

0 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```

```

### System load

- 23:46  up 43 days, 23:03, 1 user, load averages: 2.81 2.49 2.60
- CPU usage: 6.76% user, 22.48% sys, 70.75% idle 
PhysMem: 17G used (2748M wired, 7940M compressor), 94M unused.
- Assessment: not concerning

---

## Cycle 147 — 2026-07-28 00:03:43 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 18323 | 112 | 18323 | 0 |
| outputs/rebuttal/experiment_amazon | 15450 | 112 | 15450 | 0 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

0 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```

```

### System load

-  0:03  up 43 days, 23:20, 1 user, load averages: 3.48 3.42 3.15
- CPU usage: 11.51% user, 14.99% sys, 73.48% idle 
PhysMem: 17G used (2816M wired, 7088M compressor), 95M unused.
- Assessment: not concerning

---

## Cycle 148 — 2026-07-28 00:20:45 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 18323 | 112 | 18323 | 0 |
| outputs/rebuttal/experiment_amazon | 15450 | 112 | 15450 | 0 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

0 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```

```

### System load

-  0:20  up 43 days, 23:37, 1 user, load averages: 2.37 3.00 3.32
- CPU usage: 9.43% user, 15.57% sys, 74.98% idle 
PhysMem: 17G used (2796M wired, 7920M compressor), 98M unused.
- Assessment: not concerning

---

## Cycle 149 — 2026-07-28 00:37:48 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 18323 | 112 | 18323 | 0 |
| outputs/rebuttal/experiment_amazon | 15450 | 112 | 15450 | 0 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

0 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```

```

### System load

-  0:37  up 43 days, 23:54, 1 user, load averages: 2.37 2.75 3.11
- CPU usage: 5.31% user, 12.88% sys, 81.80% idle 
PhysMem: 17G used (2788M wired, 8059M compressor), 95M unused.
- Assessment: not concerning

---

## Cycle 150 — 2026-07-28 00:54:51 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 18323 | 112 | 18323 | 0 |
| outputs/rebuttal/experiment_amazon | 15450 | 112 | 15450 | 0 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

0 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```

```

### System load

-  0:54  up 44 days, 11 mins, 1 user, load averages: 3.37 3.61 3.46
- CPU usage: 3.71% user, 11.9% sys, 85.19% idle 
PhysMem: 17G used (2809M wired, 7902M compressor), 88M unused.
- Assessment: not concerning

---

## Cycle 151 — 2026-07-28 01:11:53 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 18323 | 112 | 18323 | 0 |
| outputs/rebuttal/experiment_amazon | 15450 | 112 | 15450 | 0 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

0 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```

```

### System load

-  1:11  up 44 days, 28 mins, 1 user, load averages: 4.45 3.72 3.37
- CPU usage: 9.18% user, 13.51% sys, 77.29% idle 
PhysMem: 17G used (2818M wired, 8615M compressor), 97M unused.
- Assessment: not concerning

---

## Cycle 152 — 2026-07-28 01:28:56 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 18323 | 112 | 18323 | 0 |
| outputs/rebuttal/experiment_amazon | 15450 | 112 | 15450 | 0 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

0 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```

```

### System load

-  1:28  up 44 days, 45 mins, 1 user, load averages: 2.58 2.89 3.17
- CPU usage: 4.97% user, 11.5% sys, 83.96% idle 
PhysMem: 17G used (2756M wired, 8427M compressor), 97M unused.
- Assessment: not concerning

---

## Cycle 153 — 2026-07-28 01:45:59 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 18323 | 112 | 18323 | 0 |
| outputs/rebuttal/experiment_amazon | 15450 | 112 | 15450 | 0 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

0 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```

```

### System load

-  1:46  up 44 days,  1:02, 1 user, load averages: 3.50 2.97 2.94
- CPU usage: 6.36% user, 11.46% sys, 82.17% idle 
PhysMem: 17G used (2762M wired, 8880M compressor), 89M unused.
- Assessment: not concerning

---

## Cycle 154 — 2026-07-28 02:03:01 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 18323 | 112 | 18323 | 0 |
| outputs/rebuttal/experiment_amazon | 15450 | 112 | 15450 | 0 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

0 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```

```

### System load

-  2:03  up 44 days,  1:19, 1 user, load averages: 2.97 2.93 2.84
- CPU usage: 3.87% user, 9.98% sys, 86.14% idle 
PhysMem: 17G used (2767M wired, 7782M compressor), 105M unused.
- Assessment: not concerning

---

## Cycle 155 — 2026-07-28 02:20:04 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 18323 | 112 | 18323 | 0 |
| outputs/rebuttal/experiment_amazon | 15450 | 112 | 15450 | 0 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

0 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```

```

### System load

-  2:20  up 44 days,  1:36, 1 user, load averages: 3.79 3.15 3.14
- CPU usage: 8.83% user, 13.77% sys, 77.38% idle 
PhysMem: 17G used (2737M wired, 8546M compressor), 93M unused.
- Assessment: not concerning

---

## Cycle 156 — 2026-07-28 02:37:06 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 18323 | 112 | 18323 | 0 |
| outputs/rebuttal/experiment_amazon | 15450 | 112 | 15450 | 0 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

0 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```

```

### System load

-  2:37  up 44 days,  1:53, 1 user, load averages: 2.54 2.79 3.06
- CPU usage: 4.26% user, 11.63% sys, 84.9% idle 
PhysMem: 17G used (2703M wired, 8173M compressor), 91M unused.
- Assessment: not concerning

---

## Cycle 157 — 2026-07-28 02:54:09 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 18323 | 112 | 18323 | 0 |
| outputs/rebuttal/experiment_amazon | 15450 | 112 | 15450 | 0 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

0 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```

```

### System load

-  2:54  up 44 days,  2:10, 1 user, load averages: 2.32 2.08 2.37
- CPU usage: 3.55% user, 10.58% sys, 85.85% idle 
PhysMem: 17G used (2759M wired, 6733M compressor), 116M unused.
- Assessment: not concerning

---

## Cycle 158 — 2026-07-28 08:52:27 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 18323 | 112 | 18323 | 0 |
| outputs/rebuttal/experiment_amazon | 15450 | 112 | 15450 | 0 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

0 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```

```

### System load

-  8:52  up 44 days,  8:08, 1 user, load averages: 4.69 10.99 7.97
- CPU usage: 9.92% user, 12.65% sys, 77.41% idle 
PhysMem: 17G used (2874M wired, 7442M compressor), 133M unused.
- Assessment: not concerning

---

## Cycle 159 — 2026-07-28 09:09:29 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 18323 | 112 | 18323 | 0 |
| outputs/rebuttal/experiment_amazon | 15450 | 112 | 15450 | 0 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

0 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```

```

### System load

-  9:09  up 44 days,  8:25, 1 user, load averages: 2.92 3.53 5.12
- CPU usage: 14.0% user, 14.66% sys, 71.33% idle 
PhysMem: 17G used (2813M wired, 8415M compressor), 124M unused.
- Assessment: not concerning

---

## Cycle 160 — 2026-07-28 09:26:32 EDT

### Row counts

| Directory | Rows | Files | Prev | Delta |
|---|---|---|---|---|
| outputs/rebuttal/experiment_d/full_matrix/mistral-nemo-12b (complete) | 3294 | 20 | 3294 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/qwen-2.5-7b (complete) | 4620 | 28 | 4620 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.1-8b (complete) | 4609 | 28 | 4609 | 0 |
| outputs/rebuttal/experiment_d/full_matrix/llama-3.3-70b (complete) | 3765 | 28 | 3765 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_hotpotqa (complete) | 15056 | 84 | 15056 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_musique (complete) | 20158 | 112 | 20158 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_longmemeval (complete) | 15097 | 84 | 15097 | 0 |
| outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic (complete) | 14924 | 84 | 14924 | 0 |
| outputs/rebuttal/experiment_c/nonsynthetic_multifault | 20676 | 140 | 20676 | 0 |
| outputs/rebuttal/experiment_recipes | 18323 | 112 | 18323 | 0 |
| outputs/rebuttal/experiment_amazon | 15450 | 112 | 15450 | 0 |
| outputs/rebuttal/experiment_personalwab (complete) | 2835 | 20 | 2835 | 0 |

### Real process count

0 live Python.framework processes executing scripts/rebuttal_experiment_*.py

Live scripts (deduped):
```

```

### System load

-  9:26  up 44 days,  8:42, 1 user, load averages: 1.96 2.46 3.30
- CPU usage: 10.74% user, 10.60% sys, 78.64% idle 
PhysMem: 17G used (2685M wired, 8686M compressor), 98M unused.
- Assessment: not concerning
