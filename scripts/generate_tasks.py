"""Generate synthetic PatchProof tasks using a served code model, then verify
that a gold patch promotes through the full gate pipeline.

Parameterized copy of gategrpo/scripts/generate_synthetic_tasks.py:
- model and endpoint via --model / --base-url (originals were hardcoded)
- prompt sharpened toward frontier failures: withheld regression edge cases
  beyond what visible tests exercise (targets visible_tests /
  release_gate_regressions gates — the stuck frontier)
"""
import argparse
import json
import shutil
import sys
import time
import uuid
from pathlib import Path

import requests
from difflib import unified_diff

from gatedpo.runner import run_task


def query_vllm(prompt, base_url, model, max_tokens=4096, temperature=0.7, retries=3):
    for _ in range(retries):
        try:
            r = requests.post(
                f"{base_url}/chat/completions",
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
                timeout=300,
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"vllm query error: {e}", file=sys.stderr)
            time.sleep(2)
    raise RuntimeError("vllm query failed after retries")


def extract_json(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text[: text.rfind("```")].strip()
        if text.startswith("json"):
            text = text.split("\n", 1)[1].strip()
    return json.loads(text)


def prompt_template(i, examples, target="regression"):
    if target == "visible":
        bug_clause = (
            "The bug should be in the MAIN code path — a subtle algorithmic error that the "
            "visible tests directly catch: a wrong aggregation, an off-by-one in the primary "
            "loop, an incorrect conditional in core logic, a wrong return transformation, or "
            "a misplaced data conversion. The buggy code must still run (no crashes); it just "
            "produces wrong results on ordinary inputs."
        )
        test_clause = (
            "Visible tests must catch the bug on ordinary inputs. Regression tests should "
            "check the same corrected behavior plus a few edge cases the visible tests miss."
        )
    else:
        bug_clause = (
            "The bug should be subtle and non-trivial: a missing or incorrect helper function, "
            "a wrong conditional, a type mismatch, a boundary error, an incorrect loop, or a "
            "missing validation step. Do not use trivial mistakes like a single wrong keyword, "
            "a missing import on an empty function, or \"return True instead of False\"."
        )
        test_clause = (
            "IMPORTANT: include regression tests that exercise edge cases and spec rules NOT "
            "covered by the visible tests (boundary values, empty inputs, unusual but valid "
            "inputs, required validation errors). A fix that only passes the visible tests "
            "should plausibly still fail the regression tests."
        )
    prompt = """Create a realistic Python code-repair task (task {i}).
Avoid duplicating these existing themes:
{examples}

The task must involve a small but realistic multi-file Python project (2-4 files under a src/ package and tests/).
{bug_clause}
Do not use trivial mistakes like a single wrong keyword or a missing import on an empty function.

{test_clause}

The project should look like a real, if small, library or service. Use descriptive variable and function names.
Include at least one visible test file and at least one regression/promotion test file.

Return ONLY a JSON object with these keys:
- name: a short kebab-case name like "retry_handler" or "ledger_balancer"
- instructions: one paragraph describing the bug and the desired behavior
- repo_files: list of {{"path": "src/module.py", "content": "..."}} for the buggy multi-file repo
- fixed_repo_files: same paths with the correct, fixed content
- visible_tests: list of {{"path": "tests/visible/test_xxx.py", "content": "..."}}
- regression_tests: list of {{"path": "tests/regression/test_xxx.py", "content": "..."}}
Tests must pass after fixed_repo_files are used and fail with repo_files. Output raw JSON only, no markdown, no commentary."""
    return prompt.format(
        i=i, examples=examples, bug_clause=bug_clause, test_clause=test_clause
    )


def write_repo_files(repo_dir, files):
    for f in files:
        p = repo_dir / f.get("path")
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f.get("content", ""), encoding="utf-8")


def make_patch(repo_files, fixed_files):
    lines = []
    for old, new in zip(repo_files, fixed_files):
        old_lines = old.get("content", "").splitlines(keepends=True)
        new_lines = new.get("content", "").splitlines(keepends=True)
        old_lines = [li + "\n" if not li.endswith("\n") else li for li in old_lines]
        new_lines = [li + "\n" if not li.endswith("\n") else li for li in new_lines]
        diff = list(unified_diff(old_lines, new_lines, fromfile="a/" + old.get("path"), tofile="b/" + new.get("path")))
        lines.extend(diff)
    return "".join(lines)


def verify_task(task_dir, patch_file):
    run_root = Path(".gatedpo_runs/synth_verify")
    run_root.mkdir(parents=True, exist_ok=True)
    run_dir = run_root / f"{task_dir.name}_{uuid.uuid4().hex[:8]}"
    try:
        return run_task(task_dir, run_dir, patch_file)
    except Exception as e:
        print(f"verify failed: {e}", file=sys.stderr)
        raise
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)


def generate_and_verify(i, seed_tasks, output_root, base_url, model, target):
    for attempt in range(3):
        print(f"Generating task {i} attempt {attempt+1}...")
        try:
            examples = "\n".join(f"- {t}" for t in seed_tasks[-25:])
            prompt = prompt_template(i, examples, target)
            raw = query_vllm(prompt, base_url, model, max_tokens=4096, temperature=0.7)
            data = extract_json(raw)
            name = data.get("name", f"task_{i}_{attempt}").replace(" ", "_").replace("-", "_")
            task_dir = output_root / f"synth3_{name}"
            task_dir.mkdir(parents=True, exist_ok=True)

            repo_dir = task_dir / "repo"
            write_repo_files(repo_dir, data.get("repo_files", []))
            for t in data.get("visible_tests", []):
                p = repo_dir / t.get("path")
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(t.get("content", ""), encoding="utf-8")
            for t in data.get("regression_tests", []):
                p = repo_dir / t.get("path")
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(t.get("content", ""), encoding="utf-8")

            (task_dir / "instructions.md").write_text(data.get("instructions", ""), encoding="utf-8")

            allowed_paths = [f.get("path") for f in data.get("repo_files", [])]
            task_json = {
                "id": name,
                "name": name,
                "workspace": "repo",
                "instructions": "instructions.md",
                "allowed_paths": allowed_paths,
                "visible_tests": [t.get("path") for t in data.get("visible_tests", [])],
                "regression_tests": [t.get("path") for t in data.get("regression_tests", [])],
                "default_patch": "candidate.patch",
                "candidate_patches": ["candidate.patch"],
            }
            (task_dir / "task.json").write_text(json.dumps(task_json), encoding="utf-8")

            patch_text = make_patch(data.get("repo_files", []), data.get("fixed_repo_files", []))
            patch_file = task_dir / "candidate.patch"
            patch_file.write_text(patch_text, encoding="utf-8")

            (task_dir / "data.json").write_text(json.dumps(data, indent=2), encoding="utf-8")

            result = verify_task(task_dir, patch_file)
            print(f"Verify status: {result.status}")
            for g in result.gates:
                print(f"  gate {g.name}: {g.passed}")
            if result.status == "promoted":
                print(f"Accepted {task_dir}")
                seed_tasks.append(name)
                return True
            else:
                print(f"Rejected {task_dir}")
        except Exception as e:
            print(f"attempt {attempt+1} exception: {e}", file=sys.stderr)
    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument("--output", type=Path, default=Path("tasks_frontier"))
    parser.add_argument("--base-url", default="http://localhost:8000/v1")
    parser.add_argument("--model", default="Qwen/Qwen2.5-Coder-7B-Instruct")
    parser.add_argument(
        "--avoid-dirs",
        type=Path,
        nargs="*",
        default=[],
        help="task dirs whose ids/names should be listed as themes to avoid "
        "(prevents regenerating duplicates of the existing suite)",
    )
    parser.add_argument(
        "--target",
        choices=["regression", "visible"],
        default="regression",
        help="bug style: 'regression' = edge-case/hidden-rule bugs (release-gate "
        "frontier); 'visible' = main-path algorithmic bugs the visible tests "
        "directly catch (visible_tests frontier)",
    )
    args = parser.parse_args()

    output_root = args.output
    output_root.mkdir(parents=True, exist_ok=True)
    seed_tasks = []
    for d in args.avoid_dirs:
        for tdir in sorted(d.iterdir()):
            if (tdir / "task.json").is_file():
                seed_tasks.append(tdir.name)
    n_avoid = len(seed_tasks)
    if seed_tasks:
        print(f"Seeding {n_avoid} existing task names to avoid")
    for i in range(args.count):
        generate_and_verify(i, seed_tasks, output_root, args.base_url, args.model, args.target)
    print(f"Done. Accepted {len(seed_tasks) - n_avoid} / {args.count} tasks in {output_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
