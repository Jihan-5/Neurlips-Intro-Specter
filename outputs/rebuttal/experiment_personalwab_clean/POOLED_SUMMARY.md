# PersonalWAB (WWW'25) single-turn recommendation -- rebuttal experiment

Task: single-turn personalized recommendation on real PersonalWAB user profiles/histories (757-row test recommend split, 60 examples x seeds 0,1,2 per model, bench_seed=42). Success = mechanical ASIN-containment hit@1 (the ground-truth item the user genuinely interacted with; PersonalWAB's own containment criterion). All counts below are read from the JSONL files on disk.


## Pooled requested models

Requested models: llama-3.1-8b, mistral-nemo-12b.

| model | direct | reflexion | violation_reprompt | iter_vrp | intro_specter |
|---|---|---|---|---|---|
| llama-3.1-8b | 180 | 180 | 180 | 180 | 180 |
| mistral-nemo-12b | 180 | 180 | 180 | 180 | 180 |

Zero-row cells contribute no observations; this is not a complete requested grid if any cell is short.

| arm | rows | successes | success rate |
|---|---|---|---|
| direct | 360 | 321 | 0.891667 |
| reflexion | 360 | 353 | 0.980556 |
| violation_reprompt | 360 | 334 | 0.927778 |
| iter_vrp | 360 | 338 | 0.938889 |
| intro_specter | 360 | 350 | 0.972222 |

Pairs are matched within model on (task_id, seed), then pooled; delta = IS − baseline.

| baseline | pairs | IS wins / baseline wins | delta (pp) [95% paired-bootstrap CI] | exact McNemar p |
|---|---|---|---|---|
| direct | 360 | 29 / 0 | +8.055556 [+5.277778, +10.833333] | 3.7252903e-09 |
| reflexion | 360 | 6 / 9 | -0.833333 [-3.055556, +1.111111] | 0.60723877 |
| violation_reprompt | 360 | 23 / 7 | +4.444444 [+1.666667, +7.500000] | 0.0052228794 |
| iter_vrp | 360 | 19 / 7 | +3.333333 [+0.555556, +6.111111] | 0.028959274 |
