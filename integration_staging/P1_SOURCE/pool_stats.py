#!/usr/bin/env python3
"""
Descriptive statistics of the Task 6 pool (Instruction_task6.md section 9, step 3).

  - verification status overall, by source (batch_100 / new) and per problem;
  - the problems without any valid trajectory (T6-3) and why;
  - capability distribution of the verified pool (trajectory and problem level);
  - invalid_format breakdown by cause, and whether the final number would have been correct
    (last number of the whole output, or the last \\boxed{...}); diagnostic only, scoring stays I1.

Token lengths under the Student tokenizer are measured separately by measure_pool_tokens.py
(reports/task6/pool_token_stats.json).

Usage (from experiments/week2September/manual/):
  python scripts/pool_stats.py
"""
import argparse
import collections
import math
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from answer_utils import final_number  # noqa: E402
from student_common import MANUAL_DIR, read_jsonl, sha256_file, write_json  # noqa: E402

POOL = MANUAL_DIR / "trajectory" / "pool"
CAPS = ["addition", "subtraction", "multiplication", "division", "percentage", "fraction", "ratio"]
REASONING_RE = re.compile(r"REASONING\s*:", re.I)
ANSWER_RE = re.compile(r"ANSWER\s*:", re.I)
BOXED_RE = re.compile(r"\\boxed\{([^{}]*)\}")


def format_cause(r):
    """First matching cause, in this order."""
    text, meta = r["raw_generation"], r["metadata"]
    has_r, has_a = REASONING_RE.search(text), ANSWER_RE.search(text)
    if meta["finish_reason"] == "length":
        return "truncated_at_max_tokens"
    if has_r and has_a and has_a.start() < has_r.start():
        return "answer_before_reasoning"
    if has_r and has_a:
        return "empty_reasoning_or_answer"
    if has_a:
        return "missing_reasoning_marker"
    if re.search(r"answer\W{1,4}:", text, re.I):
        return "decorated_answer_marker"
    if BOXED_RE.search(text):
        return "boxed_only"
    return "no_answer_marker"


def lenient_correct(r):
    boxed = BOXED_RE.findall(r["raw_generation"])
    cand = final_number(boxed[-1]) if boxed else final_number(r["raw_generation"])
    return cand is not None and cand == final_number(r["ground_truth"])


def two_proportion_p(x1, n1, x2, n2):
    p = (x1 + x2) / (n1 + n2)
    z = (x1 / n1 - x2 / n2) / math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    return 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw", type=Path, default=POOL / "pool_v1_teacher_raw.jsonl")
    ap.add_argument("--verified", type=Path, default=POOL / "pool_v1_verified.jsonl")
    ap.add_argument("--hf-batch100", type=Path, default=POOL / "batch_100_teacher_raw.jsonl")
    ap.add_argument("--out", type=Path, default=MANUAL_DIR / "reports" / "task6" / "pool_stats.json")
    args = ap.parse_args()

    raw, verified = read_jsonl(args.raw), read_jsonl(args.verified)
    status = lambda r: r["metadata"]["verification_status"]  # noqa: E731

    # --- status
    by_source = collections.defaultdict(collections.Counter)
    for r in raw:
        by_source[r["metadata"]["source"]][status(r)] += 1
    per_problem = collections.defaultdict(list)
    for r in raw:
        per_problem[r["problem_id"]].append(r)
    n_valid = {p: sum(status(r) == "valid" for r in rs) for p, rs in per_problem.items()}

    # --- problems without a valid trajectory (T6-3)
    no_valid = sorted(p for p, n in n_valid.items() if n == 0)
    excluded = []
    for p in no_valid:
        rs = per_problem[p]
        excluded.append({
            "problem_id": p,
            "source": rs[0]["metadata"]["source"],
            "statuses": dict(collections.Counter(status(r) for r in rs)),
            "lenient_correct": sum(lenient_correct(r) for r in rs),
            "mean_teacher_tokens": round(statistics.mean(r["metadata"]["token_length"] for r in rs), 1),
        })
    excl_summary = {
        "n": len(no_valid),
        "by_source": dict(collections.Counter(e["source"] for e in excluded)),
        "all_5_invalid_answer": sum(e["statuses"].get("invalid_answer", 0) == 5 for e in excluded),
        "with_at_least_one_invalid_format": sum("invalid_format" in e["statuses"] for e in excluded),
        "with_lenient_correct_trajectory": sum(e["lenient_correct"] > 0 for e in excluded),
        "mean_teacher_tokens_excluded": round(statistics.mean(e["mean_teacher_tokens"] for e in excluded), 1),
        "mean_teacher_tokens_all": round(statistics.mean(r["metadata"]["token_length"] for r in raw), 1),
    }

    # --- capabilities of the verified pool
    n = len(verified)
    traj_caps = collections.Counter(c for r in verified for c in r["capabilities"])
    prob_caps = collections.defaultdict(set)
    for r in verified:
        prob_caps[r["problem_id"]].update(r["capabilities"])
    prob_counts = collections.Counter(c for s in prob_caps.values() for c in s)
    combos = collections.Counter("+".join(sorted(r["capabilities"], key=CAPS.index)) for r in verified)
    capabilities = {
        "trajectory_level": {c: {"n": traj_caps[c], "share": round(traj_caps[c] / n, 4)} for c in CAPS},
        "problem_level_any_trajectory": {c: {"n": prob_counts[c], "share": round(prob_counts[c] / len(prob_caps), 4)}
                                         for c in CAPS},
        "capabilities_per_trajectory": dict(sorted(collections.Counter(len(r["capabilities"]) for r in verified).items())),
        "top_combinations": combos.most_common(10),
        "problems_where_trajectories_disagree": sum(
            len({tuple(sorted(r["capabilities"])) for r in verified if r["problem_id"] == p}) > 1 for p in prob_caps),
    }

    # --- invalid_format
    fmt = [r for r in raw if status(r) == "invalid_format"]
    causes = collections.defaultdict(list)
    for r in fmt:
        causes[format_cause(r)].append(r)
    hf = read_jsonl(args.hf_batch100) if args.hf_batch100.exists() else []
    hf_fmt = sum(r["metadata"]["verification_status"] == "invalid_format" for r in hf)
    b100, new = by_source["batch_100"], by_source["new"]
    nb, nn = sum(b100.values()), sum(new.values())
    fmt_problems = collections.Counter(r["problem_id"] for r in fmt)
    invalid_format = {
        "n": len(fmt), "share": round(len(fmt) / len(raw), 4),
        "by_cause": {k: {"n": len(v), "lenient_correct": sum(map(lenient_correct, v))}
                     for k, v in sorted(causes.items(), key=lambda kv: -len(kv[1]))},
        "lenient_correct_total": sum(map(lenient_correct, fmt)),
        "backend_check_batch_100": {"hf_first_pass": hf_fmt, "vllm": b100["invalid_format"], "n": nb},
        "batch_100_vs_new": {"batch_100": [b100["invalid_format"], nb], "new": [new["invalid_format"], nn],
                             "two_proportion_p": round(two_proportion_p(b100["invalid_format"], nb,
                                                                       new["invalid_format"], nn), 3)},
        "problems_with_any": len(fmt_problems),
        "trajectories_per_problem": dict(sorted(collections.Counter(fmt_problems.values()).items())),
        "finish_reason_length_total": sum(r["metadata"]["finish_reason"] == "length" for r in raw),
        "finish_reason_length_by_status": dict(collections.Counter(
            status(r) for r in raw if r["metadata"]["finish_reason"] == "length")),
        "examples": {k: [r["trajectory_id"] for r in v[:3]] for k, v in causes.items()},
    }

    rel = lambda p: str(Path(p).resolve().relative_to(MANUAL_DIR))  # noqa: E731
    write_json(args.out, {
        "inputs": {rel(p): sha256_file(p) for p in (args.raw, args.verified)},
        "status": {
            "overall": dict(collections.Counter(map(status, raw))),
            "by_source": {k: dict(v) for k, v in by_source.items()},
            "valid_per_problem": dict(sorted(collections.Counter(n_valid.values()).items())),
        },
        "excluded_problems": {"summary": excl_summary, "problems": excluded},
        "capabilities_verified": capabilities,
        "invalid_format": invalid_format,
    })
    print(f"written {rel(args.out)}")


if __name__ == "__main__":
    main()
