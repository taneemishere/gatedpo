# GateDPO

Verifier-ordered preference learning for code repair. GateDPO runs a deterministic hard-gate verifier on every candidate patch, orders candidates by how deep they survive in the gate chain, and uses that partial order to build DPO preference pairs; no learned reward model. Each round regenerates pairs from the current policy's own verifier-typed failures.

**Read the full write-up:** https://taneemishere.github.io/gatedpo

## Quick start

One full round: serve the policy in vLLM, generate pairs, train DPO, eval.

```bash
# round 1 from the SFT base checkpoint
ROUND=1 POLICY=outputs/sft-1.5b-v9/merged bash scripts/run_round.sh

# round 2 from round 1's merged checkpoint
ROUND=2 POLICY=outputs/gatedpo-r1/merged bash scripts/run_round.sh
```

Each round writes `data/pairs_rN.jsonl` + `data/stats_rN.json` and a merged checkpoint at `outputs/gatedpo-rN/`.

Evaluate any merged checkpoint on the held-out suite:

```bash
MODEL=outputs/gatedpo-r1/merged TAG=gatedpo_r1 bash scripts/eval_gatedpo.sh
```

Generate new verifier-typed tasks with a served code model (a task is only admitted if its gold patch promotes through every gate):

```bash
python3 scripts/generate_tasks.py --count 10 --output tasks_frontier \
  --base-url http://localhost:8000/v1 --model Qwen/Qwen2.5-Coder-32B-Instruct
```

Useful knobs (env): `N`, `M`, `STATES`, `TEMP`, `STRATEGY`, `BETA`, `LR`, `EPOCHS`, `EXTRA_PAIRGEN`, `EXTRA_TRAIN`, `SKIP_EVAL=1`.

Run tests:

```bash
python3 -m pytest -q tests
```

## Code layout

- `gatedpo/` : the verification harness, gates, and search controller
- `gatedpo/rl/` : pairgen (rollout + verify + pair construction), DPOTrainer, merge, baseline eval
- `benchmarks/` : task suites used for training and evaluation
- `tasks/` : held-out evaluation tasks
- `tasks_train_v2/` : training task corpus
- `held_out_new/` : additional out-of-distribution eval tasks
- `examples/` : bring-your-own-code example
- `tests/` : unit and integration tests
- `scripts/` : round runner, held-out eval, task generation
- `report/` : the write-up, figures, and project page

## What to watch

- `data/stats_rN.json` : `rejected_arm_gate_hist` per round is the failure-frontier migration signal.
- `logs/dpo/roundN.log` : watch `rewards/margins` and chosen-arm NLL; unanchored DPO degenerates into `patch_applies` failures.
- `.gatedpo_runs/eval/held_out/<tag>/` : per-episode eval artifacts.
