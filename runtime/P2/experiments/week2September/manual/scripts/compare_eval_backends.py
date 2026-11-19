#!/usr/bin/env python3
"""
Compare two evaluations of the same checkpoint and split, e.g. vLLM against the HF run of the smoke test.

Greedy decoding should give the same output on both backends, but padding and batching can change a few of
them. This reports the agreement; it applies no pass threshold, because none was fixed in advance.

Usage (from experiments/week2September/manual/):
  python scripts/compare_eval_backends.py reports/task5/smoke_test/results/eval_S0_dev.jsonl runs/main/S0/eval_dev.jsonl
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from student_common import read_jsonl  # noqa: E402


def compare(a_rows, b_rows):
    a = {r["problem_id"]: r for r in a_rows}
    b = {r["problem_id"]: r for r in b_rows}
    ids = sorted(set(a) & set(b))
    if not ids:
        raise ValueError("no common problems")
    n = len(ids)
    return {
        "n_common": n,
        "n_only_a": len(set(a) - set(b)),
        "n_only_b": len(set(b) - set(a)),
        "identical_output_rate": sum(a[i]["raw_output"].strip() == b[i]["raw_output"].strip() for i in ids) / n,
        "same_status_rate": sum(a[i]["status"] == b[i]["status"] for i in ids) / n,
        "accuracy_a": sum(a[i]["status"] == "valid" for i in ids) / n,
        "accuracy_b": sum(b[i]["status"] == "valid" for i in ids) / n,
        "mean_output_tokens_a": sum(a[i]["n_output_tokens"] for i in ids) / n,
        "mean_output_tokens_b": sum(b[i]["n_output_tokens"] for i in ids) / n,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("a", type=Path)
    ap.add_argument("b", type=Path)
    args = ap.parse_args()
    print(json.dumps(compare(read_jsonl(args.a), read_jsonl(args.b)), indent=2))


if __name__ == "__main__":
    main()
