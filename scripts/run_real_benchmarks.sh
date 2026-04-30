#!/usr/bin/env bash
# Run the full real-benchmark matrix in phased rollout.
#
# Strategy:
#  1. Phase 0 (validation): one cheap model × one small dataset, all 7 methods.
#  2. Phase 1 (cheap models, all datasets): 3 cheap models × 4 datasets = 12 cells.
#  3. Phase 2 (expensive models, all datasets): 5 expensive models × 4 datasets = 20 cells.
#
# Each cell runs ~7 methods × 60 trials × 3 seeds. With caching (Direct's
# primed trajectory feeding into Self-Refine / Reflexion / etc.) the effective
# trial count is closer to 5×.
#
# Cost notes:
#  - OpenRouter: Mistral Nemo $0.15/M, Qwen 7B $0.06/M, Gemini Flash $0.10/M,
#    Llama 8B $0.05/M.
#  - Together: Llama 70B / DeepSeek V3 / V3.1 / gpt-oss-20b $0.20–1.10/M.
#  - With cache + 60 trials per seed × 3 seeds × 7 methods, expected cell cost
#    is $0.50–$3.00 depending on model.
#  - Total expected cost across 32 cells: ~$25–$50.
#
# Usage:
#   ./scripts/run_real_benchmarks.sh phase0    # validation only
#   ./scripts/run_real_benchmarks.sh phase1    # cheap models
#   ./scripts/run_real_benchmarks.sh phase2    # expensive models
#   ./scripts/run_real_benchmarks.sh all       # phase1 + phase2 (skip phase0)
#
# Environment:
#   TOGETHER_API_KEY    — required for Together-hosted models
#   OPENROUTER_API_KEY  — required for OpenRouter-hosted models
#
# Tip: source .env.local first.

set -u

PHASE="${1:-all}"

CHEAP_MODELS=(qwen-2.5-7b mistral-nemo-12b llama-3.1-8b)
EXPENSIVE_MODELS=(deepseek-v3 gemini-2.5-flash gpt-oss-20b llama-3.3-70b)

DATASETS=(hotpotqa_real truthfulqa_real strategyqa_real travelplanner_real)

mkdir -p outputs/_logs

run_cell () {
    local dataset="$1"
    local model="$2"
    local cfg="configs/real/real_${dataset}__${model}.yaml"
    local logf="outputs/_logs/real_${dataset}__${model}.log"
    if [ ! -f "$cfg" ]; then
        echo "  [skip] config not found: $cfg"
        return 0
    fi
    if pgrep -fla "intro-specter run --config $cfg" | grep -v snapshot > /dev/null 2>&1; then
        echo "  [skip] already running: $cfg"
        return 0
    fi
    echo "  launching: $cfg"
    nohup .venv/bin/intro-specter run --config "$cfg" > "$logf" 2>&1 &
}

case "$PHASE" in
    phase0)
        echo "=== Phase 0: validation (Qwen 7B × HotpotQA-Real) ==="
        run_cell hotpotqa_real qwen-2.5-7b
        ;;
    phase1)
        echo "=== Phase 1: cheap models × all datasets ==="
        for ds in "${DATASETS[@]}"; do
            for m in "${CHEAP_MODELS[@]}"; do
                run_cell "$ds" "$m"
            done
        done
        ;;
    phase2)
        echo "=== Phase 2: expensive models × all datasets ==="
        for ds in "${DATASETS[@]}"; do
            for m in "${EXPENSIVE_MODELS[@]}"; do
                run_cell "$ds" "$m"
            done
        done
        ;;
    all)
        "$0" phase1
        sleep 2
        "$0" phase2
        ;;
    *)
        echo "Unknown phase: $PHASE"
        echo "Usage: $0 [phase0|phase1|phase2|all]"
        exit 1
        ;;
esac

echo
echo "Active intro-specter jobs:"
pgrep -fla 'intro-specter run' | grep -v snapshot || echo "  (none)"
