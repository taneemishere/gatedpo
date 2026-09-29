"""GateDPO pair generation — verifier-ordered preference pairs.

Samples N first-turn repair candidates per task from the current policy
(served via vLLM's OpenAI-compatible endpoint), runs each through the frozen
PatchProof hard-gate verifier, orders them by verification depth, and emits
DPO preference pairs plus a per-round gate-type histogram — the
failure-frontier signal for the iterative loop.

Pair types
----------
A. inter_gate : a candidate that dies at a deeper gate is preferred over one
   that dies at a shallower gate (promoted is deepest).
B. intra_gate : two candidates die at the *same* terminal gate; the one with
   weaker failure evidence (e.g. fewer failing tests) is preferred.
C. progress   : on the evidence-conditioned repair context
   (initial prompt + turn-1 attempt + evidence packet), a turn-2 completion
   that advances past its parent's depth is preferred over one that stalls.

Usage:
    python -m gatedpo.rl.pairgen \
        --suite benchmarks/rl_pilot_suite_train.json \
        --base-url http://localhost:8000/v1 --model gatedpo_r1 \
        --num-samples 12 --repair-samples 4 \
        --out data/pairs_r1.jsonl --stats-out data/stats_r1.json
"""
from __future__ import annotations

import argparse
import json
import random
import re
import shutil
import tempfile
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from gatedpo.critic import ROUTES
from gatedpo.evidence import build_evidence_packet, classify_failure
from gatedpo.llm import (
    _initial_prompt,
    _repair_prompt,
    _score_result,
    build_search_replace_patch,
    extract_unified_diff,
    parse_search_replace_blocks,
    OpenAICompatibleClient,
)
from gatedpo.models import CandidateRecord
from gatedpo.runner import run_task


# ---------------------------------------------------------------------------
# Verified candidates
# ---------------------------------------------------------------------------


def _strip_thinking(content: str) -> str:
    """Remove <think>...</think> blocks if present."""
    return re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()


def _extract_patch_text(content: str) -> str:
    """Pull a clean patch-ish string out of a raw completion."""
    content = _strip_thinking(content)
    if "diff --git" in content or "<<<<<<< SEARCH" in content:
        return content
    fenced = extract_unified_diff(content)
    if fenced:
        return fenced
    match = re.search(r"```(?:diff|patch)?\n(.*?)```", content, re.DOTALL)
    if match:
        return match.group(1).strip()
    return content


def _gate_depth(result) -> int:
    """Verification depth: number of gates passed before the first failure.

    A promoted candidate has depth == len(result.gates) and is deepest.
    """
    return sum(1 for gate in result.gates if gate.passed)


def _terminal_gate(result) -> str | None:
    """Name of the first failed gate, or None if promoted."""
    return classify_failure(result.gates)


def _intra_score(result) -> float:
    """Within-depth ordering signal (higher = less-bad failure evidence).

    Only populated for gates that expose a quantitative failure count; the
    pair builder only uses it when two candidates share depth AND terminal
    gate.
    """
    for gate in result.gates:
        if gate.passed:
            continue
        if gate.name == "release_gate_regressions":
            count = gate.details.get("failing_test_count")
            if isinstance(count, (int, float)):
                return -float(count)
        if gate.name == "visible_tests":
            stdout = str(gate.details.get("stdout", ""))
            return -float(stdout.count("FAILED"))
    return 0.0


@dataclass
class VerifiedCandidate:
    completion: str          # raw model completion (what DPO trains on)
    depth: int               # gates passed
    promoted: bool
    terminal_gate: str | None
    fingerprint: str | None
    intra_score: float
    status: str
    patch_file: str = ""
    result: Any = field(default=None, repr=False)


def _verify_completion(task_dir: Path, completion: str, run_root: Path, tag: str) -> VerifiedCandidate | None:
    """Convert a raw completion into a patch and run the full gate pipeline.

    Returns None on infrastructure errors (patch conversion or run_task
    raising) — a crashed verification is not evidence about the model, so the
    candidate is dropped rather than treated as a failure.
    """
    content = _strip_thinking(completion)
    run_dir = run_root / tag
    patch_file = run_dir / "candidate.patch"
    try:
        blocks = parse_search_replace_blocks(content)
        if blocks:
            srp = build_search_replace_patch(task_dir, blocks)
            effective_patch = srp.patch_text if srp.all_blocks_matched else _extract_patch_text(content)
        else:
            effective_patch = _extract_patch_text(content)
        if not effective_patch:
            effective_patch = content
        run_dir.mkdir(parents=True, exist_ok=True)
        patch_file.write_text(effective_patch, encoding="utf-8")
        result = run_task(task_dir, run_dir, patch_file)
    except Exception:
        return None
    fingerprint = next(
        (g.fingerprint for g in result.gates if not g.passed), None
    )
    return VerifiedCandidate(
        completion=content,
        depth=_gate_depth(result),
        promoted=result.passed,
        terminal_gate=_terminal_gate(result),
        fingerprint=fingerprint,
        intra_score=_intra_score(result),
        status=result.status,
        patch_file=str(patch_file),
        result=result,
    )


# ---------------------------------------------------------------------------
# Pair construction
# ---------------------------------------------------------------------------


def _strictly_better(a: VerifiedCandidate, b: VerifiedCandidate, intra_gate: bool) -> bool:
    if a.depth > b.depth:
        return True
    if (
        intra_gate
        and a.depth == b.depth
        and a.terminal_gate == b.terminal_gate
        and a.terminal_gate is not None
        and a.intra_score > b.intra_score
    ):
        return True
    return False


def _pair_kind(a: VerifiedCandidate, b: VerifiedCandidate) -> str:
    return "inter_gate" if a.depth > b.depth else "intra_gate"


def _dedup(cands: list[VerifiedCandidate]) -> list[VerifiedCandidate]:
    """Drop completions with identical normalized text (a 1.5B policy often
    emits near-identical samples; identical chosen/rejected text is noise)."""
    seen: dict[str, VerifiedCandidate] = {}
    for cand in cands:
        seen.setdefault(cand.completion.strip(), cand)
    return list(seen.values())


def _cap_pairs(
    pairs: list[tuple[VerifiedCandidate, VerifiedCandidate]],
    max_pairs: int,
    rng: random.Random,
) -> list[tuple[VerifiedCandidate, VerifiedCandidate]]:
    """Keep at most max_pairs, preferring promoted chosen-arms then the
    hardest (smallest-gap) negatives — G2D-style informativeness."""
    if len(pairs) <= max_pairs:
        return pairs
    rng.shuffle(pairs)
    pairs.sort(
        key=lambda pair: (
            not pair[0].promoted,                      # promoted chosen first
            pair[0].depth - pair[1].depth,             # smaller gap = harder
            pair[1].fingerprint or "",                 # stable tiebreak
        )
    )
    return pairs[:max_pairs]


def build_turn1_pairs(
    cands: list[VerifiedCandidate],
    *,
    strategy: str,
    intra_gate: bool,
    max_pairs: int,
    rng: random.Random,
) -> list[tuple[VerifiedCandidate, VerifiedCandidate, str]]:
    """Ordered pairs among first-turn candidates of one task."""
    cands = _dedup(cands)
    if len(cands) < 2:
        return []
    raw: list[tuple[VerifiedCandidate, VerifiedCandidate]] = []
    if strategy == "all_edges":
        for a in cands:
            for b in cands:
                if _strictly_better(a, b, intra_gate):
                    raw.append((a, b))
    elif strategy == "adjacent":
        # Hard negatives only: candidates from consecutive depth levels.
        depths = sorted({c.depth for c in cands}, reverse=True)
        for upper, lower in zip(depths, depths[1:]):
            top = [c for c in cands if c.depth == upper]
            bot = [c for c in cands if c.depth == lower]
            raw.extend((a, b) for a in top for b in bot)
    elif strategy == "max_margin":
        deepest = max(c.depth for c in cands)
        shallowest = min(c.depth for c in cands)
        if deepest > shallowest:
            top = [c for c in cands if c.depth == deepest]
            bot = [c for c in cands if c.depth == shallowest]
            raw.extend((a, b) for a in top for b in bot)
    else:
        raise ValueError(f"unknown strategy: {strategy}")
    kept = _cap_pairs(raw, max_pairs, rng)
    return [(a, b, _pair_kind(a, b)) for a, b in kept]


def build_progress_pairs(
    parent: VerifiedCandidate,
    turn2: list[VerifiedCandidate],
    *,
    max_pairs: int,
    rng: random.Random,
) -> list[tuple[VerifiedCandidate, VerifiedCandidate, str]]:
    """Pairs on the repair context: advancing turn-2 ≻ stalled turn-2."""
    turn2 = _dedup(turn2)
    advancing = [c for c in turn2 if c.promoted or c.depth > parent.depth]
    stalling = [c for c in turn2 if not (c.promoted or c.depth > parent.depth)]
    raw = [(a, b) for a in advancing for b in stalling]
    kept = _cap_pairs(raw, max_pairs, rng)
    return [(a, b, "progress") for a, b in kept]


# ---------------------------------------------------------------------------
# Rollout
# ---------------------------------------------------------------------------


def _sample_n(client: OpenAICompatibleClient, messages: list[dict[str, Any]], n: int, workers: int) -> list[str]:
    """N independent samples via the OpenAI-compatible endpoint."""
    with ThreadPoolExecutor(max_workers=max(1, min(workers, n))) as pool:
        responses = list(pool.map(client.chat, [messages] * n))
    return [str(getattr(r, "content", "") or "") for r in responses]


def _make_record(candidate: VerifiedCandidate, tag: str, route: str) -> CandidateRecord:
    result = candidate.result
    return CandidateRecord(
        candidate_id=tag,
        patch_file=candidate.patch_file,
        status=result.status,
        route=route,
        failure_type=classify_failure(result.gates),
        score=_score_result(result.status, classify_failure(result.gates)),
        gates=tuple({"name": g.name, "passed": g.passed} for g in result.gates),
        evidence=build_evidence_packet(result.gates),
    )


def _process_task(
    case: dict[str, Any],
    task_dir: Path,
    args: argparse.Namespace,
    client: OpenAICompatibleClient,
    run_root: Path,
    rng: random.Random,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Generate + verify candidates for one task; emit pairs and stats."""
    task_id = str(case.get("id") or task_dir.name)
    initial = _initial_prompt(task_dir)
    t1_messages = [{"role": "user", "content": initial}]

    # ---- turn 1: sample + verify -----------------------------------------
    completions = _sample_n(client, t1_messages, args.num_samples, args.workers)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        t1 = [
            cand
            for cand in pool.map(
                lambda i_c: _verify_completion(task_dir, i_c[1], run_root, f"{task_id}_t1_{i_c[0]:03d}"),
                enumerate(completions),
            )
            if cand is not None
        ]

    pairs: list[dict[str, Any]] = []

    def _row(prompt_msgs, chosen, rejected, kind):
        return {
            "prompt": prompt_msgs,
            "chosen": [{"role": "assistant", "content": chosen}],
            "rejected": [{"role": "assistant", "content": rejected}],
            "pair_type": kind,
            "task_id": task_id,
        }

    # ---- type A/B pairs ---------------------------------------------------
    for chosen, rejected, kind in build_turn1_pairs(
        t1,
        strategy=args.strategy,
        intra_gate=args.intra_gate,
        max_pairs=args.max_pairs_per_task,
        rng=rng,
    ):
        row = _row(t1_messages, chosen.completion, rejected.completion, kind)
        row["chosen_depth"], row["rejected_depth"] = chosen.depth, rejected.depth
        row["rejected_gate"] = rejected.terminal_gate
        pairs.append(row)

    # ---- type C pairs: evidence-conditioned second turn -------------------
    progress_states = 0
    if args.progress_pairs:
        parents = [c for c in t1 if not c.promoted]
        # Prefer the deepest non-promoted states — the current frontier.
        parents.sort(key=lambda c: (-c.depth, c.intra_score))
        parents = parents[: args.repair_states]
        progress_states = len(parents)
        for state_idx, parent in enumerate(parents):
            evidence = build_evidence_packet(parent.result.gates)
            gate = evidence.gate if evidence else (parent.terminal_gate or "")
            route = ROUTES.get(gate, "general_repair")
            record = _make_record(parent, f"{task_id}_t1_parent", route)
            repair_text = _repair_prompt(task_dir, route, parent.completion, evidence, [record])
            t2_messages = [
                {"role": "user", "content": initial},
                {"role": "assistant", "content": parent.completion},
                {"role": "user", "content": repair_text},
            ]
            t2_completions = _sample_n(client, t2_messages, args.repair_samples, args.workers)
            tag_root = f"{task_id}_t2_{state_idx:03d}"
            with ThreadPoolExecutor(max_workers=args.workers) as pool:
                t2 = [
                    cand
                    for cand in pool.map(
                        lambda i_c: _verify_completion(task_dir, i_c[1], run_root, f"{tag_root}_{i_c[0]:02d}"),
                        enumerate(t2_completions),
                    )
                    if cand is not None
                ]
            for chosen, rejected, kind in build_progress_pairs(
                parent, t2, max_pairs=args.max_progress_pairs, rng=rng
            ):
                row = _row(t2_messages, chosen.completion, rejected.completion, kind)
                row["parent_depth"], row["chosen_depth"], row["rejected_depth"] = (
                    parent.depth, chosen.depth, rejected.depth,
                )
                row["rejected_gate"] = rejected.terminal_gate
                pairs.append(row)

    stats = {
        "task_id": task_id,
        "turn1_terminal_hist": dict(
            Counter(c.terminal_gate or "promoted" for c in t1)
        ),
        "turn1_promoted": sum(1 for c in t1 if c.promoted),
        "turn1_samples": len(completions),
        "turn1_verified": len(t1),
        "progress_states": progress_states,
        "pairs": len(pairs),
    }
    return pairs, stats


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def _resolve_task_dir(suite_path: Path, task_dir: str) -> Path:
    path = Path(task_dir)
    if path.is_absolute():
        return path
    return suite_path.resolve().parent.parent / path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate verifier-ordered DPO preference pairs for GateDPO.",
    )
    parser.add_argument("--suite", type=Path, required=True)
    parser.add_argument("--base-url", default="http://localhost:8000/v1")
    parser.add_argument("--model", required=True, help="served-model-name on the vLLM endpoint")
    parser.add_argument("--api-key", default=None)
    parser.add_argument("--num-samples", type=int, default=12, help="turn-1 candidates per task")
    parser.add_argument("--repair-samples", type=int, default=4, help="turn-2 candidates per repair state")
    parser.add_argument("--repair-states", type=int, default=8, help="max failing turn-1 states expanded per task")
    parser.add_argument("--temperature", type=float, default=0.9)
    parser.add_argument("--strategy", choices=["all_edges", "adjacent", "max_margin"], default="all_edges")
    parser.add_argument("--intra-gate", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--progress-pairs", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--max-pairs-per-task", type=int, default=12)
    parser.add_argument("--max-progress-pairs", type=int, default=4, help="per repair state")
    parser.add_argument("--limit-tasks", type=int, default=0, help="smoke-test cap (0 = all)")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--run-dir", type=Path, default=None, help="verifier workspaces root")
    parser.add_argument("--keep-runs", action="store_true", help="keep verifier workspaces (debug)")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--stats-out", type=Path, default=None)
    args = parser.parse_args()

    suite = json.loads(args.suite.read_text(encoding="utf-8"))
    cases = suite["cases"][: args.limit_tasks] if args.limit_tasks else suite["cases"]
    client = OpenAICompatibleClient(
        base_url=args.base_url,
        model=args.model,
        api_key=args.api_key,
        temperature=args.temperature,
    )
    run_root = args.run_dir or Path(tempfile.mkdtemp(prefix="gatedpo_pairgen_"))
    run_root.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)

    all_pairs: list[dict[str, Any]] = []
    per_task: dict[str, Any] = {}
    global_terminal = Counter()
    rejected_arm_hist = Counter()
    chosen_arm_hist = Counter()
    pair_type_hist = Counter()
    started = time.time()

    for case in cases:
        task_dir = _resolve_task_dir(args.suite, str(case["task_dir"]))
        pairs, stats = _process_task(case, task_dir, args, client, run_root, rng)
        all_pairs.extend(pairs)
        task_id = stats["task_id"]
        per_task[task_id] = stats
        for gate, n in stats["turn1_terminal_hist"].items():
            global_terminal[gate] += n
        for row in pairs:
            pair_type_hist[row["pair_type"]] += 1
            rejected_arm_hist[row.get("rejected_gate") or "promoted"] += 1
            chosen_arm_hist[str(row.get("chosen_depth"))] += 1
        print(
            f"[pairgen] {task_id}: t1_promoted={stats['turn1_promoted']}/"
            f"{stats['turn1_samples']} pairs={stats['pairs']}",
            flush=True,
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as handle:
        for row in all_pairs:
            handle.write(json.dumps(row) + "\n")

    summary = {
        "suite": str(args.suite),
        "model": args.model,
        "num_samples": args.num_samples,
        "repair_samples": args.repair_samples,
        "repair_states": args.repair_states,
        "strategy": args.strategy,
        "intra_gate": args.intra_gate,
        "progress_pairs": args.progress_pairs,
        "tasks": len(per_task),
        "pairs_total": len(all_pairs),
        "pair_type_hist": dict(pair_type_hist),
        # turn-1 failure distribution — where the policy currently dies
        "turn1_terminal_gate_hist": dict(global_terminal),
        # rejected-arm gate distribution — the failure-frontier signal
        "rejected_arm_gate_hist": dict(rejected_arm_hist),
        "per_task": per_task,
        "elapsed_seconds": round(time.time() - started, 1),
    }
    if args.stats_out:
        args.stats_out.parent.mkdir(parents=True, exist_ok=True)
        args.stats_out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "per_task"}, indent=2))

    if not args.keep_runs:
        shutil.rmtree(run_root, ignore_errors=True)


if __name__ == "__main__":
    main()
