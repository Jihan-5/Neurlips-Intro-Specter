# Tier-C synthetic results (auto-generated)

## Per-method per-mode summary

| mode         | method          |   n |   success |   violation |   tokens_total |   delta_success_vs_direct |   delta_tokens_vs_direct |   mcnemar_success_p |   wilcoxon_tokens_p |   holm_success_adj |   degradation_rate |
|:-------------|:----------------|----:|----------:|------------:|---------------:|--------------------------:|-------------------------:|--------------------:|--------------------:|-------------------:|-------------------:|
| single_fault | direct          |  60 |     0.000 |       1.000 |          0.000 |                   nan     |                  nan     |             nan     |             nan     |            nan     |            nan     |
| single_fault | full_regen      |  60 |     1.000 |       0.000 |        798.000 |                     1.000 |                  798.000 |               0.000 |               0.000 |              0.000 |              0.000 |
| single_fault | intro_specter   |  60 |     1.000 |       0.000 |          0.000 |                     1.000 |                    0.000 |               0.000 |               1.000 |              0.000 |              0.000 |
| single_fault | oracle_detector |  60 |     1.000 |       0.000 |          0.000 |                     1.000 |                    0.000 |               0.000 |               1.000 |              0.000 |              0.000 |
| single_fault | oracle_repair   |  60 |     1.000 |       0.000 |          0.000 |                     1.000 |                    0.000 |               0.000 |               1.000 |              0.000 |              0.000 |
| single_fault | reflexion       |  60 |     0.000 |       1.000 |          0.000 |                     0.000 |                    0.000 |               1.000 |               1.000 |              1.000 |              0.000 |
| single_fault | self_refine     |  60 |     0.000 |       1.000 |          0.000 |                     0.000 |                    0.000 |               1.000 |               1.000 |              1.000 |              0.000 |
| multi_valid  | direct          |  60 |     0.000 |       1.000 |          0.000 |                   nan     |                  nan     |             nan     |             nan     |            nan     |            nan     |
| multi_valid  | full_regen      |  60 |     1.000 |       0.000 |        798.000 |                     1.000 |                  798.000 |               0.000 |               0.000 |              0.000 |              0.000 |
| multi_valid  | intro_specter   |  60 |     1.000 |       0.000 |          0.000 |                     1.000 |                    0.000 |               0.000 |               1.000 |              0.000 |              0.000 |
| multi_valid  | oracle_detector |  60 |     1.000 |       0.000 |          0.000 |                     1.000 |                    0.000 |               0.000 |               1.000 |              0.000 |              0.000 |
| multi_valid  | oracle_repair   |  60 |     1.000 |       0.000 |          0.000 |                     1.000 |                    0.000 |               0.000 |               1.000 |              0.000 |              0.000 |
| multi_valid  | reflexion       |  60 |     0.000 |       1.000 |          0.000 |                     0.000 |                    0.000 |               1.000 |               1.000 |              1.000 |              0.000 |
| multi_valid  | self_refine     |  60 |     0.000 |       1.000 |          0.000 |                     0.000 |                    0.000 |               1.000 |               1.000 |              1.000 |              0.000 |


## Intro-Specter attribution accuracy

| mode         |   n |   top1_acc |   top3_acc |   mrr |
|:-------------|----:|-----------:|-----------:|------:|
| single_fault |  60 |      1.000 |      1.000 | 1.000 |
| multi_valid  |  60 |      0.000 |      1.000 | 0.500 |

