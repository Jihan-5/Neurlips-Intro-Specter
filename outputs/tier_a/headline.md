# Tier-A Headline Results (draft for §5)

## Per-benchmark main results

| benchmark                             | method            |   n |   success |   violation |   tokens_total |   delta_success_vs_direct |   ci_low |   ci_high |   mcnemar_p |   holm_success_adj |
|:--------------------------------------|:------------------|----:|----------:|------------:|---------------:|--------------------------:|---------:|----------:|------------:|-------------------:|
| Profile-PFQA (Llama 3.3 70B)          | direct            |  60 |     0.967 |       0.033 |        858.233 |                   nan     |  nan     |   nan     |     nan     |            nan     |
| Profile-PFQA (Llama 3.3 70B)          | full_regen        |  60 |     0.950 |       0.050 |       1711.250 |                    -0.017 |   -0.050 |     0.000 |       1.000 |              1.000 |
| Profile-PFQA (Llama 3.3 70B)          | intro_specter_llm |  60 |     0.983 |       0.017 |       2177.917 |                     0.017 |    0.000 |     0.050 |       1.000 |              1.000 |
| Profile-PFQA (Llama 3.3 70B)          | reflexion         |  60 |     0.983 |       0.017 |        964.700 |                     0.017 |    0.000 |     0.050 |       1.000 |              1.000 |
| Profile-PFQA (Llama 3.3 70B)          | self_refine       |  60 |     0.417 |       0.583 |       2265.717 |                    -0.550 |   -0.667 |    -0.417 |       0.000 |              0.000 |
| Profile-PFQA (Llama 3.1 8B)           | direct            |  60 |     0.850 |       0.150 |        736.983 |                   nan     |  nan     |   nan     |     nan     |            nan     |
| Profile-PFQA (Llama 3.1 8B)           | full_regen        |  60 |     0.833 |       0.167 |       1501.450 |                    -0.017 |   -0.100 |     0.067 |       1.000 |              1.000 |
| Profile-PFQA (Llama 3.1 8B)           | intro_specter_llm |  60 |     0.900 |       0.100 |       1887.450 |                     0.050 |    0.000 |     0.117 |       0.250 |              0.500 |
| Profile-PFQA (Llama 3.1 8B)           | reflexion         |  60 |     0.917 |       0.083 |       1194.933 |                     0.067 |    0.017 |     0.133 |       0.125 |              0.375 |
| Profile-PFQA (Llama 3.1 8B)           | self_refine       |  60 |     0.317 |       0.683 |       1902.467 |                    -0.533 |   -0.667 |    -0.400 |       0.000 |              0.000 |
| Profile-PFQA (DeepSeek V3)            | direct            |  60 |     0.750 |       0.250 |        873.100 |                   nan     |  nan     |   nan     |     nan     |            nan     |
| Profile-PFQA (DeepSeek V3)            | full_regen        |  60 |     0.733 |       0.267 |       1736.450 |                    -0.017 |   -0.117 |     0.083 |       1.000 |              1.000 |
| Profile-PFQA (DeepSeek V3)            | intro_specter_llm |  60 |     0.883 |       0.117 |       2358.317 |                     0.133 |    0.050 |     0.233 |       0.008 |              0.023 |
| Profile-PFQA (DeepSeek V3)            | reflexion         |  60 |     0.867 |       0.133 |       1842.983 |                     0.117 |    0.050 |     0.200 |       0.016 |              0.031 |
| Profile-PFQA (DeepSeek V3)            | self_refine       |  60 |     0.433 |       0.567 |       2369.483 |                    -0.317 |   -0.433 |    -0.200 |       0.000 |              0.000 |
| Profile-PFQA (DeepSeek V3.1)          | direct            |  60 |     0.750 |       0.250 |        860.550 |                   nan     |  nan     |   nan     |     nan     |            nan     |
| Profile-PFQA (DeepSeek V3.1)          | full_regen        |  60 |     0.800 |       0.200 |       1702.400 |                     0.050 |   -0.050 |     0.150 |       0.508 |              0.508 |
| Profile-PFQA (DeepSeek V3.1)          | intro_specter_llm |  60 |     0.817 |       0.183 |       2355.050 |                     0.067 |    0.017 |     0.133 |       0.125 |              0.375 |
| Profile-PFQA (DeepSeek V3.1)          | reflexion         |  60 |     0.817 |       0.183 |       2104.333 |                     0.067 |    0.017 |     0.133 |       0.125 |              0.375 |
| Profile-PFQA (DeepSeek V3.1)          | self_refine       |  60 |     0.383 |       0.617 |       2356.567 |                    -0.367 |   -0.483 |    -0.250 |       0.000 |              0.000 |
| Profile-PFQA (gpt-oss-20b)            | direct            |  60 |     0.500 |       0.500 |        963.800 |                   nan     |  nan     |   nan     |     nan     |            nan     |
| Profile-PFQA (gpt-oss-20b)            | full_regen        |  60 |     0.450 |       0.550 |       1988.000 |                    -0.050 |   -0.133 |     0.017 |       0.375 |              0.500 |
| Profile-PFQA (gpt-oss-20b)            | intro_specter_llm |  60 |     0.600 |       0.400 |       2792.400 |                     0.100 |    0.033 |     0.183 |       0.031 |              0.094 |
| Profile-PFQA (gpt-oss-20b)            | reflexion         |  60 |     0.967 |       0.033 |       2820.000 |                     0.467 |    0.333 |     0.600 |       0.000 |              0.000 |
| Profile-PFQA (gpt-oss-20b)            | self_refine       |  60 |     0.450 |       0.550 |       2522.033 |                    -0.050 |   -0.117 |     0.000 |       0.250 |              0.500 |
| Profile-PFQA (Mistral Nemo 12B)       | direct            |  60 |     0.733 |       0.267 |        800.617 |                   nan     |  nan     |   nan     |     nan     |            nan     |
| Profile-PFQA (Mistral Nemo 12B)       | full_regen        |  60 |     0.750 |       0.250 |       1595.983 |                     0.017 |   -0.100 |     0.133 |       1.000 |              1.000 |
| Profile-PFQA (Mistral Nemo 12B)       | intro_specter_llm |  60 |     0.900 |       0.100 |       2129.433 |                     0.167 |    0.083 |     0.267 |       0.002 |              0.006 |
| Profile-PFQA (Mistral Nemo 12B)       | reflexion         |  60 |     0.767 |       0.233 |       2025.467 |                     0.033 |    0.000 |     0.083 |       0.500 |              1.000 |
| Profile-PFQA (Mistral Nemo 12B)       | self_refine       |  60 |     0.300 |       0.700 |       2117.167 |                    -0.433 |   -0.567 |    -0.317 |       0.000 |              0.000 |
| Profile-PFQA (Gemini 2.5 Flash)       | direct            |  60 |     0.450 |       0.550 |        970.983 |                   nan     |  nan     |   nan     |     nan     |            nan     |
| Profile-PFQA (Gemini 2.5 Flash)       | full_regen        |  60 |     0.433 |       0.567 |       1941.167 |                    -0.017 |   -0.100 |     0.067 |       1.000 |              1.000 |
| Profile-PFQA (Gemini 2.5 Flash)       | intro_specter_llm |  60 |     0.600 |       0.400 |       2709.300 |                     0.150 |    0.067 |     0.250 |       0.004 |              0.012 |
| Profile-PFQA (Gemini 2.5 Flash)       | reflexion         |  60 |     0.733 |       0.267 |       3501.800 |                     0.283 |    0.167 |     0.400 |       0.000 |              0.000 |
| Profile-PFQA (Gemini 2.5 Flash)       | self_refine       |  60 |     0.417 |       0.583 |       2471.767 |                    -0.033 |   -0.100 |     0.033 |       0.625 |              1.000 |
| Profile-PFQA (Qwen 2.5 7B)            | direct            |  60 |     0.550 |       0.450 |        838.300 |                   nan     |  nan     |   nan     |     nan     |            nan     |
| Profile-PFQA (Qwen 2.5 7B)            | full_regen        |  60 |     0.450 |       0.550 |       1705.617 |                    -0.100 |   -0.233 |     0.033 |       0.210 |              0.420 |
| Profile-PFQA (Qwen 2.5 7B)            | intro_specter_llm |  60 |     0.750 |       0.250 |       2175.833 |                     0.200 |    0.100 |     0.300 |       0.000 |              0.002 |
| Profile-PFQA (Qwen 2.5 7B)            | reflexion         |  60 |     0.583 |       0.417 |       3203.650 |                     0.033 |    0.000 |     0.083 |       0.500 |              0.500 |
| Profile-PFQA (Qwen 2.5 7B)            | self_refine       |  60 |     0.367 |       0.633 |       2212.300 |                    -0.183 |   -0.300 |    -0.083 |       0.003 |              0.010 |
| Profile-Travel (Llama 3.3 70B)        | direct            |  60 |     0.933 |       0.067 |       1422.850 |                   nan     |  nan     |   nan     |     nan     |            nan     |
| Profile-Travel (Llama 3.3 70B)        | full_regen        |  60 |     0.933 |       0.067 |       2772.167 |                     0.000 |   -0.083 |     0.083 |       1.000 |              1.000 |
| Profile-Travel (Llama 3.3 70B)        | intro_specter_llm |  60 |     0.950 |       0.050 |       4058.783 |                     0.017 |    0.000 |     0.050 |       1.000 |              1.000 |
| Profile-Travel (Llama 3.3 70B)        | reflexion         |  60 |     1.000 |       0.000 |       1657.250 |                     0.067 |    0.017 |     0.133 |       0.125 |              0.625 |
| Profile-Travel (Llama 3.3 70B)        | self_refine       |  60 |     0.967 |       0.033 |       4365.600 |                     0.033 |    0.000 |     0.083 |       0.500 |              1.000 |
| Profile-Travel (Llama 3.1 8B)         | direct            |  60 |     1.000 |       0.000 |       1463.600 |                   nan     |  nan     |   nan     |     nan     |            nan     |
| Profile-Travel (Llama 3.1 8B)         | full_regen        |  60 |     0.983 |       0.017 |       2855.950 |                    -0.017 |   -0.050 |     0.000 |       1.000 |              1.000 |
| Profile-Travel (Llama 3.1 8B)         | intro_specter_llm |  60 |     1.000 |       0.000 |       4574.317 |                     0.000 |    0.000 |     0.000 |       1.000 |              1.000 |
| Profile-Travel (Llama 3.1 8B)         | reflexion         |  60 |     1.000 |       0.000 |       1458.200 |                     0.000 |    0.000 |     0.000 |       1.000 |              1.000 |
| Profile-Travel (Llama 3.1 8B)         | self_refine       |  60 |     0.983 |       0.017 |       4627.100 |                    -0.017 |   -0.050 |     0.000 |       1.000 |              1.000 |
| Profile-Travel (DeepSeek V3)          | direct            |  60 |     0.717 |       0.283 |       1196.350 |                   nan     |  nan     |   nan     |     nan     |            nan     |
| Profile-Travel (DeepSeek V3)          | full_regen        |  60 |     0.583 |       0.417 |       2361.950 |                    -0.133 |   -0.283 |     0.017 |       0.134 |              0.268 |
| Profile-Travel (DeepSeek V3)          | intro_specter_llm |  60 |     0.850 |       0.150 |       3897.483 |                     0.133 |    0.050 |     0.233 |       0.008 |              0.023 |
| Profile-Travel (DeepSeek V3)          | reflexion         |  60 |     0.733 |       0.267 |       3980.000 |                     0.017 |   -0.033 |     0.083 |       1.000 |              1.000 |
| Profile-Travel (DeepSeek V3)          | self_refine       |  59 |     0.475 |       0.525 |       3688.458 |                    -0.254 |   -0.407 |    -0.102 |       0.003 |              0.010 |
| Profile-Travel (DeepSeek V3.1)        | direct            |  60 |     0.617 |       0.383 |       1177.033 |                   nan     |  nan     |   nan     |     nan     |            nan     |
| Profile-Travel (DeepSeek V3.1)        | full_regen        |  60 |     0.500 |       0.500 |       2430.883 |                    -0.117 |   -0.250 |     0.017 |       0.167 |              0.334 |
| Profile-Travel (DeepSeek V3.1)        | intro_specter_llm |  60 |     0.800 |       0.200 |       3817.850 |                     0.183 |    0.067 |     0.300 |       0.007 |              0.030 |
| Profile-Travel (DeepSeek V3.1)        | reflexion         |  60 |     0.650 |       0.350 |       4530.550 |                     0.033 |    0.000 |     0.083 |       0.500 |              0.500 |
| Profile-Travel (DeepSeek V3.1)        | self_refine       |  60 |     0.467 |       0.533 |       3760.517 |                    -0.150 |   -0.283 |    -0.017 |       0.049 |              0.147 |
| Profile-Travel (gpt-oss-20b)          | direct            |  60 |     0.933 |       0.067 |       1859.517 |                   nan     |  nan     |   nan     |     nan     |            nan     |
| Profile-Travel (gpt-oss-20b)          | full_regen        |  60 |     0.883 |       0.117 |       4009.683 |                    -0.050 |   -0.150 |     0.050 |       0.549 |              1.000 |
| Profile-Travel (gpt-oss-20b)          | intro_specter_llm |  59 |     0.966 |       0.034 |       4806.373 |                     0.034 |    0.000 |     0.085 |       0.500 |              1.000 |
| Profile-Travel (gpt-oss-20b)          | reflexion         |  60 |     0.967 |       0.033 |       2497.333 |                     0.033 |    0.000 |     0.083 |       0.500 |              1.000 |
| Profile-Travel (gpt-oss-20b)          | self_refine       |  53 |     0.943 |       0.057 |       5799.340 |                     0.000 |   -0.057 |     0.057 |       1.000 |              1.000 |
| Profile-Travel (Mistral Nemo 12B)     | direct            |  60 |     0.983 |       0.017 |       1217.450 |                   nan     |  nan     |   nan     |     nan     |            nan     |
| Profile-Travel (Mistral Nemo 12B)     | full_regen        |  60 |     0.967 |       0.033 |       2423.750 |                    -0.017 |   -0.083 |     0.033 |       1.000 |              1.000 |
| Profile-Travel (Mistral Nemo 12B)     | intro_specter_llm |  60 |     0.983 |       0.017 |       3762.267 |                     0.000 |    0.000 |     0.000 |       1.000 |              1.000 |
| Profile-Travel (Mistral Nemo 12B)     | reflexion         |  60 |     1.000 |       0.000 |       1251.317 |                     0.017 |    0.000 |     0.050 |       1.000 |              1.000 |
| Profile-Travel (Mistral Nemo 12B)     | self_refine       |  60 |     0.950 |       0.050 |       3939.117 |                    -0.033 |   -0.100 |     0.033 |       0.625 |              1.000 |
| Profile-Travel (Gemini 2.5 Flash)     | direct            |  60 |     0.900 |       0.100 |       2001.367 |                   nan     |  nan     |   nan     |     nan     |            nan     |
| Profile-Travel (Gemini 2.5 Flash)     | full_regen        |  60 |     0.933 |       0.067 |       3979.967 |                     0.033 |   -0.067 |     0.133 |       0.754 |              1.000 |
| Profile-Travel (Gemini 2.5 Flash)     | intro_specter_llm |  60 |     0.917 |       0.083 |       6240.383 |                     0.017 |    0.000 |     0.050 |       1.000 |              1.000 |
| Profile-Travel (Gemini 2.5 Flash)     | reflexion         |  60 |     1.000 |       0.000 |       2529.267 |                     0.100 |    0.033 |     0.183 |       0.031 |              0.156 |
| Profile-Travel (Gemini 2.5 Flash)     | self_refine       |  60 |     0.917 |       0.083 |       5760.017 |                     0.017 |    0.000 |     0.050 |       1.000 |              1.000 |
| Profile-Travel (Qwen 2.5 7B)          | direct            |  60 |     0.917 |       0.083 |       1359.233 |                   nan     |  nan     |   nan     |     nan     |            nan     |
| Profile-Travel (Qwen 2.5 7B)          | full_regen        |  60 |     0.933 |       0.067 |       2776.067 |                     0.017 |   -0.067 |     0.100 |       1.000 |              1.000 |
| Profile-Travel (Qwen 2.5 7B)          | intro_specter_llm |  60 |     0.983 |       0.017 |       4058.767 |                     0.067 |    0.017 |     0.133 |       0.125 |              0.500 |
| Profile-Travel (Qwen 2.5 7B)          | reflexion         |  60 |     0.950 |       0.050 |       2041.517 |                     0.033 |    0.000 |     0.083 |       0.500 |              1.000 |
| Profile-Travel (Qwen 2.5 7B)          | self_refine       |  59 |     0.898 |       0.102 |       4254.966 |                    -0.017 |   -0.068 |     0.034 |       1.000 |              1.000 |
| Profile-TauBench (Llama 3.3 70B)      | direct            |  60 |     1.000 |       0.000 |        936.617 |                   nan     |  nan     |   nan     |     nan     |            nan     |
| Profile-TauBench (Llama 3.3 70B)      | full_regen        |  60 |     1.000 |       0.000 |       1859.167 |                     0.000 |    0.000 |     0.000 |       1.000 |              1.000 |
| Profile-TauBench (Llama 3.3 70B)      | intro_specter_llm |  60 |     1.000 |       0.000 |       2516.300 |                     0.000 |    0.000 |     0.000 |       1.000 |              1.000 |
| Profile-TauBench (Llama 3.3 70B)      | reflexion         |  60 |     1.000 |       0.000 |        936.617 |                     0.000 |    0.000 |     0.000 |       1.000 |              1.000 |
| Profile-TauBench (Llama 3.3 70B)      | self_refine       |  60 |     1.000 |       0.000 |       2580.533 |                     0.000 |    0.000 |     0.000 |       1.000 |              1.000 |
| Profile-TauBench (Llama 3.1 8B)       | direct            |  60 |     0.600 |       0.400 |        999.067 |                   nan     |  nan     |   nan     |     nan     |            nan     |
| Profile-TauBench (Llama 3.1 8B)       | full_regen        |  60 |     0.583 |       0.417 |       1986.583 |                    -0.017 |   -0.167 |     0.117 |       1.000 |              1.000 |
| Profile-TauBench (Llama 3.1 8B)       | intro_specter_llm |  60 |     0.633 |       0.367 |       2926.717 |                     0.033 |   -0.033 |     0.100 |       0.625 |              1.000 |
| Profile-TauBench (Llama 3.1 8B)       | reflexion         |  60 |     0.933 |       0.067 |       2706.650 |                     0.333 |    0.217 |     0.450 |       0.000 |              0.000 |
| Profile-TauBench (Llama 3.1 8B)       | self_refine       |  60 |     0.533 |       0.467 |       2830.117 |                    -0.067 |   -0.250 |     0.117 |       0.608 |              1.000 |
| Profile-TauBench (DeepSeek V3)        | direct            |  60 |     1.000 |       0.000 |        900.217 |                   nan     |  nan     |   nan     |     nan     |            nan     |
| Profile-TauBench (DeepSeek V3)        | full_regen        |  60 |     1.000 |       0.000 |       1788.317 |                     0.000 |    0.000 |     0.000 |       1.000 |              1.000 |
| Profile-TauBench (DeepSeek V3)        | intro_specter_llm |  60 |     1.000 |       0.000 |       2478.367 |                     0.000 |    0.000 |     0.000 |       1.000 |              1.000 |
| Profile-TauBench (DeepSeek V3)        | reflexion         |  60 |     1.000 |       0.000 |        900.217 |                     0.000 |    0.000 |     0.000 |       1.000 |              1.000 |
| Profile-TauBench (DeepSeek V3)        | self_refine       |  60 |     0.983 |       0.017 |       2429.467 |                    -0.017 |   -0.050 |     0.000 |       1.000 |              1.000 |
| Profile-TauBench (DeepSeek V3.1)      | direct            |  60 |     1.000 |       0.000 |        918.717 |                   nan     |  nan     |   nan     |     nan     |            nan     |
| Profile-TauBench (DeepSeek V3.1)      | full_regen        |  60 |     1.000 |       0.000 |       1801.617 |                     0.000 |    0.000 |     0.000 |       1.000 |              1.000 |
| Profile-TauBench (DeepSeek V3.1)      | intro_specter_llm |  60 |     1.000 |       0.000 |       2520.200 |                     0.000 |    0.000 |     0.000 |       1.000 |              1.000 |
| Profile-TauBench (DeepSeek V3.1)      | reflexion         |  60 |     1.000 |       0.000 |        918.717 |                     0.000 |    0.000 |     0.000 |       1.000 |              1.000 |
| Profile-TauBench (DeepSeek V3.1)      | self_refine       |  60 |     0.917 |       0.083 |       2465.433 |                    -0.083 |   -0.167 |    -0.017 |       0.062 |              0.312 |
| Profile-TauBench (gpt-oss-20b)        | direct            |  60 |     1.000 |       0.000 |       1126.617 |                   nan     |  nan     |   nan     |     nan     |            nan     |
| Profile-TauBench (gpt-oss-20b)        | full_regen        |  60 |     0.983 |       0.017 |       2258.783 |                    -0.017 |   -0.050 |     0.000 |       1.000 |              1.000 |
| Profile-TauBench (gpt-oss-20b)        | intro_specter_llm |  60 |     1.000 |       0.000 |       2761.800 |                     0.000 |    0.000 |     0.000 |       1.000 |              1.000 |
| Profile-TauBench (gpt-oss-20b)        | reflexion         |  60 |     1.000 |       0.000 |       1126.617 |                     0.000 |    0.000 |     0.000 |       1.000 |              1.000 |
| Profile-TauBench (gpt-oss-20b)        | self_refine       |  60 |     0.983 |       0.017 |       2781.700 |                    -0.017 |   -0.050 |     0.000 |       1.000 |              1.000 |
| Profile-TauBench (Mistral Nemo 12B)   | direct            |  60 |     0.683 |       0.317 |        992.050 |                   nan     |  nan     |   nan     |     nan     |            nan     |
| Profile-TauBench (Mistral Nemo 12B)   | full_regen        |  60 |     0.633 |       0.367 |       1937.083 |                    -0.050 |   -0.200 |     0.083 |       0.648 |              1.000 |
| Profile-TauBench (Mistral Nemo 12B)   | intro_specter_llm |  60 |     0.717 |       0.283 |       2804.717 |                     0.033 |    0.000 |     0.083 |       0.500 |              1.000 |
| Profile-TauBench (Mistral Nemo 12B)   | reflexion         |  60 |     0.950 |       0.050 |       2255.833 |                     0.267 |    0.167 |     0.383 |       0.000 |              0.000 |
| Profile-TauBench (Mistral Nemo 12B)   | self_refine       |  60 |     0.617 |       0.383 |       2791.217 |                    -0.067 |   -0.250 |     0.117 |       0.597 |              1.000 |
| Profile-TauBench (Gemini 2.5 Flash)   | direct            |  60 |     1.000 |       0.000 |       1292.817 |                   nan     |  nan     |   nan     |     nan     |            nan     |
| Profile-TauBench (Gemini 2.5 Flash)   | full_regen        |  60 |     1.000 |       0.000 |       2548.833 |                     0.000 |    0.000 |     0.000 |       1.000 |              1.000 |
| Profile-TauBench (Gemini 2.5 Flash)   | intro_specter_llm |  60 |     1.000 |       0.000 |       3651.100 |                     0.000 |    0.000 |     0.000 |       1.000 |              1.000 |
| Profile-TauBench (Gemini 2.5 Flash)   | reflexion         |  60 |     1.000 |       0.000 |       1292.817 |                     0.000 |    0.000 |     0.000 |       1.000 |              1.000 |
| Profile-TauBench (Gemini 2.5 Flash)   | self_refine       |  60 |     1.000 |       0.000 |       3553.450 |                     0.000 |    0.000 |     0.000 |       1.000 |              1.000 |
| Profile-TauBench (Qwen 2.5 7B)        | direct            |  60 |     0.783 |       0.217 |        878.683 |                   nan     |  nan     |   nan     |     nan     |            nan     |
| Profile-TauBench (Qwen 2.5 7B)        | full_regen        |  60 |     0.750 |       0.250 |       1780.917 |                    -0.033 |   -0.150 |     0.083 |       0.774 |              0.774 |
| Profile-TauBench (Qwen 2.5 7B)        | intro_specter_llm |  60 |     0.933 |       0.067 |       2517.450 |                     0.150 |    0.067 |     0.250 |       0.004 |              0.012 |
| Profile-TauBench (Qwen 2.5 7B)        | reflexion         |  60 |     0.967 |       0.033 |       1575.833 |                     0.183 |    0.083 |     0.283 |       0.001 |              0.004 |
| Profile-TauBench (Qwen 2.5 7B)        | self_refine       |  60 |     0.633 |       0.367 |       2350.350 |                    -0.150 |   -0.333 |     0.033 |       0.163 |              0.326 |
| Profile-HotpotQA (DeepSeek V3)        | direct            |  60 |     0.833 |       0.167 |        945.750 |                   nan     |  nan     |   nan     |     nan     |            nan     |
| Profile-HotpotQA (DeepSeek V3)        | full_regen        |  60 |     0.867 |       0.133 |       1882.267 |                     0.033 |   -0.050 |     0.133 |       0.727 |              1.000 |
| Profile-HotpotQA (DeepSeek V3)        | intro_specter_llm |  60 |     0.850 |       0.150 |       2668.783 |                     0.017 |    0.000 |     0.050 |       1.000 |              1.000 |
| Profile-HotpotQA (DeepSeek V3)        | reflexion         |  60 |     0.917 |       0.083 |       1755.800 |                     0.083 |    0.017 |     0.150 |       0.062 |              0.188 |
| Profile-HotpotQA (DeepSeek V3)        | self_refine       |  60 |     0.367 |       0.633 |       2672.933 |                    -0.467 |   -0.617 |    -0.333 |       0.000 |              0.000 |
| Profile-HotpotQA (Mistral Nemo 12B)   | direct            |  60 |     0.667 |       0.333 |        840.950 |                   nan     |  nan     |   nan     |     nan     |            nan     |
| Profile-HotpotQA (Mistral Nemo 12B)   | full_regen        |  60 |     0.667 |       0.333 |       1717.317 |                     0.000 |   -0.150 |     0.150 |       1.000 |              1.000 |
| Profile-HotpotQA (Mistral Nemo 12B)   | intro_specter_llm |  60 |     0.817 |       0.183 |       2304.633 |                     0.150 |    0.067 |     0.250 |       0.004 |              0.008 |
| Profile-HotpotQA (Mistral Nemo 12B)   | reflexion         |  60 |     0.850 |       0.150 |       2321.683 |                     0.183 |    0.100 |     0.283 |       0.001 |              0.003 |
| Profile-HotpotQA (Mistral Nemo 12B)   | self_refine       |  60 |     0.367 |       0.633 |       2330.117 |                    -0.300 |   -0.433 |    -0.167 |       0.000 |              0.000 |
| Profile-HotpotQA (Qwen 2.5 7B)        | direct            |  41 |     0.537 |       0.463 |        943.878 |                   nan     |  nan     |   nan     |     nan     |            nan     |
| Profile-HotpotQA (Qwen 2.5 7B)        | full_regen        |  40 |     0.475 |       0.525 |       1903.025 |                    -0.075 |   -0.200 |     0.050 |       0.453 |              0.453 |
| Profile-HotpotQA (Qwen 2.5 7B)        | intro_specter_llm |  40 |     0.750 |       0.250 |       2545.225 |                     0.200 |    0.075 |     0.325 |       0.008 |              0.023 |
| Profile-HotpotQA (Qwen 2.5 7B)        | reflexion         |  40 |     0.650 |       0.350 |       3509.250 |                     0.100 |    0.025 |     0.200 |       0.125 |              0.250 |
| Profile-HotpotQA (Qwen 2.5 7B)        | self_refine       |  40 |     0.225 |       0.775 |       2600.175 |                    -0.325 |   -0.475 |    -0.175 |       0.000 |              0.001 |
| Profile-HotpotQA (Gemini 2.5 Flash)   | direct            |  60 |     0.417 |       0.583 |       1119.533 |                   nan     |  nan     |   nan     |     nan     |            nan     |
| Profile-HotpotQA (Gemini 2.5 Flash)   | full_regen        |  60 |     0.450 |       0.550 |       2234.283 |                     0.033 |   -0.067 |     0.133 |       0.754 |              1.000 |
| Profile-HotpotQA (Gemini 2.5 Flash)   | intro_specter_llm |  60 |     0.600 |       0.400 |       3283.650 |                     0.183 |    0.083 |     0.283 |       0.001 |              0.003 |
| Profile-HotpotQA (Gemini 2.5 Flash)   | reflexion         |  60 |     0.717 |       0.283 |       4251.850 |                     0.300 |    0.183 |     0.417 |       0.000 |              0.000 |
| Profile-HotpotQA (Gemini 2.5 Flash)   | self_refine       |  60 |     0.383 |       0.617 |       3022.833 |                    -0.033 |   -0.117 |     0.050 |       0.688 |              1.000 |
| Profile-ALFWorld (DeepSeek V3)        | direct            |  60 |     0.083 |       0.917 |        886.167 |                   nan     |  nan     |   nan     |     nan     |            nan     |
| Profile-ALFWorld (DeepSeek V3)        | full_regen        |  60 |     0.117 |       0.883 |       1764.000 |                     0.033 |   -0.067 |     0.133 |       0.754 |              0.906 |
| Profile-ALFWorld (DeepSeek V3)        | intro_specter_llm |  57 |     0.158 |       0.842 |       2514.561 |                     0.070 |    0.018 |     0.140 |       0.125 |              0.375 |
| Profile-ALFWorld (DeepSeek V3)        | reflexion         |  60 |     0.717 |       0.283 |       4881.750 |                     0.633 |    0.517 |     0.750 |       0.000 |              0.000 |
| Profile-ALFWorld (DeepSeek V3)        | self_refine       |  59 |     0.119 |       0.881 |       2599.881 |                     0.051 |   -0.034 |     0.136 |       0.453 |              0.906 |
| Profile-ALFWorld (Mistral Nemo 12B)   | direct            |  60 |     0.583 |       0.417 |        782.417 |                   nan     |  nan     |   nan     |     nan     |            nan     |
| Profile-ALFWorld (Mistral Nemo 12B)   | full_regen        |  60 |     0.500 |       0.500 |       1574.033 |                    -0.083 |   -0.250 |     0.083 |       0.424 |              0.849 |
| Profile-ALFWorld (Mistral Nemo 12B)   | intro_specter_llm |  60 |     0.833 |       0.167 |       2172.333 |                     0.250 |    0.133 |     0.367 |       0.000 |              0.001 |
| Profile-ALFWorld (Mistral Nemo 12B)   | reflexion         |  60 |     0.583 |       0.417 |       3074.900 |                     0.000 |   -0.050 |     0.050 |       1.000 |              1.000 |
| Profile-ALFWorld (Mistral Nemo 12B)   | self_refine       |  60 |     0.467 |       0.533 |       2184.283 |                    -0.117 |   -0.200 |    -0.050 |       0.016 |              0.047 |
| Profile-ALFWorld (Qwen 2.5 7B)        | direct            |  60 |     0.467 |       0.533 |        880.183 |                   nan     |  nan     |   nan     |     nan     |            nan     |
| Profile-ALFWorld (Qwen 2.5 7B)        | full_regen        |  60 |     0.550 |       0.450 |       1765.567 |                     0.083 |   -0.067 |     0.233 |       0.383 |              0.767 |
| Profile-ALFWorld (Qwen 2.5 7B)        | intro_specter_llm |  60 |     0.683 |       0.317 |       2604.100 |                     0.217 |    0.100 |     0.333 |       0.001 |              0.003 |
| Profile-ALFWorld (Qwen 2.5 7B)        | reflexion         |  60 |     0.717 |       0.283 |       3475.500 |                     0.250 |    0.150 |     0.367 |       0.000 |              0.000 |
| Profile-ALFWorld (Qwen 2.5 7B)        | self_refine       |  60 |     0.433 |       0.567 |       2539.800 |                    -0.033 |   -0.100 |     0.033 |       0.625 |              0.767 |
| Profile-ALFWorld (Gemini 2.5 Flash)   | direct            |  60 |     0.383 |       0.617 |        934.650 |                   nan     |  nan     |   nan     |     nan     |            nan     |
| Profile-ALFWorld (Gemini 2.5 Flash)   | full_regen        |  60 |     0.450 |       0.550 |       1888.183 |                     0.067 |   -0.083 |     0.233 |       0.541 |              1.000 |
| Profile-ALFWorld (Gemini 2.5 Flash)   | intro_specter_llm |  60 |     0.683 |       0.317 |       2862.850 |                     0.300 |    0.183 |     0.433 |       0.000 |              0.000 |
| Profile-ALFWorld (Gemini 2.5 Flash)   | reflexion         |  60 |     0.917 |       0.083 |       3083.667 |                     0.533 |    0.400 |     0.667 |       0.000 |              0.000 |
| Profile-ALFWorld (Gemini 2.5 Flash)   | self_refine       |  60 |     0.383 |       0.617 |       2549.500 |                     0.000 |   -0.050 |     0.050 |       1.000 |              1.000 |
| Profile-WebShop (DeepSeek V3)         | direct            |  60 |     0.100 |       0.900 |        874.850 |                   nan     |  nan     |   nan     |     nan     |            nan     |
| Profile-WebShop (DeepSeek V3)         | full_regen        |  60 |     0.083 |       0.917 |       1756.200 |                    -0.017 |   -0.100 |     0.067 |       1.000 |              1.000 |
| Profile-WebShop (DeepSeek V3)         | intro_specter_llm |  58 |     0.121 |       0.879 |       2666.414 |                     0.017 |    0.000 |     0.052 |       1.000 |              1.000 |
| Profile-WebShop (DeepSeek V3)         | reflexion         |  60 |     0.100 |       0.900 |       6085.300 |                     0.000 |   -0.050 |     0.050 |       1.000 |              1.000 |
| Profile-WebShop (DeepSeek V3)         | self_refine       |  60 |     0.117 |       0.883 |       2466.000 |                     0.017 |   -0.033 |     0.083 |       1.000 |              1.000 |
| Profile-WebShop (Mistral Nemo 12B)    | direct            |  60 |     0.100 |       0.900 |        861.817 |                   nan     |  nan     |   nan     |     nan     |            nan     |
| Profile-WebShop (Mistral Nemo 12B)    | full_regen        |  60 |     0.183 |       0.817 |       1712.017 |                     0.083 |   -0.017 |     0.183 |       0.227 |              0.680 |
| Profile-WebShop (Mistral Nemo 12B)    | intro_specter_llm |  60 |     0.167 |       0.833 |       2472.617 |                     0.067 |    0.017 |     0.133 |       0.125 |              0.500 |
| Profile-WebShop (Mistral Nemo 12B)    | reflexion         |  60 |     0.100 |       0.900 |       5971.567 |                     0.000 |    0.000 |     0.000 |       1.000 |              1.000 |
| Profile-WebShop (Mistral Nemo 12B)    | self_refine       |  60 |     0.083 |       0.917 |       2326.583 |                    -0.017 |   -0.050 |     0.000 |       1.000 |              1.000 |
| Profile-WebShop (Qwen 2.5 7B)         | direct            |  60 |     0.267 |       0.733 |        877.433 |                   nan     |  nan     |   nan     |     nan     |            nan     |
| Profile-WebShop (Qwen 2.5 7B)         | full_regen        |  60 |     0.117 |       0.883 |       1751.033 |                    -0.150 |   -0.267 |    -0.050 |       0.022 |              0.090 |
| Profile-WebShop (Qwen 2.5 7B)         | intro_specter_llm |  58 |     0.241 |       0.759 |       2368.879 |                    -0.017 |   -0.103 |     0.069 |       1.000 |              1.000 |
| Profile-WebShop (Qwen 2.5 7B)         | reflexion         |  60 |     0.367 |       0.633 |       4603.767 |                     0.100 |    0.033 |     0.183 |       0.031 |              0.094 |
| Profile-WebShop (Qwen 2.5 7B)         | self_refine       |  60 |     0.217 |       0.783 |       2349.883 |                    -0.050 |   -0.117 |     0.000 |       0.250 |              0.500 |
| Profile-WebShop (Gemini 2.5 Flash)    | direct            |  60 |     0.283 |       0.717 |       1077.400 |                   nan     |  nan     |   nan     |     nan     |            nan     |
| Profile-WebShop (Gemini 2.5 Flash)    | full_regen        |  60 |     0.317 |       0.683 |       2172.250 |                     0.033 |   -0.067 |     0.133 |       0.754 |              1.000 |
| Profile-WebShop (Gemini 2.5 Flash)    | intro_specter_llm |  60 |     0.317 |       0.683 |       3331.867 |                     0.033 |    0.000 |     0.083 |       0.500 |              1.000 |
| Profile-WebShop (Gemini 2.5 Flash)    | reflexion         |  60 |     0.567 |       0.433 |       5493.783 |                     0.283 |    0.167 |     0.400 |       0.000 |              0.000 |
| Profile-WebShop (Gemini 2.5 Flash)    | self_refine       |  60 |     0.333 |       0.667 |       3123.683 |                     0.050 |   -0.017 |     0.117 |       0.375 |              1.000 |
| Profile-MuSiQue (DeepSeek V3)         | direct            |  60 |     0.817 |       0.183 |        896.100 |                   nan     |  nan     |   nan     |     nan     |            nan     |
| Profile-MuSiQue (DeepSeek V3)         | full_regen        |  60 |     0.850 |       0.150 |       1789.383 |                     0.033 |   -0.083 |     0.150 |       0.791 |              1.000 |
| Profile-MuSiQue (DeepSeek V3)         | intro_specter_llm |  60 |     0.933 |       0.067 |       2427.750 |                     0.117 |    0.050 |     0.200 |       0.016 |              0.094 |
| Profile-MuSiQue (DeepSeek V3)         | react             |  60 |     0.867 |       0.133 |       2101.683 |                     0.050 |   -0.067 |     0.167 |       0.581 |              1.000 |
| Profile-MuSiQue (DeepSeek V3)         | reflexion         |  60 |     0.883 |       0.117 |       1831.583 |                     0.067 |    0.017 |     0.133 |       0.125 |              0.625 |
| Profile-MuSiQue (DeepSeek V3)         | self_refine       |  60 |     0.300 |       0.700 |       2496.667 |                    -0.517 |   -0.650 |    -0.367 |       0.000 |              0.000 |
| Profile-MuSiQue (DeepSeek V3)         | selfcheckgpt      |  60 |     0.783 |       0.217 |       3667.383 |                    -0.033 |   -0.083 |     0.000 |       0.500 |              1.000 |
| Profile-MuSiQue (DeepSeek V3)         | tot               |  60 |     0.867 |       0.133 |       7594.533 |                     0.050 |   -0.050 |     0.150 |       0.508 |              1.000 |
| Profile-MuSiQue (Mistral Nemo 12B)    | direct            |  60 |     0.783 |       0.217 |        843.317 |                   nan     |  nan     |   nan     |     nan     |            nan     |
| Profile-MuSiQue (Mistral Nemo 12B)    | full_regen        |  60 |     0.767 |       0.233 |       1688.983 |                    -0.017 |   -0.150 |     0.117 |       1.000 |              1.000 |
| Profile-MuSiQue (Mistral Nemo 12B)    | intro_specter_llm |  60 |     0.883 |       0.117 |       2312.583 |                     0.100 |    0.033 |     0.183 |       0.031 |              0.156 |
| Profile-MuSiQue (Mistral Nemo 12B)    | react             |  60 |     0.600 |       0.400 |       1917.683 |                    -0.183 |   -0.317 |    -0.067 |       0.013 |              0.076 |
| Profile-MuSiQue (Mistral Nemo 12B)    | reflexion         |  60 |     0.883 |       0.117 |       1791.383 |                     0.100 |    0.033 |     0.183 |       0.031 |              0.156 |
| Profile-MuSiQue (Mistral Nemo 12B)    | self_refine       |  60 |     0.450 |       0.550 |       2336.217 |                    -0.333 |   -0.483 |    -0.183 |       0.000 |              0.001 |
| Profile-MuSiQue (Mistral Nemo 12B)    | selfcheckgpt      |  59 |     0.847 |       0.153 |       3673.441 |                     0.068 |    0.000 |     0.153 |       0.219 |              0.656 |
| Profile-MuSiQue (Mistral Nemo 12B)    | tot               |  45 |     0.889 |       0.111 |      29632.333 |                     0.067 |   -0.067 |     0.200 |       0.508 |              1.000 |
| Profile-MuSiQue (Qwen 2.5 7B)         | direct            |  56 |     0.571 |       0.429 |        924.411 |                   nan     |  nan     |   nan     |     nan     |            nan     |
| Profile-MuSiQue (Qwen 2.5 7B)         | full_regen        |  59 |     0.559 |       0.441 |       1857.983 |                     0.000 |   -0.125 |     0.125 |       1.000 |              1.000 |
| Profile-MuSiQue (Qwen 2.5 7B)         | intro_specter_llm |  59 |     0.814 |       0.186 |       2487.356 |                     0.250 |    0.143 |     0.375 |       0.000 |              0.001 |
| Profile-MuSiQue (Qwen 2.5 7B)         | react             |  59 |     0.678 |       0.322 |       2019.492 |                     0.107 |    0.000 |     0.214 |       0.109 |              0.438 |
| Profile-MuSiQue (Qwen 2.5 7B)         | reflexion         |  58 |     0.707 |       0.293 |       3050.948 |                     0.127 |    0.055 |     0.218 |       0.016 |              0.094 |
| Profile-MuSiQue (Qwen 2.5 7B)         | self_refine       |  59 |     0.407 |       0.593 |       2580.780 |                    -0.179 |   -0.304 |    -0.054 |       0.021 |              0.106 |
| Profile-MuSiQue (Qwen 2.5 7B)         | selfcheckgpt      |  58 |     0.586 |       0.414 |       3669.569 |                     0.018 |   -0.036 |     0.073 |       1.000 |              1.000 |
| Profile-MuSiQue (Qwen 2.5 7B)         | tot               |  34 |     0.676 |       0.324 |      29084.324 |                     0.094 |   -0.094 |     0.281 |       0.508 |              1.000 |
| Profile-MuSiQue (Gemini 2.5 Flash)    | direct            |  60 |     0.500 |       0.500 |       1022.400 |                   nan     |  nan     |   nan     |     nan     |            nan     |
| Profile-MuSiQue (Gemini 2.5 Flash)    | full_regen        |  60 |     0.483 |       0.517 |       2071.933 |                    -0.017 |   -0.083 |     0.050 |       1.000 |              1.000 |
| Profile-MuSiQue (Gemini 2.5 Flash)    | intro_specter_llm |  60 |     0.833 |       0.167 |       2892.550 |                     0.333 |    0.217 |     0.450 |       0.000 |              0.000 |
| Profile-MuSiQue (Gemini 2.5 Flash)    | react             |  60 |     0.767 |       0.233 |       2157.700 |                     0.267 |    0.133 |     0.400 |       0.000 |              0.002 |
| Profile-MuSiQue (Gemini 2.5 Flash)    | reflexion         |  60 |     0.867 |       0.133 |       3437.700 |                     0.367 |    0.250 |     0.484 |       0.000 |              0.000 |
| Profile-MuSiQue (Gemini 2.5 Flash)    | self_refine       |  59 |     0.508 |       0.492 |       2689.169 |                     0.000 |   -0.085 |     0.085 |       1.000 |              1.000 |
| Profile-MuSiQue (Gemini 2.5 Flash)    | selfcheckgpt      |  60 |     0.500 |       0.500 |       3998.567 |                     0.000 |    0.000 |     0.000 |       1.000 |              1.000 |
| Profile-MuSiQue (Gemini 2.5 Flash)    | tot               |  60 |     0.700 |       0.300 |       6460.550 |                     0.200 |    0.067 |     0.333 |       0.008 |              0.030 |
| Profile-StrategyQA (DeepSeek V3)      | direct            |  60 |     0.717 |       0.283 |        854.067 |                   nan     |  nan     |   nan     |     nan     |            nan     |
| Profile-StrategyQA (DeepSeek V3)      | full_regen        |  60 |     0.700 |       0.300 |       1728.367 |                    -0.017 |   -0.117 |     0.083 |       1.000 |              1.000 |
| Profile-StrategyQA (DeepSeek V3)      | intro_specter_llm |  60 |     0.850 |       0.150 |       2306.583 |                     0.133 |    0.050 |     0.233 |       0.008 |              0.047 |
| Profile-StrategyQA (DeepSeek V3)      | react             |  60 |     0.683 |       0.317 |       2050.767 |                    -0.033 |   -0.167 |     0.100 |       0.804 |              1.000 |
| Profile-StrategyQA (DeepSeek V3)      | reflexion         |  60 |     0.833 |       0.167 |       2338.833 |                     0.117 |    0.050 |     0.200 |       0.016 |              0.078 |
| Profile-StrategyQA (DeepSeek V3)      | self_refine       |  60 |     0.183 |       0.817 |       2333.817 |                    -0.533 |   -0.667 |    -0.400 |       0.000 |              0.000 |
| Profile-StrategyQA (DeepSeek V3)      | selfcheckgpt      |  60 |     0.667 |       0.333 |       3768.733 |                    -0.050 |   -0.117 |     0.000 |       0.250 |              1.000 |
| Profile-StrategyQA (DeepSeek V3)      | tot               |  60 |     0.733 |       0.267 |       7422.283 |                     0.017 |   -0.100 |     0.133 |       1.000 |              1.000 |
| Profile-StrategyQA (Mistral Nemo 12B) | direct            |  60 |     0.883 |       0.117 |        821.517 |                   nan     |  nan     |   nan     |     nan     |            nan     |
| Profile-StrategyQA (Mistral Nemo 12B) | full_regen        |  60 |     0.833 |       0.167 |       1624.383 |                    -0.050 |   -0.150 |     0.050 |       0.508 |              1.000 |
| Profile-StrategyQA (Mistral Nemo 12B) | intro_specter_llm |  60 |     0.967 |       0.033 |       2225.133 |                     0.083 |    0.017 |     0.167 |       0.062 |              0.312 |
| Profile-StrategyQA (Mistral Nemo 12B) | react             |  60 |     0.550 |       0.450 |       1871.233 |                    -0.333 |   -0.467 |    -0.183 |       0.000 |              0.001 |
| Profile-StrategyQA (Mistral Nemo 12B) | reflexion         |  60 |     0.933 |       0.067 |       1430.150 |                     0.050 |    0.000 |     0.117 |       0.250 |              1.000 |
| Profile-StrategyQA (Mistral Nemo 12B) | self_refine       |  60 |     0.483 |       0.517 |       2250.767 |                    -0.400 |   -0.533 |    -0.283 |       0.000 |              0.000 |
| Profile-StrategyQA (Mistral Nemo 12B) | selfcheckgpt      |  59 |     0.831 |       0.169 |       3667.068 |                    -0.051 |   -0.119 |     0.000 |       0.250 |              1.000 |
| Profile-StrategyQA (Mistral Nemo 12B) | tot               |  41 |     0.878 |       0.122 |      27667.341 |                    -0.024 |   -0.171 |     0.122 |       1.000 |              1.000 |
| Profile-StrategyQA (Qwen 2.5 7B)      | direct            |  60 |     0.650 |       0.350 |        877.833 |                   nan     |  nan     |   nan     |     nan     |            nan     |
| Profile-StrategyQA (Qwen 2.5 7B)      | full_regen        |  60 |     0.633 |       0.367 |       1748.800 |                    -0.017 |   -0.133 |     0.100 |       1.000 |              1.000 |
| Profile-StrategyQA (Qwen 2.5 7B)      | intro_specter_llm |  60 |     0.750 |       0.250 |       2342.700 |                     0.100 |    0.033 |     0.183 |       0.031 |              0.188 |
| Profile-StrategyQA (Qwen 2.5 7B)      | react             |  60 |     0.667 |       0.333 |       1966.467 |                     0.017 |   -0.083 |     0.117 |       1.000 |              1.000 |
| Profile-StrategyQA (Qwen 2.5 7B)      | reflexion         |  60 |     0.733 |       0.267 |       2949.250 |                     0.083 |    0.017 |     0.167 |       0.062 |              0.250 |
| Profile-StrategyQA (Qwen 2.5 7B)      | self_refine       |  58 |     0.190 |       0.810 |       2427.190 |                    -0.448 |   -0.569 |    -0.328 |       0.000 |              0.000 |
| Profile-StrategyQA (Qwen 2.5 7B)      | selfcheckgpt      |  60 |     0.667 |       0.333 |       3512.733 |                     0.017 |    0.000 |     0.050 |       1.000 |              1.000 |
| Profile-StrategyQA (Qwen 2.5 7B)      | tot               |  44 |     0.773 |       0.227 |      20812.955 |                     0.182 |    0.045 |     0.318 |       0.039 |              0.193 |
| Profile-StrategyQA (Gemini 2.5 Flash) | direct            |  60 |     0.633 |       0.367 |       1091.967 |                   nan     |  nan     |   nan     |     nan     |            nan     |
| Profile-StrategyQA (Gemini 2.5 Flash) | full_regen        |  60 |     0.617 |       0.383 |       2185.517 |                    -0.017 |   -0.050 |     0.000 |       1.000 |              1.000 |
| Profile-StrategyQA (Gemini 2.5 Flash) | intro_specter_llm |  60 |     0.850 |       0.150 |       3042.683 |                     0.217 |    0.117 |     0.333 |       0.000 |              0.002 |
| Profile-StrategyQA (Gemini 2.5 Flash) | react             |  60 |     0.717 |       0.283 |       2248.633 |                     0.083 |   -0.017 |     0.183 |       0.227 |              0.680 |
| Profile-StrategyQA (Gemini 2.5 Flash) | reflexion         |  60 |     0.850 |       0.150 |       3291.350 |                     0.217 |    0.117 |     0.317 |       0.000 |              0.002 |
| Profile-StrategyQA (Gemini 2.5 Flash) | self_refine       |  59 |     0.559 |       0.441 |       2978.203 |                    -0.068 |   -0.136 |    -0.017 |       0.125 |              0.500 |
| Profile-StrategyQA (Gemini 2.5 Flash) | selfcheckgpt      |  60 |     0.617 |       0.383 |       4228.017 |                    -0.017 |   -0.050 |     0.000 |       1.000 |              1.000 |
| Profile-StrategyQA (Gemini 2.5 Flash) | tot               |  60 |     0.833 |       0.167 |       5669.850 |                     0.200 |    0.100 |     0.317 |       0.002 |              0.009 |
| Real-HotpotQA (DeepSeek V3)           | detection_only    |  60 |     0.700 |       0.300 |       3982.567 |                     0.000 |    0.000 |     0.000 |       1.000 |              1.000 |
| Real-HotpotQA (DeepSeek V3)           | direct            |  60 |     0.700 |       0.300 |       1866.617 |                   nan     |  nan     |   nan     |     nan     |            nan     |
| Real-HotpotQA (DeepSeek V3)           | full_regen        |  60 |     0.667 |       0.333 |       3749.400 |                    -0.033 |   -0.150 |     0.083 |       0.774 |              1.000 |
| Real-HotpotQA (DeepSeek V3)           | intro_specter_llm |  60 |     0.750 |       0.250 |       4432.583 |                     0.050 |    0.000 |     0.117 |       0.250 |              1.000 |
| Real-HotpotQA (DeepSeek V3)           | react             |  60 |     0.650 |       0.350 |       4142.483 |                    -0.050 |   -0.150 |     0.050 |       0.508 |              1.000 |
| Real-HotpotQA (DeepSeek V3)           | reflexion         |  60 |     0.850 |       0.150 |       4399.433 |                     0.150 |    0.067 |     0.250 |       0.004 |              0.020 |
| Real-HotpotQA (DeepSeek V3)           | self_refine       |  60 |     0.367 |       0.633 |       4489.717 |                    -0.333 |   -0.467 |    -0.183 |       0.000 |              0.001 |
| Real-HotpotQA (Mistral Nemo 12B)      | detection_only    |  60 |     0.633 |       0.367 |       4115.900 |                     0.000 |    0.000 |     0.000 |       1.000 |              1.000 |
| Real-HotpotQA (Mistral Nemo 12B)      | direct            |  60 |     0.633 |       0.367 |       1934.400 |                   nan     |  nan     |   nan     |     nan     |            nan     |
| Real-HotpotQA (Mistral Nemo 12B)      | full_regen        |  60 |     0.717 |       0.283 |       3840.967 |                     0.083 |   -0.067 |     0.233 |       0.383 |              0.767 |
| Real-HotpotQA (Mistral Nemo 12B)      | intro_specter_llm |  60 |     0.767 |       0.233 |       4565.100 |                     0.133 |    0.050 |     0.233 |       0.008 |              0.039 |
| Real-HotpotQA (Mistral Nemo 12B)      | react             |  60 |     0.467 |       0.533 |       4067.967 |                    -0.167 |   -0.300 |    -0.033 |       0.041 |              0.125 |
| Real-HotpotQA (Mistral Nemo 12B)      | reflexion         |  60 |     0.733 |       0.267 |       5455.367 |                     0.100 |    0.033 |     0.183 |       0.031 |              0.125 |
| Real-HotpotQA (Mistral Nemo 12B)      | self_refine       |  60 |     0.383 |       0.617 |       4705.250 |                    -0.250 |   -0.383 |    -0.100 |       0.003 |              0.016 |
| Real-HotpotQA (Qwen 2.5 7B)           | detection_only    |  60 |     0.533 |       0.467 |       3978.867 |                     0.000 |    0.000 |     0.000 |       1.000 |              1.000 |
| Real-HotpotQA (Qwen 2.5 7B)           | direct            |  60 |     0.533 |       0.467 |       1874.933 |                   nan     |  nan     |   nan     |     nan     |            nan     |
| Real-HotpotQA (Qwen 2.5 7B)           | full_regen        |  60 |     0.600 |       0.400 |       3735.850 |                     0.067 |   -0.050 |     0.183 |       0.388 |              1.000 |
| Real-HotpotQA (Qwen 2.5 7B)           | intro_specter_llm |  59 |     0.712 |       0.288 |       4378.797 |                     0.186 |    0.085 |     0.288 |       0.001 |              0.006 |
| Real-HotpotQA (Qwen 2.5 7B)           | react             |  60 |     0.533 |       0.467 |       4000.517 |                     0.000 |   -0.133 |     0.133 |       1.000 |              1.000 |
| Real-HotpotQA (Qwen 2.5 7B)           | reflexion         |  60 |     0.683 |       0.317 |       5852.200 |                     0.150 |    0.067 |     0.250 |       0.004 |              0.020 |
| Real-HotpotQA (Qwen 2.5 7B)           | self_refine       |  60 |     0.400 |       0.600 |       4439.567 |                    -0.133 |   -0.250 |    -0.033 |       0.039 |              0.154 |
| Real-HotpotQA (Gemini 2.5 Flash)      | detection_only    |  60 |     0.500 |       0.500 |       4681.933 |                     0.000 |    0.000 |     0.000 |       1.000 |              1.000 |
| Real-HotpotQA (Gemini 2.5 Flash)      | direct            |  60 |     0.500 |       0.500 |       2208.233 |                   nan     |  nan     |   nan     |     nan     |            nan     |
| Real-HotpotQA (Gemini 2.5 Flash)      | full_regen        |  60 |     0.417 |       0.583 |       4426.567 |                    -0.083 |   -0.200 |     0.017 |       0.227 |              0.680 |
| Real-HotpotQA (Gemini 2.5 Flash)      | intro_specter_llm |  60 |     0.633 |       0.367 |       5380.950 |                     0.133 |    0.050 |     0.217 |       0.008 |              0.039 |
| Real-HotpotQA (Gemini 2.5 Flash)      | react             |  60 |     0.600 |       0.400 |       4471.383 |                     0.100 |    0.000 |     0.200 |       0.109 |              0.438 |
| Real-HotpotQA (Gemini 2.5 Flash)      | reflexion         |  60 |     0.683 |       0.317 |       7787.067 |                     0.183 |    0.083 |     0.283 |       0.001 |              0.006 |
| Real-HotpotQA (Gemini 2.5 Flash)      | self_refine       |  59 |     0.407 |       0.593 |       5397.780 |                    -0.085 |   -0.220 |     0.034 |       0.302 |              0.680 |


## Cross-family comparison: Llama 3.3 70B → DeepSeek V3 on PFQABench-Recon

| method            |   llama_success |   deepseek_success |   delta_deepseek_minus_llama |   ci_low |   ci_high |   mcnemar_p |
|:------------------|----------------:|-------------------:|-----------------------------:|---------:|----------:|------------:|
| direct            |           0.967 |              0.750 |                       -0.217 |   -0.333 |    -0.100 |       0.001 |
| full_regen        |           0.950 |              0.733 |                       -0.217 |   -0.333 |    -0.100 |       0.001 |
| intro_specter_llm |           0.983 |              0.883 |                       -0.100 |   -0.183 |    -0.033 |       0.031 |
| reflexion         |           0.983 |              0.867 |                       -0.117 |   -0.200 |    -0.050 |       0.016 |
| self_refine       |           0.417 |              0.433 |                        0.017 |   -0.100 |     0.133 |       1.000 |

