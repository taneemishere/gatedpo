#!/usr/bin/env bash
# GateDPO - one iterative round: serve policy, generate pairs, train DPO, eval.
# Run from anywhere; the script cds to the repo root.
# Activate your Python environment (torch, trl, peft, vllm) before running.
#
# Round 0->1 usage (from an SFT checkpoint):
#   ROUND=1 POLICY=outputs/sft-1.5b-v9/merged bash scripts/run_round.sh
# Later rounds:
#   ROUND=2 POLICY=outputs/gatedpo-r1/merged bash scripts/run_round.sh
set -euo pipefail

cd "$(dirname "$0")/.."
export PYTHONPATH="$(pwd)${PYTHONPATH:+:$PYTHONPATH}"

ROUND=${ROUND:?set ROUND (e.g. 1)}
POLICY=${POLICY:?set POLICY (merged checkpoint path to start from)}
SUITE=${SUITE:-benchmarks/rl_pilot_suite_train.json}
OUT=${OUT:-outputs/gatedpo-r${ROUND}}
PAIRS=${PAIRS:-data/pairs_r${ROUND}.jsonl}
STATS=${STATS:-data/stats_r${ROUND}.json}
SERVED=${SERVED:-gatedpo_r${ROUND}}
N=${N:-12}
M=${M:-4}
STATES=${STATES:-8}
TEMP=${TEMP:-0.9}
STRATEGY=${STRATEGY:-all_edges}
BETA=${BETA:-0.1}
LR=${LR:-1e-5}
EPOCHS=${EPOCHS:-1}
EXTRA_PAIRGEN=${EXTRA_PAIRGEN:-}     # e.g. "--no-intra-gate --limit-tasks 3"
EXTRA_TRAIN=${EXTRA_TRAIN:-}       # e.g. "--loss-type sigmoid sft --loss-weights 1.0 0.1"
SKIP_EVAL=${SKIP_EVAL:-0}
PORT=${PORT:-8000}                 # vLLM endpoint port (8000 may be taken by other services)

LOG="logs/dpo/round${ROUND}.log"
mkdir -p logs/dpo logs/vllm data outputs .gatedpo_runs/pairgen
: > "$LOG"

echo "=== GateDPO round ${ROUND} ===" | tee -a "$LOG"
echo "policy:   $POLICY" | tee -a "$LOG"
echo "pairs:    $PAIRS" | tee -a "$LOG"
echo "out:      $OUT" | tee -a "$LOG"

serve_model() {
    local model_path=$1
    local name=$2
    screen -X -S vllm kill 2>/dev/null || true
    sleep 2
    screen -dmS vllm bash -c "vllm serve $model_path --served-model-name $name --port $PORT --max-model-len 32768 --gpu-memory-utilization 0.9 --dtype bfloat16 --trust-remote-code > 'logs/vllm/vllm_${name}.log' 2>&1"
    for i in {1..120}; do
        if python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT}/health')" 2>/dev/null; then
            echo "vllm ready ($name)" | tee -a "$LOG"
            return 0
        fi
        sleep 5
    done
    echo "vllm failed to start" | tee -a "$LOG"
    return 1
}

# ---- 1. serve current policy + generate pairs ----------------------------
serve_model "$POLICY" "$SERVED"
python3 -u -m gatedpo.rl.pairgen \
    --suite "$SUITE" \
    --base-url http://localhost:${PORT}/v1 \
    --model "$SERVED" \
    --num-samples "$N" \
    --repair-samples "$M" \
    --repair-states "$STATES" \
    --temperature "$TEMP" \
    --strategy "$STRATEGY" \
    --run-dir ".gatedpo_runs/pairgen/r${ROUND}" \
    --out "$PAIRS" \
    --stats-out "$STATS" \
    $EXTRA_PAIRGEN | tee -a "$LOG"

screen -X -S vllm kill 2>/dev/null || true
sleep 5   # let the GPU free before training

# ---- 2. DPO train (adapter + merged export) -------------------------------
python3 -u -m gatedpo.rl.dpo_trainer \
    --pairs "$PAIRS" \
    --model "$POLICY" \
    --output-dir "$OUT" \
    --beta "$BETA" \
    --learning-rate "$LR" \
    --epochs "$EPOCHS" \
    $EXTRA_TRAIN | tee -a "$LOG"

# ---- 3. held-out eval of the merged checkpoint ---------------------------
if [ "$SKIP_EVAL" != "1" ]; then
    serve_model "$OUT/merged" "gatedpo_r${ROUND}_eval"
    python3 -u -m gatedpo.rl.baseline \
        --suite benchmarks/held_out_suite.json \
        --run-dir ".gatedpo_runs/eval/held_out/gatedpo_r${ROUND}" \
        --llm-provider vllm \
        --llm-model "gatedpo_r${ROUND}_eval" \
        --llm-base-url http://localhost:${PORT}/v1 | tee -a "$LOG"
    screen -X -S vllm kill 2>/dev/null || true
fi

echo "=== round ${ROUND} complete: $OUT ===" | tee -a "$LOG"
