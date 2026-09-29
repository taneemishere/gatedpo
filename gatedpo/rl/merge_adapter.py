"""Merge a GateDPO LoRA adapter checkpoint into a base model for serving.

Generic argv-driven version of merge_grpo_adapter.py — used to merge
intermediate DPO checkpoints (checkpoint-N) that the trainer's built-in
merge only covers for the final adapter.

Usage:
    python -m gatedpo.rl.merge_adapter \
        --base outputs/gatedpo-r1/base_placeholder \
        --adapter outputs/gatedpo-r1/checkpoint-20 \
        --out outputs/gatedpo-r1-merged-ckpt20
"""
from __future__ import annotations

import argparse

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer


def merge(base_path: str, adapter_path: str, output_path: str) -> None:
    print(f"Merging {adapter_path} into {base_path} -> {output_path}")
    tokenizer = AutoTokenizer.from_pretrained(base_path, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token
    base = AutoModelForCausalLM.from_pretrained(
        base_path,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True,
        attn_implementation="sdpa",
    )
    model = PeftModel.from_pretrained(base, adapter_path)
    merged = model.merge_and_unload()
    merged.save_pretrained(output_path)
    tokenizer.save_pretrained(output_path)
    print(f"Saved merged model to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge a LoRA adapter into a base checkpoint.")
    parser.add_argument("--base", required=True, help="base model the adapter was trained from")
    parser.add_argument("--adapter", required=True, help="adapter/checkpoint dir")
    parser.add_argument("--out", required=True, help="output dir for merged model")
    args = parser.parse_args()
    merge(args.base, args.adapter, args.out)
