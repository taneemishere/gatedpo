"""GateDPO trainer — Direct Preference Optimization on verifier-ordered pairs.

Trains a LoRA adapter on the preference pairs produced by
`gatedpo.rl.pairgen` (inter-gate / intra-gate / progress pairs ordered by
the frozen PatchProof gate pipeline), then merges the adapter into the base
checkpoint so the result can be served by vLLM for the next round and for
held-out evaluation.

Usage:
    python -m gatedpo.rl.dpo_trainer \
        --pairs data/pairs_r1.jsonl \
        --model outputs/gatedpo-sft-1.5b-v9/merged \
        --output-dir outputs/gatedpo-r1
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path

import torch
from datasets import Dataset
from peft import LoraConfig
from transformers import AutoModelForCausalLM, AutoTokenizer
from trl import DPOConfig, DPOTrainer

LORA_TARGETS = [
    "q_proj",
    "k_proj",
    "v_proj",
    "o_proj",
    "gate_proj",
    "up_proj",
    "down_proj",
]


def load_pairs(paths: list[Path], max_pairs: int = 0, seed: int = 0) -> Dataset:
    """Load pairgen JSONL rows into a conversational DPO dataset.

    TRL expects `prompt` (message list), `chosen` and `rejected` (single-turn
    message lists). pairgen emits exactly that; extra metadata columns are
    dropped here so the trainer sees a clean schema.
    """
    rows: list[dict] = []
    for path in paths:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            rows.append(
                {
                    "prompt": raw["prompt"],
                    "chosen": raw["chosen"],
                    "rejected": raw["rejected"],
                }
            )
    if max_pairs and len(rows) > max_pairs:
        import random

        random.Random(seed).shuffle(rows)
        rows = rows[:max_pairs]
    print(f"[dpo] loaded {len(rows)} preference pairs from {len(paths)} file(s)")
    return Dataset.from_list(rows)


def main() -> None:
    os.environ.setdefault("TRL_EXPERIMENTAL_SILENCE", "1")
    parser = argparse.ArgumentParser(description="GateDPO — DPO on verifier-ordered pairs.")
    parser.add_argument("--pairs", type=Path, nargs="+", required=True)
    parser.add_argument("--model", required=True, help="base/merged checkpoint to adapt")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--beta", type=float, default=0.1)
    parser.add_argument("--learning-rate", type=float, default=1e-5)
    parser.add_argument("--epochs", type=float, default=1.0)
    parser.add_argument("--lora-r", type=int, default=16)
    parser.add_argument("--lora-alpha", type=int, default=32)
    parser.add_argument("--max-length", type=int, default=16384)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--grad-accum", type=int, default=8)
    parser.add_argument("--save-steps", type=int, default=20)
    parser.add_argument(
        "--loss-type",
        nargs="+",
        default=["sigmoid"],
        help="TRL DPOConfig loss_type list, e.g. sigmoid, or 'sigmoid sft' for the "
        "MPO-style chosen-NLL regularizer (pair with --loss-weights).",
    )
    parser.add_argument(
        "--loss-weights",
        type=float,
        nargs="+",
        default=None,
        help="weights for combined --loss-type entries (equal weights if unset)",
    )
    parser.add_argument("--max-pairs", type=int, default=0, help="cap dataset size (0 = all)")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--no-merge", action="store_true", help="skip merged-checkpoint export")
    args = parser.parse_args()

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True,
        attn_implementation="sdpa",
    )

    dataset = load_pairs(args.pairs, max_pairs=args.max_pairs, seed=args.seed)

    peft_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        target_modules=LORA_TARGETS,
        lora_dropout=0.05,
        task_type="CAUSAL_LM",
    )

    config = DPOConfig(
        output_dir=str(output_dir),
        beta=args.beta,
        learning_rate=args.learning_rate,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        bf16=True,
        max_length=args.max_length,
        loss_type=args.loss_type,
        loss_weights=args.loss_weights,
        logging_steps=1,
        save_steps=args.save_steps,
        save_strategy="steps",
        report_to="none",
        seed=args.seed,
        dataset_num_proc=8,
    )

    trainer = DPOTrainer(
        model=model,
        args=config,
        train_dataset=dataset,
        processing_class=tokenizer,
        peft_config=peft_config,
    )
    trainer.train()

    adapter_dir = output_dir / "adapter"
    trainer.save_model(str(adapter_dir))
    tokenizer.save_pretrained(str(adapter_dir))
    print(f"[dpo] adapter saved to {adapter_dir}")

    if not args.no_merge:
        merged_dir = output_dir / "merged"
        shutil.rmtree(merged_dir, ignore_errors=True)
        merged = trainer.model.merge_and_unload()
        merged.save_pretrained(str(merged_dir))
        tokenizer.save_pretrained(str(merged_dir))
        print(f"[dpo] merged checkpoint saved to {merged_dir}")


if __name__ == "__main__":
    main()
