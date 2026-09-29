"""Merge GRPO LoRA adapters into SFT v9 for serving."""
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer


def merge(base_path: str, adapter_path: str, output_path: str):
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
    base = "outputs/gatedpo-sft-1.5b-v9/merged"
    merge(base, "outputs/gatedpo-grpo-1.5b-v10/checkpoint-10", "outputs/gatedpo-grpo-1.5b-v10-merged-ckpt10")
    merge(base, "outputs/gatedpo-grpo-1.5b-v10/checkpoint-20", "outputs/gatedpo-grpo-1.5b-v10-merged-ckpt20")
