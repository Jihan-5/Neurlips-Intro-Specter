# Condition 1 (single-fault synthetic baseline) -- aggregated from existing `outputs/real/` runs

**Zero new experiments.** This is committed, already-completed data from the paper's own real-benchmark suite (`outputs/real/{dataset}__{model}/`), aggregated here into the same comparison format used for the Condition 2 (multi-fault synthetic) and Condition 3 (non-synthetic multi-fault) legs of the rebuttal campaign. Success is read directly from the `success` boolean field written by each run; no re-scoring or re-computation of correctness was performed.

**Sample-size caveat (reported honestly, not hidden):** twowiki_real, musique_real, and longmemeval_real each have 60 examples x 1 seed (seed42). hotpotqa_real and travelplanner_real instead have 12 examples x 3 seeds (seed42/123/456) ≈ 36 total -- smaller AND structured differently (repeated sampling of a tiny pool vs. a single larger pool). Rates for these two datasets should be read with wider uncertainty than the other three.

## Table 1: full (dataset, model) x arm success-rate matrix (%)

| Dataset | Model | n | direct | self_refine | reflexion | full_regen | react | selfcheckgpt | intro_specter |
|---|---|---|---|---|---|---|---|---|---|
| twowiki_real | mistral-nemo-12b | 60 | 91.7 | 86.7 | 95.0 | 90.0 | 86.7 | 89.8 | 96.7 |
| twowiki_real | qwen-2.5-7b | 60 | 81.7 | 80.0 | 91.7 | 85.0 | 76.7 | 85.0 | 90.0 |
| twowiki_real | llama-3.1-8b | 60 | 86.7 | 76.7 | 93.3 | 78.3 | 76.7 | 66.7 | 93.3 |
| twowiki_real | llama-3.3-70b | 60 | 96.7 | 91.7 | 96.7 | 95.0 | 95.0 | 93.3 | 96.7 |
| hotpotqa_real *(small n)* | mistral-nemo-12b | 36 | 83.3 | 80.6 | 86.1 | 88.9 | 83.3 | 80.0 | 91.7 |
| hotpotqa_real *(small n)* | qwen-2.5-7b | 36 | 77.8 | 80.6 | 83.3 | 69.4 | 77.8 | 72.2 | 91.7 |
| hotpotqa_real *(small n)* | llama-3.1-8b | 36 | 91.7 | 91.7 | 94.4 | 88.9 | 91.7 | 75.0 | 97.2 |
| hotpotqa_real *(small n)* | llama-3.3-70b | 36 | 83.3 | 77.8 | 97.2 | 86.1 | 80.6 | 77.8 | 86.1 |
| musique_real | mistral-nemo-12b | 60 | 71.7 | 61.7 | 85.0 | 71.7 | 68.3 | 75.0 | 81.7 |
| musique_real | qwen-2.5-7b | 60 | 80.0 | 63.3 | 83.3 | 80.0 | 65.0 | 75.0 | 85.0 |
| musique_real | llama-3.1-8b | 60 | 76.7 | 66.7 | 90.0 | 76.7 | 66.7 | 51.7 | 91.7 |
| musique_real | llama-3.3-70b | 60 | 83.3 | 78.3 | 96.7 | 81.7 | 81.7 | 70.0 | 93.3 |
| longmemeval_real | mistral-nemo-12b | 60 | 55.0 | 50.0 | 73.3 | 58.3 | 58.3 | 53.3 | 73.3 |
| longmemeval_real | qwen-2.5-7b | 60 | 70.0 | 66.7 | 76.7 | 66.7 | 63.3 | 75.0 | 71.7 |
| longmemeval_real | llama-3.1-8b | 60 | 63.3 | 51.7 | 76.7 | 63.3 | 61.7 | 50.0 | 78.3 |
| longmemeval_real | llama-3.3-70b | 60 | 43.3 | 48.3 | 70.0 | 45.0 | 40.0 | 33.3 | 56.7 |
| travelplanner_real *(small n)* | mistral-nemo-12b | 36 | 25.0 | 27.8 | 41.7 | 19.4 | 36.1 | 22.6 | 27.8 |
| travelplanner_real *(small n)* | qwen-2.5-7b | 36 | 41.7 | 41.7 | 66.7 | 38.9 | 52.8 | 34.4 | 54.3 |
| travelplanner_real *(small n)* | llama-3.1-8b | 36 | 52.8 | 52.8 | 80.6 | 47.2 | 52.8 | 74.2 | 66.7 |
| travelplanner_real *(small n)* | llama-3.3-70b | 36 | 25.0 | 22.2 | 25.0 | 25.0 | 41.7 | 34.5 | 33.3 |

## Table 2: compact summary -- arm x model, averaged across datasets (%)

Two averages shown per cell: **all 5 datasets** (unweighted mean of the 5 per-dataset rates) and **large-n only** (twowiki/musique/longmemeval, 60 examples each) in parentheses, since the small hotpotqa/travelplanner cells carry more noise.

| Arm | mistral-nemo-12b | qwen-2.5-7b | llama-3.1-8b | llama-3.3-70b |
|---|---|---|---|---|
| direct | 65.3 (72.8) | 70.2 (77.2) | 74.2 (75.6) | 66.3 (74.4) |
| self_refine | 61.3 (66.1) | 66.4 (70.0) | 67.9 (65.0) | 63.7 (72.8) |
| reflexion | 76.2 (84.4) | 80.3 (83.9) | 87.0 (86.7) | 77.1 (87.8) |
| full_regen | 65.7 (73.3) | 68.0 (77.2) | 70.9 (72.8) | 66.6 (73.9) |
| react | 66.6 (71.1) | 67.1 (68.3) | 69.9 (68.3) | 67.8 (72.2) |
| selfcheckgpt | 64.1 (72.7) | 68.3 (78.3) | 63.5 (56.1) | 61.8 (65.6) |
| intro_specter | 74.2 (83.9) | 78.5 (82.2) | 85.4 (87.8) | 73.2 (82.2) |

## Table 3: per-arm grand average across all 5 datasets x 4 models (%)

| Arm | Grand avg (all 5 datasets) | Grand avg (large-n 3 datasets only) |
|---|---|---|
| direct | 69.03 | 75.00 |
| self_refine | 64.83 | 68.47 |
| reflexion | 80.17 | 85.69 |
| full_regen | 67.78 | 74.31 |
| react | 67.83 | 70.00 |
| selfcheckgpt | 64.44 | 68.18 |
| intro_specter | 77.85 | 84.03 |

**Ranking (grand avg, all 5 datasets, high to low):** reflexion (80.17%), intro_specter (77.85%), direct (69.03%), react (67.83%), full_regen (67.78%), self_refine (64.83%), selfcheckgpt (64.44%)

