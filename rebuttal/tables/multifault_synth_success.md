# multifault_synth success rates — frozen FINAL-2026-07-27T20:05EDT

## TwoWiki  (source: outputs/rebuttal/experiment_d/full_matrix/**/*.jsonl)
| arm | success | n |
|---|---|---|
| direct | 65.5% | 2503 |
| self_refine | 53.2% | 2497 |
| reflexion | 71.5% | 2538 |
| full_regen | 62.1% | 2500 |
| react | 60.7% | 2501 |
| selfcheckgpt | 62.1% | 2532 |
| intro_specter | 78.6% | 2537 |

| num_faults | direct | self_refine | reflexion | full_regen | react | selfcheckgpt | intro_specter |
|---|---|---|---|---|---|---|---|
| 2 | 81.5% (666) | 69.2% (666) | 89.0% (684) | 79.7% (666) | 77.6% (666) | 76.4% (682) | 90.6% (684) |
| 3 | 74.6% (668) | 57.3% (665) | 78.9% (684) | 70.7% (666) | 70.8% (667) | 68.8% (682) | 88.0% (684) |
| 4 | 65.7% (665) | 55.3% (662) | 73.4% (683) | 58.4% (664) | 61.0% (664) | 62.3% (681) | 88.4% (683) |
| 5 | 31.9% (504) | 24.0% (504) | 33.7% (487) | 32.3% (504) | 24.4% (504) | 32.6% (487) | 34.6% (486) |

| model | intro_specter | reflexion |
|---|---|---|
| llama-3.1-8b | 81.9% (659) | 78.8% (659) |
| llama-3.3-70b | 77.6% (558) | 63.5% (559) |
| mistral-nemo-12b | 82.1% (660) | 72.1% (660) |
| qwen-2.5-7b | 72.6% (660) | 70.3% (660) |

## HotpotQA  (source: outputs/rebuttal/experiment_d/full_matrix_hotpotqa/**/*.jsonl)
| arm | success | n |
|---|---|---|
| direct | 62.9% | 2155 |
| self_refine | 49.2% | 2143 |
| reflexion | 71.6% | 2155 |
| full_regen | 59.4% | 2155 |
| react | 61.2% | 2145 |
| selfcheckgpt | 59.0% | 2148 |
| intro_specter | 81.4% | 2155 |

| num_faults | direct | self_refine | reflexion | full_regen | react | selfcheckgpt | intro_specter |
|---|---|---|---|---|---|---|---|
| 2 | 74.0% (719) | 57.2% (717) | 84.1% (719) | 70.7% (719) | 73.3% (719) | 69.4% (718) | 84.8% (719) |
| 3 | 60.3% (720) | 47.9% (718) | 68.3% (720) | 56.4% (720) | 57.4% (718) | 55.1% (719) | 79.9% (720) |
| 4 | 54.3% (716) | 42.5% (708) | 62.3% (716) | 51.1% (716) | 52.7% (708) | 52.6% (711) | 79.6% (716) |

| model | intro_specter | reflexion |
|---|---|---|
| llama-3.1-8b | 91.6% (535) | 87.9% (535) |
| llama-3.3-70b | 77.6% (540) | 63.9% (540) |
| mistral-nemo-12b | 83.0% (540) | 64.6% (540) |
| qwen-2.5-7b | 73.7% (540) | 70.2% (540) |

## MuSiQue  (source: outputs/rebuttal/experiment_d/full_matrix_musique/**/*.jsonl)
| arm | success | n |
|---|---|---|
| direct | 54.5% | 2880 |
| self_refine | 42.4% | 2879 |
| reflexion | 57.2% | 2880 |
| full_regen | 53.5% | 2880 |
| react | 48.4% | 2880 |
| selfcheckgpt | 53.1% | 2879 |
| intro_specter | 62.4% | 2880 |

| num_faults | direct | self_refine | reflexion | full_regen | react | selfcheckgpt | intro_specter |
|---|---|---|---|---|---|---|---|
| 2 | 71.4% (720) | 58.2% (720) | 79.9% (720) | 72.1% (720) | 68.9% (720) | 69.2% (720) | 85.6% (720) |
| 3 | 67.1% (720) | 49.9% (719) | 73.5% (720) | 64.6% (720) | 61.4% (720) | 62.2% (720) | 80.8% (720) |
| 4 | 44.0% (720) | 34.9% (720) | 42.4% (720) | 41.9% (720) | 35.0% (720) | 44.2% (720) | 44.3% (720) |
| 5 | 35.4% (720) | 26.7% (720) | 33.2% (720) | 35.6% (720) | 28.3% (720) | 36.7% (719) | 39.0% (720) |

| model | intro_specter | reflexion |
|---|---|---|
| llama-3.1-8b | 53.8% (720) | 48.6% (720) |
| llama-3.3-70b | 81.1% (720) | 72.2% (720) |
| mistral-nemo-12b | 56.8% (720) | 51.7% (720) |
| qwen-2.5-7b | 58.1% (720) | 56.4% (720) |

## LongMemEval  (source: outputs/rebuttal/experiment_d/full_matrix_longmemeval/**/*.jsonl)
| arm | success | n |
|---|---|---|
| direct | 48.8% | 2160 |
| self_refine | 34.9% | 2157 |
| reflexion | 57.7% | 2160 |
| full_regen | 46.3% | 2160 |
| react | 45.1% | 2150 |
| selfcheckgpt | 46.7% | 2150 |
| intro_specter | 65.3% | 2160 |

| num_faults | direct | self_refine | reflexion | full_regen | react | selfcheckgpt | intro_specter |
|---|---|---|---|---|---|---|---|
| 2 | 59.3% (720) | 45.8% (720) | 71.7% (720) | 55.7% (720) | 54.8% (717) | 55.8% (719) | 73.9% (720) |
| 3 | 51.5% (720) | 34.9% (720) | 57.9% (720) | 49.2% (720) | 46.5% (718) | 48.1% (713) | 66.0% (720) |
| 4 | 35.7% (720) | 24.0% (717) | 43.6% (720) | 34.0% (720) | 33.8% (715) | 36.4% (718) | 56.1% (720) |

| model | intro_specter | reflexion |
|---|---|---|
| llama-3.1-8b | 76.9% (540) | 69.8% (540) |
| llama-3.3-70b | 58.7% (540) | 55.7% (540) |
| mistral-nemo-12b | 71.3% (540) | 54.6% (540) |
| qwen-2.5-7b | 54.4% (540) | 50.7% (540) |

## TravelPlanner-synth  (source: outputs/rebuttal/experiment_d/full_matrix_travelplanner_synthetic/**/*.jsonl)
| arm | success | n |
|---|---|---|
| direct | 34.0% | 2159 |
| self_refine | 34.1% | 2159 |
| reflexion | 32.6% | 2159 |
| full_regen | 32.9% | 2159 |
| react | 32.7% | 2159 |
| selfcheckgpt | 33.0% | 1970 |
| intro_specter | 36.6% | 2159 |

| num_faults | direct | self_refine | reflexion | full_regen | react | selfcheckgpt | intro_specter |
|---|---|---|---|---|---|---|---|
| 2 | 58.5% (720) | 58.1% (720) | 55.4% (720) | 59.0% (720) | 60.1% (720) | 58.1% (640) | 63.3% (720) |
| 3 | 27.5% (720) | 28.5% (720) | 27.1% (720) | 26.8% (720) | 27.2% (720) | 26.5% (660) | 30.1% (720) |
| 4 | 15.9% (719) | 15.9% (719) | 15.3% (719) | 12.9% (719) | 10.7% (719) | 15.4% (670) | 16.3% (719) |

| model | intro_specter | reflexion |
|---|---|---|
| llama-3.1-8b | 37.7% (539) | 37.3% (539) |
| llama-3.3-70b | 33.9% (540) | 22.0% (540) |
| mistral-nemo-12b | 31.7% (540) | 29.1% (540) |
| qwen-2.5-7b | 43.1% (540) | 42.0% (540) |
