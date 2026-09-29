"""Quick completion-diff check between SFT v9 and GRPO v10 on the same prompt."""
import json
import os
import random
import sys
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

from gatedpo.llm import _initial_prompt


def load_model_with_adapter(base_path: str, adapter_path: str):
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
    return model, tokenizer


def load_sft(base_path: str):
    tokenizer = AutoTokenizer.from_pretrained(base_path, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        base_path,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True,
        attn_implementation="sdpa",
    )
    return model, tokenizer


def generate(model, tokenizer, prompt_text: str, n: int = 3):
    messages = [{"role": "user", "content": prompt_text}]
    ids = tokenizer.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=True,
        return_dict=False,
    )
    input_ids = torch.tensor([ids], device=model.device)
    outputs = []
    for _ in range(n):
        with torch.no_grad():
            out = model.generate(
                input_ids,
                max_new_tokens=1024,
                do_sample=True,
                temperature=0.7,
                top_p=0.95,
                pad_token_id=tokenizer.pad_token_id,
            )[0]
        completion = out[len(ids) :]
        text = tokenizer.decode(completion, skip_special_tokens=True)
        outputs.append(text)
    return outputs


def main():
    base_path = "outputs/gatedpo-sft-1.5b-v9/merged"
    adapter_path = "outputs/gatedpo-grpo-1.5b-v10/checkpoint-20"

    # Pick one held-out and one train task.
    held_out = "benchmarks/held_out_suite.json"
    train_suite = "benchmarks/rl_pilot_suite_train.json"
    tasks = []
    for p in (held_out, train_suite):
        with open(p, encoding="utf-8") as f:
            suite = json.load(f)
        for c in suite["cases"][:1]:
            tasks.append((p, c["task_dir"]))

    print("Loading SFT v9...", flush=True)
    sft_model, tok = load_sft(base_path)
    print("Loading GRPO v10 (adapter over SFT v9)...", flush=True)
    grpo_model, _ = load_model_with_adapter(base_path, adapter_path)

    for suite, task_dir in tasks:
        print(f"\n=== {suite} : {task_dir} ===", flush=True)
        prompt = _initial_prompt(Path(task_dir))
        print("\n--- SFT v9 completions ---", flush=True)
        for i, c in enumerate(generate(sft_model, tok, prompt, n=2), 1):
            print(f"[{i}]\n{c[:800]}\n", flush=True)
        print("\n--- GRPO v10 completions ---", flush=True)
        for i, c in enumerate(generate(grpo_model, tok, prompt, n=2), 1):
            print(f"[{i}]\n{c[:800]}\n", flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
