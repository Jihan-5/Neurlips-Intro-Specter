# Experiment C, non-synthetic MULTI-FAULT leg -- full model x N x 7-arm matrix

TravelPlanner-NATIVE constraints only (budget, trip length, and whichever local constraints -- cuisine/house rule/room type/transportation -- a row carries), corrupted with N>=2 independent, simultaneous faults via `intro_specter/profiles/native_multi_fault_injection.py`. No templated `inject_profile` content anywhere in the prompt. All 7 arms (`direct`, `self_refine`, `full_regen`, `react`, `selfcheckgpt`, `reflexion`, `intro_specter`) run the real, UNMODIFIED `intro_specter/baselines/*` and `intro_specter/pipeline.py`. See `scripts/rebuttal_experiment_c_nonsynthetic_multifault_common.py` module docstring for the full per-level feasibility (N=2: all levels; N=3: medium+hard; N=4/5: hard only) and mechanical resolution-checking methodology.

**Comparison point already on record (single-fault, native budget only, 2 arms, mistral-nemo-12b):** Reflexion 91.8% vs. Intro-Specter 68.6% (`outputs/rebuttal/experiment_c/nonsynthetic_travelplanner_results*.jsonl`) -- a real, mechanistically-understood loss for Intro-Specter on this budget-optimization task (targeted repair has less room to cut costs than full regeneration). This table reports whatever the multi-fault, multi-model, 7-arm data actually shows relative to that -- no assumption that multi-fault reverses the pattern.


## Headline: Reflexion vs. Intro-Specter, aggregated across all 4 models


### By fault count N (all 4 models combined)

| N | reflexion %all_resolved (n) | intro_specter %all_resolved (n) | paired McNemar p |
|---|---|---|---|
| 2 | 75.7% (720) | 74.7% (719) | 0.0013 |
| 3 | 36.5% (720) | 31.7% (720) | 0.0784 |
| 4 | 30.0% (720) | 24.4% (718) | 0.0001 |
| 5 | 24.9% (720) | 20.6% (719) | 0.0066 |

### By model (all N combined)

| model | reflexion %all_resolved (n) | intro_specter %all_resolved (n) | paired McNemar p |
|---|---|---|---|
| mistral-nemo-12b | 36.5% (720) | 24.6% (720) | 0.0000 |
| qwen-2.5-7b | 24.7% (720) | 27.4% (720) | 0.0671 |
| llama-3.1-8b | 60.3% (720) | 46.5% (716) | 0.0000 |
| llama-3.3-70b | 45.6% (720) | 52.9% (720) | 0.0000 |

### Grand total (all models, all N combined)

reflexion: 41.8% (n=2880) vs. intro_specter: 37.8% (n=2876); paired n=720, reflexion-only-wins=14, intro_specter-only-wins=67, both=314, neither=325, McNemar p=0.000000


**Honest comparison to the single-fault result:** Reflexion beats Intro-Specter in the aggregate multi-fault matrix too, but the gap is much narrower than the single-fault, budget-only result (91.8% vs 68.6%, a 23.2-point gap). Multi-fault does NOT reverse the pattern -- Reflexion remains ahead overall -- but it also does not make the pattern uniformly worse for Intro-Specter: at the per-model level, Intro-Specter actually beats Reflexion on qwen-2.5-7b and llama-3.3-70b (see table above), while losing more heavily on mistral-nemo-12b and llama-3.1-8b. This is a genuine, mixed result -- not a clean win or loss for either method -- and is reported as-is rather than forced toward either conclusion.


## Model: mistral-nemo-12b


### N=2 (level distribution: {'easy': 72, 'hard': 72, 'medium': 36})

| arm | n | %all_resolved | mean frac. faults resolved | tokens (in+out) |
|---|---|---|---|---|
| direct | 180 | 58.9% | 0.772 | 433,300 |
| self_refine | 180 | 61.7% | 0.786 | 1,119,342 |
| full_regen | 180 | 43.3% | 0.642 | 861,291 |
| react | 180 | 62.8% | 0.764 | 915,203 |
| selfcheckgpt | 150 | 60.7% | 0.787 | 2,011,428 |
| reflexion | 180 | 72.2% | 0.850 | 1,327,535 |
| intro_specter | 180 | 63.3% | 0.800 | 1,054,910 |

### N=3 (level distribution: {'hard': 111, 'medium': 69})

| arm | n | %all_resolved | mean frac. faults resolved | tokens (in+out) |
|---|---|---|---|---|
| direct | 180 | 15.0% | 0.556 | 446,817 |
| self_refine | 180 | 23.3% | 0.607 | 1,152,048 |
| full_regen | 180 | 17.8% | 0.513 | 894,446 |
| react | 180 | 24.4% | 0.604 | 960,238 |
| selfcheckgpt | 153 | 16.3% | 0.562 | 2,085,664 |
| reflexion | 180 | 27.8% | 0.683 | 2,558,890 |
| intro_specter | 180 | 18.3% | 0.452 | 1,094,355 |

### N=4 (level distribution: {'hard': 180})

| arm | n | %all_resolved | mean frac. faults resolved | tokens (in+out) |
|---|---|---|---|---|
| direct | 180 | 10.0% | 0.586 | 471,590 |
| self_refine | 179 | 20.1% | 0.647 | 1,221,878 |
| full_regen | 180 | 6.1% | 0.501 | 932,249 |
| react | 180 | 11.7% | 0.519 | 976,009 |
| selfcheckgpt | 157 | 10.2% | 0.584 | 2,219,116 |
| reflexion | 180 | 27.8% | 0.735 | 2,808,445 |
| intro_specter | 180 | 11.7% | 0.486 | 1,163,219 |

### N=5 (level distribution: {'hard': 180})

| arm | n | %all_resolved | mean frac. faults resolved | tokens (in+out) |
|---|---|---|---|---|
| direct | 180 | 2.8% | 0.503 | 477,529 |
| self_refine | 180 | 3.3% | 0.601 | 1,250,082 |
| full_regen | 180 | 2.8% | 0.420 | 942,520 |
| react | 180 | 5.6% | 0.400 | 973,725 |
| selfcheckgpt | 166 | 3.0% | 0.519 | 2,404,550 |
| reflexion | 180 | 18.3% | 0.692 | 3,085,385 |
| intro_specter | 180 | 5.0% | 0.389 | 1,190,485 |

## Model: qwen-2.5-7b


### N=2 (level distribution: {'easy': 72, 'hard': 72, 'medium': 36})

| arm | n | %all_resolved | mean frac. faults resolved | tokens (in+out) |
|---|---|---|---|---|
| direct | 180 | 46.1% | 0.728 | 504,355 |
| self_refine | 180 | 31.1% | 0.653 | 1,338,995 |
| full_regen | 180 | 41.7% | 0.675 | 987,635 |
| react | 180 | 36.7% | 0.678 | 1,024,339 |
| selfcheckgpt | 162 | 46.9% | 0.731 | 3,410,948 |
| reflexion | 180 | 61.7% | 0.808 | 2,032,548 |
| intro_specter | 180 | 65.6% | 0.797 | 1,317,558 |

### N=3 (level distribution: {'hard': 111, 'medium': 69})

| arm | n | %all_resolved | mean frac. faults resolved | tokens (in+out) |
|---|---|---|---|---|
| direct | 180 | 11.7% | 0.550 | 507,999 |
| self_refine | 180 | 12.2% | 0.561 | 1,375,293 |
| full_regen | 180 | 8.3% | 0.507 | 1,003,646 |
| react | 180 | 8.9% | 0.520 | 1,048,761 |
| selfcheckgpt | 158 | 13.3% | 0.580 | 3,402,699 |
| reflexion | 180 | 20.0% | 0.591 | 3,173,585 |
| intro_specter | 180 | 23.9% | 0.552 | 1,363,184 |

### N=4 (level distribution: {'hard': 180})

| arm | n | %all_resolved | mean frac. faults resolved | tokens (in+out) |
|---|---|---|---|---|
| direct | 180 | 6.7% | 0.515 | 516,988 |
| self_refine | 180 | 5.0% | 0.526 | 1,384,889 |
| full_regen | 180 | 5.0% | 0.521 | 1,029,589 |
| react | 180 | 11.1% | 0.568 | 1,081,371 |
| selfcheckgpt | 168 | 5.4% | 0.552 | 3,814,505 |
| reflexion | 180 | 12.2% | 0.543 | 3,502,024 |
| intro_specter | 180 | 11.7% | 0.475 | 1,428,660 |

### N=5 (level distribution: {'hard': 180})

| arm | n | %all_resolved | mean frac. faults resolved | tokens (in+out) |
|---|---|---|---|---|
| direct | 180 | 1.1% | 0.471 | 507,565 |
| self_refine | 180 | 0.0% | 0.457 | 1,346,488 |
| full_regen | 180 | 1.7% | 0.487 | 1,009,022 |
| react | 180 | 7.8% | 0.482 | 1,062,131 |
| selfcheckgpt | 170 | 1.2% | 0.529 | 3,782,621 |
| reflexion | 180 | 5.0% | 0.493 | 3,618,766 |
| intro_specter | 180 | 8.3% | 0.477 | 1,370,329 |

## Model: llama-3.1-8b


### N=2 (level distribution: {'easy': 71, 'hard': 72, 'medium': 36})

| arm | n | %all_resolved | mean frac. faults resolved | tokens (in+out) |
|---|---|---|---|---|
| direct | 180 | 55.6% | 0.769 | 513,139 |
| self_refine | 180 | 59.4% | 0.786 | 1,426,413 |
| full_regen | 180 | 51.7% | 0.742 | 999,316 |
| react | 180 | 66.1% | 0.831 | 1,037,223 |
| selfcheckgpt | 117 | 53.0% | 0.765 | 2,026,453 |
| reflexion | 180 | 84.4% | 0.919 | 1,563,386 |
| intro_specter | 179 | 77.7% | 0.855 | 1,301,916 |

### N=3 (level distribution: {'hard': 111, 'medium': 69})

| arm | n | %all_resolved | mean frac. faults resolved | tokens (in+out) |
|---|---|---|---|---|
| direct | 180 | 28.9% | 0.689 | 485,666 |
| self_refine | 180 | 32.8% | 0.717 | 1,280,188 |
| full_regen | 180 | 24.4% | 0.652 | 992,504 |
| react | 180 | 21.7% | 0.626 | 1,015,007 |
| selfcheckgpt | 111 | 28.8% | 0.676 | 1,910,439 |
| reflexion | 180 | 55.6% | 0.813 | 2,331,962 |
| intro_specter | 180 | 36.7% | 0.622 | 1,195,654 |

### N=4 (level distribution: {'hard': 178})

| arm | n | %all_resolved | mean frac. faults resolved | tokens (in+out) |
|---|---|---|---|---|
| direct | 180 | 28.9% | 0.690 | 506,179 |
| self_refine | 180 | 26.1% | 0.689 | 1,340,116 |
| full_regen | 180 | 15.0% | 0.640 | 1,013,050 |
| react | 180 | 26.7% | 0.662 | 1,075,274 |
| selfcheckgpt | 118 | 23.7% | 0.682 | 2,140,135 |
| reflexion | 180 | 52.2% | 0.826 | 2,440,957 |
| intro_specter | 178 | 37.6% | 0.659 | 1,234,679 |

### N=5 (level distribution: {'hard': 179})

| arm | n | %all_resolved | mean frac. faults resolved | tokens (in+out) |
|---|---|---|---|---|
| direct | 180 | 22.2% | 0.731 | 493,957 |
| self_refine | 180 | 23.3% | 0.729 | 1,302,260 |
| full_regen | 180 | 6.1% | 0.567 | 1,005,950 |
| react | 180 | 7.8% | 0.570 | 1,050,953 |
| selfcheckgpt | 110 | 20.9% | 0.740 | 1,969,515 |
| reflexion | 180 | 48.9% | 0.837 | 2,545,440 |
| intro_specter | 179 | 34.1% | 0.703 | 1,197,802 |

## Model: llama-3.3-70b


### N=2 (level distribution: {'easy': 72, 'hard': 72, 'medium': 36})

| arm | n | %all_resolved | mean frac. faults resolved | tokens (in+out) |
|---|---|---|---|---|
| direct | 180 | 80.0% | 0.900 | 392,065 |
| self_refine | 180 | 72.8% | 0.853 | 1,019,432 |
| full_regen | 180 | 83.3% | 0.911 | 779,407 |
| react | 180 | 42.2% | 0.686 | 789,536 |
| selfcheckgpt | 134 | 91.0% | 0.955 | 1,779,206 |
| reflexion | 180 | 84.4% | 0.847 | 727,447 |
| intro_specter | 180 | 92.2% | 0.961 | 964,392 |

### N=3 (level distribution: {'hard': 111, 'medium': 69})

| arm | n | %all_resolved | mean frac. faults resolved | tokens (in+out) |
|---|---|---|---|---|
| direct | 180 | 38.9% | 0.741 | 393,998 |
| self_refine | 180 | 30.0% | 0.656 | 1,007,505 |
| full_regen | 180 | 41.1% | 0.744 | 795,558 |
| react | 180 | 13.9% | 0.587 | 808,609 |
| selfcheckgpt | 141 | 47.5% | 0.790 | 1,866,308 |
| reflexion | 180 | 42.8% | 0.517 | 1,478,095 |
| intro_specter | 180 | 47.8% | 0.737 | 966,837 |

### N=4 (level distribution: {'hard': 180})

| arm | n | %all_resolved | mean frac. faults resolved | tokens (in+out) |
|---|---|---|---|---|
| direct | 180 | 25.0% | 0.729 | 416,726 |
| self_refine | 180 | 20.0% | 0.657 | 1,058,291 |
| full_regen | 180 | 27.8% | 0.724 | 832,217 |
| react | 180 | 18.9% | 0.622 | 847,549 |
| selfcheckgpt | 150 | 28.7% | 0.788 | 2,106,513 |
| reflexion | 180 | 27.8% | 0.376 | 1,807,968 |
| intro_specter | 180 | 36.7% | 0.747 | 1,025,211 |

### N=5 (level distribution: {'hard': 180})

| arm | n | %all_resolved | mean frac. faults resolved | tokens (in+out) |
|---|---|---|---|---|
| direct | 180 | 23.3% | 0.740 | 412,324 |
| self_refine | 180 | 23.3% | 0.728 | 1,041,487 |
| full_regen | 180 | 22.2% | 0.723 | 827,893 |
| react | 180 | 8.9% | 0.581 | 843,249 |
| selfcheckgpt | 160 | 26.2% | 0.782 | 2,251,049 |
| reflexion | 180 | 27.2% | 0.358 | 1,819,058 |
| intro_specter | 180 | 35.0% | 0.780 | 1,013,791 |

## Grand totals (across all models/N/arms found so far)

Total rows written: 19600

Total tokens (in+out): 152,445,996

