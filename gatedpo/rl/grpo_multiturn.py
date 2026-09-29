"""Multi-turn GRPO rollout for PatchProof.

Uses TRL GRPOTrainer's experimental rollout_func to collect a 2-turn repair
episode for each sampled first-turn completion. The first-turn completion is
what the model trains on; the reward is the best PatchProof verifier reward
seen across the two turns.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

import torch
from datasets import Dataset
from peft import LoraConfig
from transformers import AutoModelForCausalLM, AutoTokenizer
from trl import GRPOConfig, GRPOTrainer

from gatedpo.evidence import build_evidence_packet, classify_failure
from gatedpo.llm import (
    _initial_prompt,
    _repair_prompt,
    _score_result,
    build_search_replace_patch,
    extract_unified_diff,
    parse_search_replace_blocks,
)
from gatedpo.models import CandidateRecord
from gatedpo.rl.rewards import patchproof_reward, compute_format_reward
from gatedpo.runner import run_task


def _strip_thinking(content: str) -> str:
    """Remove <think>... blocks if present."""
    return re.sub(r"", "", content, flags=re.DOTALL).strip()


def _extract_patch_text(content: str) -> str:
    """Try to pull a clean patch out of the model response."""
    content = _strip_thinking(content)
    # If it looks like a unified diff, return as-is.
    if "diff --git" in content:
        return content
    # If it has Aider SEARCH/REPLACE blocks, return as-is.
    if "<<<<<<< SEARCH" in content:
        return content
    # Otherwise, look for a fenced patch.
    match = re.search(r"```(?:diff|patch)?\n(.*?)```", content, re.DOTALL)
    if match:
        return match.group(1).strip()
    return content


def _make_record(patch_file: Path, result, route: str) -> CandidateRecord:
    return CandidateRecord(
        candidate_id="grpo_001",
        patch_file=str(patch_file),
        status=result.status,
        route=route,
        failure_type=classify_failure(result.gates),
        score=_score_result(result.status, classify_failure(result.gates)),
        gates=tuple({"name": g.name, "passed": g.passed} for g in result.gates),
        evidence=build_evidence_packet(result.gates),
    )


def _tokenize_messages(tokenizer, messages, add_generation_prompt: bool = True) -> list[int]:
    return tokenizer.apply_chat_template(
        messages,
        add_generation_prompt=add_generation_prompt,
        tokenize=True,
        return_dict=False,
    )


def _run_one_turn(task_dir: Path, patch_text: str):
    # Convert Aider SEARCH/REPLACE blocks to a unified diff, or fall back to raw text.
    blocks = parse_search_replace_blocks(patch_text)
    if blocks:
        srp = build_search_replace_patch(task_dir, blocks)
        effective_patch = srp.patch_text if srp.all_blocks_matched else _extract_patch_text(patch_text)
    else:
        effective_patch = _extract_patch_text(patch_text)
    if not effective_patch:
        effective_patch = patch_text
    with tempfile.NamedTemporaryFile(mode="w", suffix=".patch", delete=False) as f:
        f.write(effective_patch)
        patch_file = Path(f.name)
    run_dir = Path(tempfile.mkdtemp(prefix="grpo_"))
    try:
        result = run_task(task_dir, run_dir, patch_file)
        reward = patchproof_reward(
            gates=result.gates,
            promoted=result.passed,
            completion_tokens=0,
            max_tokens=1,
        )
        return result, reward, patch_file
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


def episode_reward_func(
    prompts: list[list[dict[str, Any]]],
    completions: list[list[dict[str, Any]]],
    *,
    episode_reward: list[float],
    **kwargs,
) -> list[float]:
    return episode_reward


def format_reward(
    prompts: list[list[dict[str, Any]]],
    completions: list[list[dict[str, Any]]],
    *,
    task_dir: list[str],
    **kwargs,
) -> list[float]:
    rewards = []
    for comp, td in zip(completions, task_dir):
        text = comp[0]["content"]
        rewards.append(compute_format_reward(text, td))
    return rewards


def build_dataset(suite_path: Path, tokenizer):
    with suite_path.open(encoding="utf-8") as f:
        suite = json.load(f)
    rows = []
    for case in suite["cases"]:
        task_dir = Path(case["task_dir"])
        prompt_text = _initial_prompt(task_dir)
        rows.append(
            {
                "prompt": [
                    {
                        "role": "user",
                        "content": prompt_text,
                        "task_dir": str(task_dir),
                    }
                ],
                "task_dir": str(task_dir),
            }
        )
    return Dataset.from_list(rows)


def make_rollout_func(max_candidates: int = 2):
    def rollout_func(prompts: list[list[dict[str, Any]]], trainer) -> dict[str, Any]:
        tokenizer = trainer.processing_class
        task_dirs = []
        for p in prompts:
            task_dir = None
            for m in p:
                task_dir = m.get("task_dir") or task_dir
            task_dirs.append(Path(task_dir))

        # Tokenize initial prompts.
        prompt_ids = [_tokenize_messages(tokenizer, p) for p in prompts]
        images = None
        multimodal_fields = {}

        # First turn generation.
        completion_ids, _ = trainer._generate_single_turn(
            prompt_ids, images, multimodal_fields, has_tool_images=False
        )
        completion_texts = [
            tokenizer.decode(ids, skip_special_tokens=True) for ids in completion_ids
        ]

        # Run first turn verifier.
        rewards = []
        records = []
        patch_files = []
        for i, (task_dir, patch_text) in enumerate(zip(task_dirs, completion_texts)):
            result, reward, patch_file = _run_one_turn(task_dir, patch_text)
            rewards.append(reward)
            records.append(_make_record(patch_file, result, "initial_repair"))
            patch_files.append(patch_file)

        # Second turn for non-promoted attempts (up to max_candidates-1 more turns).
        if max_candidates > 1:
            # Build repair prompts and tokenize for the still-failing ones.
            repair_prompts = []
            repair_indices = []
            for i, (task_dir, record) in enumerate(zip(task_dirs, records)):
                if record.status == "promoted":
                    continue
                repair_text = _repair_prompt(
                    task_dir,
                    record.route,
                    completion_texts[i],
                    record.evidence,
                    [record],
                )
                messages = [
                    {"role": "user", "content": _initial_prompt(task_dir)},
                    {"role": "assistant", "content": completion_texts[i]},
                    {"role": "user", "content": repair_text},
                ]
                repair_prompts.append(messages)
                repair_indices.append(i)

            if repair_prompts:
                repair_prompt_ids = [
                    _tokenize_messages(tokenizer, m) for m in repair_prompts
                ]
                repair_completion_ids, _ = trainer._generate_single_turn(
                    repair_prompt_ids, images, multimodal_fields, has_tool_images=False
                )
                repair_texts = [
                    tokenizer.decode(ids, skip_special_tokens=True)
                    for ids in repair_completion_ids
                ]
                for j, i in enumerate(repair_indices):
                    task_dir = task_dirs[i]
                    result, reward, patch_file2 = _run_one_turn(task_dir, repair_texts[j])
                    # Episode reward is the sum of per-turn per-gate partial credit.
                    rewards[i] = rewards[i] + reward
                    patch_file2.unlink(missing_ok=True)

        for pf in patch_files:
            pf.unlink(missing_ok=True)

        # The required keys for a rollout_func return.
        return {
            "prompt_ids": prompt_ids,
            "completion_ids": completion_ids,
            "logprobs": None,
            "episode_reward": rewards,
            "task_dir": [str(td) for td in task_dirs],
        }

    return rollout_func


def main():
    os.environ["TRL_EXPERIMENTAL_SILENCE"] = "1"

    output_dir = Path("outputs/gatedpo-grpo-1.5b-v10b")
    shutil.rmtree(output_dir, ignore_errors=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    model_name = "outputs/gatedpo-sft-1.5b-v9/merged"
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True,
        attn_implementation="sdpa",
    )

    dataset = build_dataset(
        Path("benchmarks/rl_pilot_suite_train.json"),
        tokenizer,
    )

    peft_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=[
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
        lora_dropout=0.05,
        task_type="CAUSAL_LM",
    )

    grpo_args = GRPOConfig(
        output_dir=str(output_dir),
        learning_rate=5e-6,
        num_generations=4,
        num_train_epochs=1,
        max_completion_length=2048,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        bf16=True,
        temperature=0.7,
        top_p=0.95,
        use_vllm=False,
        logging_steps=1,
        save_steps=10,
        report_to="none",
        loss_type="dr_grpo",
        scale_rewards="batch",
        beta=0.05,
    )

    trainer = GRPOTrainer(
        model=model,
        processing_class=tokenizer,
        reward_funcs=[episode_reward_func],
        args=grpo_args,
        train_dataset=dataset,
        peft_config=peft_config,
        rollout_func=make_rollout_func(max_candidates=2),
    )

    trainer.train()
    trainer.save_model(str(output_dir))
    print(f"GRPO v10 (multi-turn) saved to {output_dir}")


if __name__ == "__main__":
    raise SystemExit(main())
