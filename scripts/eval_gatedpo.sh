#!/usr/bin/env bash
# GateDPO - held-out eval of any merged checkpoint.
# Activate your Python environment (vllm + the gatedpo harness) before running.
#
# Usage:
#   MODEL=outputs/gatedpo-r1/merged TAG=gatedpo_r1 bash scripts/eval_gatedpo.sh
#   MODEL=outputs/gatedpo-r1-merged-ckpt20 TAG=gatedpo_r1_ckpt20 bash scripts/eval_gatedpo.sh
set -euo pipefail

cd "$(dirname "$0")/.."
export PYTHONPATH="$(pwd)${PYTHONPATH:+:$PYTHONPATH}"

MODEL=${MODEL:?set MODEL (merged checkpoint path)}
TAG=${TAG:?set TAG (eval artifact name, e.g. gatedpo_r1)}
PORT=${PORT:-8000}
SUITE=${SUITE:-benchmarks/held_out_suite.json}
RUNDIR=${RUNDIR:-.gatedpo_runs/eval/held_out/${TAG}}

LOG="logs/eval/${TAG}.log"
mkdir -p logs/eval logs/vllm
: > "$LOG"

echo "Evaluating $MODEL as $TAG on $SUITE" | tee -a "$LOG"

screen -X -S vllm kill 2>/dev/null || true
sleep 2
screen -dmS vllm bash -c "vllm serve $MODEL --served-model-name $TAG --port $PORT --max-model-len 32768 --gpu-memory-utilization 0.9 --dtype bfloat16 --trust-remote-code > 'logs/vllm/vllm_${TAG}.log' 2>&1"

for i in {1..120}; do
    if python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT}/health')" 2>/dev/null; then
        echo "vllm ready" | tee -a "$LOG"
        break
    fi
    sleep 5
done

python3 -u -m gatedpo.rl.baseline \
    --suite "$SUITE" \
    --run-dir "$RUNDIR" \
    --llm-provider vllm \
    --llm-model "$TAG" \
    --llm-base-url http://localhost:${PORT}/v1 | tee -a "$LOG"

screen -X -S vllm kill 2>/dev/null || true
sleep 2
echo "Eval complete: $RUNDIR" | tee -a "$LOG"
