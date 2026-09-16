# Real-MuSiQue (3-hop, n=60, seed=42) — Phase 1 final

**Real-MuSiQue: IS strict wins vs Direct (Holm p<0.05): 1/6.** 
**IS strict wins vs Reflexion (McNemar p<0.05): 0/6.**

Source: HuggingFace `dgslibisey/MuSiQue` validation split, 3-hop subset only. 
60 examples per cell sampled with seed=42 via deterministic loader (paired across all (method, model) within a cell). 8 methods compared: Direct, Self-Refine, Reflexion, Full-Regen, ReAct, SelfCheckGPT, Tree-of-Thoughts, Intro-Specter. ToT marked with ‡ where rate-limit skips left it partial; reported as-is per no-fabrication clause.


## Per-cell success rates (%)

| LLM | Direct | Self-Refine | Reflexion | Full-Regen | ReAct | SelfCheckGPT | ToT | **IS** | Best (excl. Direct) |
|---|---|---|---|---|---|---|---|---|---|
| Llama 3.1 8B | 76.7 | 66.7 | 90.0 | 76.7 | 66.7 | 51.7 | 71.7 | **91.7** | **IS** |
| Llama 3.3 70B | 83.3 | 78.3 | **96.7** | 81.7 | 81.7 | 70.0 | 55.0 | 93.3 | Reflexion |
| DeepSeek V3 | 56.7 | 55.0 | **71.7** | 56.7 | 66.7 | 63.3 | 61.7 | 61.7 | Reflexion |
| Mistral Nemo 12B | 71.7 | 61.7 | **85.0** | 71.7 | 68.3 | 75.0 | 68.6‡(n=51) | 81.7 | Reflexion |
| Qwen 2.5 7B | 80.0 | 63.3 | 83.3 | 80.0 | 65.0 | 75.0 | 77.3‡(n=22) | **85.0** | **IS** |
| Gemini 2.5 Flash | 51.7 | 41.7 | **68.3** | 55.0 | 41.7 | 51.7 | 63.3 | 60.0 | Reflexion |

## IS vs Direct: paired-bootstrap CI + Holm-Bonferroni-corrected McNemar p

| LLM | n | Direct | IS | Δ | 95% CI | McNemar p | **Holm p** | Sig |
|---|---|---|---|---|---|---|---|---|
| Llama 3.1 8B | 60 | 76.7% | 91.7% | +15.0 | [+6.7, +25.0] | 0.0039 | 0.0234 | ✓ |
| Llama 3.3 70B | 60 | 83.3% | 93.3% | +10.0 | [+3.3, +18.3] | 0.0312 | 0.1562 |  |
| DeepSeek V3 | 60 | 56.7% | 61.7% | +5.0 | [+0.0, +11.7] | 0.2500 | 0.5000 |  |
| Mistral Nemo 12B | 60 | 71.7% | 81.7% | +10.0 | [+3.3, +18.3] | 0.0312 | 0.1562 |  |
| Qwen 2.5 7B | 60 | 80.0% | 85.0% | +5.0 | [+0.0, +11.7] | 0.2500 | 0.5000 |  |
| Gemini 2.5 Flash | 60 | 51.7% | 60.0% | +8.3 | [+1.7, +16.7] | 0.0625 | 0.1875 |  |

## IS vs Reflexion: paired-bootstrap CI + Holm-Bonferroni-corrected McNemar p

| LLM | n | Reflexion | IS | Δ | 95% CI | McNemar p | **Holm p** | Sig |
|---|---|---|---|---|---|---|---|---|
| Llama 3.1 8B | 60 | 90.0% | 91.7% | +1.7 | [-3.3, +8.3] | 1.0000 | 1.0000 |  |
| Llama 3.3 70B | 60 | 96.7% | 93.3% | -3.3 | [-10.0, +3.3] | 0.6250 | 1.0000 |  |
| DeepSeek V3 | 60 | 71.7% | 61.7% | -10.0 | [-20.0, +0.0] | 0.1094 | 0.5469 |  |
| Mistral Nemo 12B | 60 | 85.0% | 81.7% | -3.3 | [-13.3, +6.7] | 0.7539 | 1.0000 |  |
| Qwen 2.5 7B | 60 | 83.3% | 85.0% | +1.7 | [-3.3, +6.7] | 1.0000 | 1.0000 |  |
| Gemini 2.5 Flash | 60 | 68.3% | 60.0% | -8.3 | [-16.7, -1.7] | 0.0625 | 0.3750 |  |

## Decision tree status

- IS Holm-significant wins vs Direct: **1/6**
- IS Holm-significant wins vs Reflexion: **0/6**

**Decision: PAUSE / DISCUSS.** 1/6 IS wins vs Direct. Falls into the 1-2/6 tier in the user spec.

## Caveats

- Mistral Nemo 12B: ToT partial (n=51/60) due to rate-limit skips.
- Qwen 2.5 7B: ToT partial (n=22/60) due to rate-limit skips.