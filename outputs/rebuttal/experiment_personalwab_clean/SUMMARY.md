# PersonalWAB (WWW'25) single-turn recommendation -- rebuttal experiment

Task: single-turn personalized recommendation on real PersonalWAB user profiles/histories (757-row test recommend split, 60 examples x seeds 0,1,2 per model, bench_seed=42). Success = mechanical ASIN-containment hit@1 (the ground-truth item the user genuinely interacted with; PersonalWAB's own containment criterion). All counts below are read from the JSONL files on disk.


## llama-3.1-8b

| arm | n rows | success rate | mean rounds_used | tokens in | tokens out | est. cost ($) |
|---|---|---|---|---|---|---|
| direct | 180 | 148/180 = 0.822 | 1.00 | 1,392,703 | 107,317 | 0.031 |
| reflexion | 180 | 175/180 = 0.972 | 1.18 | 2,104,030 | 208,759 | 0.048 |
| violation_reprompt | 180 | 160/180 = 0.889 | 1.18 | 1,611,548 | 113,398 | 0.036 |
| iter_vrp | 180 | 164/180 = 0.911 | 1.29 | 1,750,326 | 117,443 | 0.039 |
| intro_specter | 180 | 170/180 = 0.944 | 1.19 | 2,943,775 | 257,752 | 0.067 |

Paired exact McNemar, intro_specter vs. baseline (paired on (task_id, seed); delta = IS - baseline, percentage points, with 95% paired-bootstrap CI):

| baseline | n paired | IS wins / baseline wins (discordant) | delta (pp) [95% CI] | McNemar p |
|---|---|---|---|---|
| direct | 180 | 22 / 0 | +12.222222 [+7.777778, +17.222222] | 4.7683716e-07 |
| reflexion | 180 | 4 / 9 | -2.777778 [-6.666667, +1.111111] | 0.2668457 |
| violation_reprompt | 180 | 17 / 7 | +5.555556 [+0.555556, +11.111111] | 0.063914657 |
| iter_vrp | 180 | 13 / 7 | +3.333333 [-1.111111, +8.333333] | 0.26317596 |

## mistral-nemo-12b

| arm | n rows | success rate | mean rounds_used | tokens in | tokens out | est. cost ($) |
|---|---|---|---|---|---|---|
| direct | 180 | 173/180 = 0.961 | 1.00 | 1,524,865 | 70,101 | 0.033 |
| reflexion | 180 | 178/180 = 0.989 | 1.04 | 1,676,589 | 73,977 | 0.036 |
| violation_reprompt | 180 | 174/180 = 0.967 | 1.04 | 1,570,469 | 70,936 | 0.034 |
| iter_vrp | 180 | 174/180 = 0.967 | 1.07 | 1,610,987 | 71,656 | 0.035 |
| intro_specter | 180 | 180/180 = 1.000 | 1.00 | 3,162,756 | 153,404 | 0.069 |

Paired exact McNemar, intro_specter vs. baseline (paired on (task_id, seed); delta = IS - baseline, percentage points, with 95% paired-bootstrap CI):

| baseline | n paired | IS wins / baseline wins (discordant) | delta (pp) [95% CI] | McNemar p |
|---|---|---|---|---|
| direct | 180 | 7 / 0 | +3.888889 [+1.111111, +6.666667] | 0.015625 |
| reflexion | 180 | 2 / 0 | +1.111111 [+0.000000, +2.777778] | 0.5 |
| violation_reprompt | 180 | 6 / 0 | +3.333333 [+1.111111, +6.111111] | 0.03125 |
| iter_vrp | 180 | 6 / 0 | +3.333333 [+1.111111, +6.111111] | 0.03125 |
