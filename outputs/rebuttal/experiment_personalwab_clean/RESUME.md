> Historical pause snapshot. The current Llama/Mistral scope is complete; see `VALIDATION.md`, `SUMMARY.md` and `POOLED_SUMMARY.md`. Qwen is omitted by Jihan, not pending.

# PersonalWAB clean queues — paused safely

Paused 2026-09-21 after sending Ctrl-C through the two detached screen
terminals. No PersonalWAB workers or screens remain. Existing JSONL rows and
SQLite caches were not deleted or rewritten.

## Current state

- Clean compact dataset: `/Users/jas/Downloads/Neurlips-Intro-Specter/data/personalwab/compact_recommend_clean.json`
- Llama-3.1-8B: `llama-3.1-8b/direct.jsonl` — 38 rows
- Mistral-Nemo-12B: `mistral-nemo-12b/direct.jsonl` — 135 rows
- All other Llama/Mistral arm JSONLs have not started yet.
- Caches: `cache/personalwab_clean/llama-3.1-8b.sqlite` and
  `cache/personalwab_clean/mistral-nemo-12b.sqlite`
- Qwen was not resumed or modified by this pause operation.

## Resume commands

Run from the repository root after reopening the laptop. These commands load
`.env.local` without printing it, reuse the clean compact dataset, reuse the
existing per-model cache, and rely on the runner's `(task_id, seed)` resume
deduplication. Do not delete the JSONLs or caches.

```sh
screen -dmS pwab_clean_llama31 /usr/bin/caffeinate -i /bin/zsh -lc 'cd /Users/jas/Downloads/Neurlips-Intro-Specter || exit 1; set -a; source .env.local; set +a; export PERSONALWAB_COMPACT=/Users/jas/Downloads/Neurlips-Intro-Specter/data/personalwab/compact_recommend_clean.json; for pwab_arm in direct reflexion violation_reprompt iter_vrp intro_specter; do .venv/bin/python -u scripts/rebuttal_experiment_personalwab.py --model llama-3.1-8b --arms "$pwab_arm" --seeds 0,1,2 --n-examples 60 --cache-path cache/personalwab_clean/llama-3.1-8b.sqlite --output-dir outputs/rebuttal/experiment_personalwab_clean > outputs/rebuttal/experiment_personalwab_clean/logs/llama-3.1-8b__$pwab_arm.log 2>&1 || exit $?; done'

screen -dmS pwab_clean_mistral /usr/bin/caffeinate -i /bin/zsh -lc 'cd /Users/jas/Downloads/Neurlips-Intro-Specter || exit 1; set -a; source .env.local; set +a; export PERSONALWAB_COMPACT=/Users/jas/Downloads/Neurlips-Intro-Specter/data/personalwab/compact_recommend_clean.json; for pwab_arm in direct reflexion violation_reprompt iter_vrp intro_specter; do .venv/bin/python -u scripts/rebuttal_experiment_personalwab.py --model mistral-nemo-12b --arms "$pwab_arm" --seeds 0,1,2 --n-examples 60 --cache-path cache/personalwab_clean/mistral-nemo-12b.sqlite --output-dir outputs/rebuttal/experiment_personalwab_clean > outputs/rebuttal/experiment_personalwab_clean/logs/mistral-nemo-12b__$pwab_arm.log 2>&1 || exit $?; done'
```
