# PersonalWAB (WWW'25) single-turn recommendation -- rebuttal experiment

Task: single-turn personalized recommendation on real PersonalWAB user profiles/histories (757-row test recommend split, 60 examples x seeds 0,1,2 per model, bench_seed=42). Success = mechanical ASIN-containment hit@1 (the ground-truth item the user genuinely interacted with; PersonalWAB's own containment criterion). All counts below are read from the JSONL files on disk.


## mistral-nemo-12b

| arm | n rows | success rate | mean rounds_used | tokens in | tokens out | est. cost ($) |
|---|---|---|---|---|---|---|
| direct | 180 | 164/180 = 0.911 | 1.00 | 822,533 | 74,631 | 0.019 |
| reflexion | 180 | 174/180 = 0.967 | 1.09 | 1,110,760 | 94,248 | 0.026 |
| violation_reprompt | 180 | 167/180 = 0.928 | 1.09 | 871,853 | 77,817 | 0.021 |
| iter_vrp | 180 | 169/180 = 0.939 | 1.16 | 911,780 | 80,530 | 0.021 |
| intro_specter | 180 | 176/180 = 0.978 | 1.02 | 1,768,620 | 156,223 | 0.042 |

Paired exact McNemar, intro_specter vs. baseline (paired on (task_id, seed); delta = IS - baseline, percentage points, with 95% paired-bootstrap CI):

| baseline | n paired | IS wins / baseline wins (discordant) | delta (pp) [95% CI] | McNemar p |
|---|---|---|---|---|
| direct | 180 | 12 / 0 | +6.7 [+3.3, +10.6] | 0.0005 |
| reflexion | 180 | 4 / 2 | +1.1 [-1.7, +3.9] | 0.6875 |
| violation_reprompt | 180 | 9 / 0 | +5.0 [+2.2, +8.3] | 0.0039 |
| iter_vrp | 180 | 9 / 2 | +3.9 [+0.6, +7.8] | 0.0654 |

## qwen-2.5-7b

| arm | n rows | success rate | mean rounds_used | tokens in | tokens out | est. cost ($) |
|---|---|---|---|---|---|---|
| direct | 27 | 25/27 = 0.926 | 1.00 | 114,338 | 12,963 | 0.006 |
| reflexion | 27 | 25/27 = 0.926 | 1.07 | 153,126 | 15,569 | 0.008 |
| violation_reprompt | 27 | 25/27 = 0.926 | 1.07 | 119,970 | 13,361 | 0.006 |
| iter_vrp | 27 | 25/27 = 0.926 | 1.15 | 125,602 | 13,649 | 0.006 |
| intro_specter | 27 | 27/27 = 1.000 | 1.00 | 249,132 | 32,487 | 0.013 |

Paired exact McNemar, intro_specter vs. baseline (paired on (task_id, seed); delta = IS - baseline, percentage points, with 95% paired-bootstrap CI):

| baseline | n paired | IS wins / baseline wins (discordant) | delta (pp) [95% CI] | McNemar p |
|---|---|---|---|---|
| direct | 27 | 2 / 0 | +7.4 [+0.0, +18.5] | 0.5000 |
| reflexion | 27 | 2 / 0 | +7.4 [+0.0, +18.5] | 0.5000 |
| violation_reprompt | 27 | 2 / 0 | +7.4 [+0.0, +18.5] | 0.5000 |
| iter_vrp | 27 | 2 / 0 | +7.4 [+0.0, +18.5] | 0.5000 |

## llama-3.1-8b

| arm | n rows | success rate | mean rounds_used | tokens in | tokens out | est. cost ($) |
|---|---|---|---|---|---|---|
| direct | 180 | 174/180 = 0.967 | 1.00 | 739,401 | 103,308 | 0.018 |
| reflexion | 180 | 178/180 = 0.989 | 1.03 | 824,104 | 118,582 | 0.020 |
| violation_reprompt | 180 | 176/180 = 0.978 | 1.03 | 756,817 | 104,582 | 0.018 |
| iter_vrp | 180 | 177/180 = 0.983 | 1.06 | 768,276 | 105,271 | 0.019 |
| intro_specter | 180 | 179/180 = 0.994 | 1.00 | 1,634,194 | 241,095 | 0.040 |

Paired exact McNemar, intro_specter vs. baseline (paired on (task_id, seed); delta = IS - baseline, percentage points, with 95% paired-bootstrap CI):

| baseline | n paired | IS wins / baseline wins (discordant) | delta (pp) [95% CI] | McNemar p |
|---|---|---|---|---|
| direct | 180 | 5 / 0 | +2.8 [+0.6, +5.6] | 0.0625 |
| reflexion | 180 | 2 / 1 | +0.6 [-1.1, +2.8] | 1.0000 |
| violation_reprompt | 180 | 3 / 0 | +1.7 [+0.0, +3.9] | 0.2500 |
| iter_vrp | 180 | 3 / 1 | +1.1 [-1.1, +3.3] | 0.6250 |

## qwen-2.5-7b-together

| arm | n rows | success rate | mean rounds_used | tokens in | tokens out | est. cost ($) |
|---|---|---|---|---|---|---|
| direct | 180 | 165/180 = 0.917 | 1.00 | 773,288 | 77,760 | 0.255 |
| reflexion | 180 | 168/180 = 0.933 | 1.08 | 1,060,571 | 98,259 | 0.348 |
| violation_reprompt | 180 | 168/180 = 0.933 | 1.08 | 818,799 | 80,339 | 0.270 |
| iter_vrp | 180 | 168/180 = 0.933 | 1.15 | 854,696 | 82,177 | 0.281 |
| intro_specter | 180 | 174/180 = 0.967 | 1.04 | 1,677,804 | 207,932 | 0.566 |

Paired exact McNemar, intro_specter vs. baseline (paired on (task_id, seed); delta = IS - baseline, percentage points, with 95% paired-bootstrap CI):

| baseline | n paired | IS wins / baseline wins (discordant) | delta (pp) [95% CI] | McNemar p |
|---|---|---|---|---|
| direct | 180 | 9 / 0 | +5.0 [+2.2, +8.3] | 0.0039 |
| reflexion | 180 | 6 / 0 | +3.3 [+1.1, +6.1] | 0.0312 |
| violation_reprompt | 180 | 6 / 0 | +3.3 [+1.1, +6.1] | 0.0312 |
| iter_vrp | 180 | 6 / 0 | +3.3 [+1.1, +6.1] | 0.0312 |
