"""
Tests for scripts/answer_utils.py.

1. Unit cases (format, last number, Decimal canonicalization).
2. Reproduces stored verification_status of the recovered v2 pool (expected 480 valid / 20 invalid_answer).
3. Reports where the two existing verifiers disagree with the stored status.

Usage:
  python3 scripts/test_answer_utils.py [--pool trajectory/pool/batch_100_teacher_raw_recovered_v2.jsonl]
"""

from pathlib import Path
import argparse
import collections
import json
import re
import sys
from decimal import Decimal, InvalidOperation

from answer_utils import evaluate_output, final_number, split_response, verify_answer


BASE = Path(__file__).resolve().parents[1]
DEFAULT_POOL = BASE / "trajectory" / "pool" / "batch_100_teacher_raw_recovered_v2.jsonl"


# Copies of the two existing verifiers, for comparison only.
def generate_verify(answer, ground_truth):
    # scripts/generate_teacher_trajectories_batch.py:82-92
    def norm(value):
        value = str(value or "").replace(",", "").strip().lower()
        value = value.replace("$", "").replace("%", "")
        nums = re.findall(r"[-+]?\d+(?:\.\d+)?", value)
        return nums[-1] if nums else value
    if not answer:
        return "invalid_format"
    return "valid" if norm(answer) == norm(ground_truth) else "invalid_answer"


def regenerate_verify(answer, ground_truth):
    # scripts/regenerate_failed_trajectories_reviewed.py:87-97 (+ comparison at :200)
    def num(value):
        text = str(value or "").replace(",", "").replace("$", "").replace("%", "").strip()
        m = re.search(r"[-+]?\d+(?:\.\d+)?", text)
        if not m:
            return None
        try:
            return format(Decimal(m.group(0)).normalize(), "f")
        except InvalidOperation:
            return None
    if not answer:
        return "invalid_format"
    a = num(answer)
    return "valid" if a is not None and a == num(ground_truth) else "invalid_answer"


UNIT_CASES = [
    (final_number("Leigh had 16 seashells."), "16"),
    (final_number("36.00"), "36"),
    (final_number("$1,250.50"), "1250.5"),
    (final_number("16 x 60 = 960, total 228"), "228"),
    (final_number("no number"), None),
    (verify_answer("", "5"), "invalid_format"),
    (verify_answer("The answer is 5.", "5"), "valid"),
    (verify_answer("The answer is 6.", "5"), "invalid_answer"),
    (split_response("REASONING:\n1+1=2\n\nANSWER:\n2")[1:], ("2", "parsed")),
    (split_response("just 2")[2], "invalid_format"),
    (evaluate_output("REASONING:\nx\nANSWER:\nShe has 40 apples.", "40"), "valid"),
    (evaluate_output("She has 40 apples.", "40"), "invalid_format"),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pool", type=Path, default=DEFAULT_POOL)
    args = parser.parse_args()

    failures = 0
    for i, (got, expected) in enumerate(UNIT_CASES, start=1):
        if got != expected:
            failures += 1
            print(f"[FAIL] unit case {i}: got {got!r}, expected {expected!r}")
    print(f"[{'PASS' if not failures else 'FAIL'}] unit cases: {len(UNIT_CASES) - failures}/{len(UNIT_CASES)}")

    records = [json.loads(l) for l in args.pool.open(encoding="utf-8") if l.strip()]
    counts = collections.Counter()
    mismatch = {"answer_utils": [], "generate": [], "regenerate": []}

    for r in records:
        stored = r["metadata"]["verification_status"]
        a, g = r["answer"], r["ground_truth"]
        for name, fn in (("answer_utils", verify_answer), ("generate", generate_verify), ("regenerate", regenerate_verify)):
            if fn(a, g) != stored:
                mismatch[name].append(r["trajectory_id"])
        counts[verify_answer(a, g)] += 1

    print(f"[INFO] pool: {args.pool.name}, records: {len(records)}, answer_utils: {dict(counts)}")
    for name, ids in mismatch.items():
        print(f"[INFO] {name}: {len(ids)} mismatch(es) with stored status {ids}")

    if mismatch["answer_utils"]:
        failures += 1
        print("[FAIL] answer_utils does not reproduce stored verification_status")
    else:
        print("[PASS] answer_utils reproduces stored verification_status")

    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
