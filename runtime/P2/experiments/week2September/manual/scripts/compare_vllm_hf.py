#!/usr/bin/env python3
"""
Parity check vLLM vs HF on batch_100 (task6_decisions.md T6-5), before generating the new problems.

Both sides are re-scored with answer_utils (I1) and their lengths are re-tokenized with the Teacher
tokenizer, so the comparison does not depend on how each backend counts the stop token.

  HF   : trajectory/pool/batch_100_teacher_raw.jsonl (first pass, prompt v1, seeds per the rule;
         the 98 regenerated trajectories are NOT used)
  vLLM : rows with problem_index 0-99 of trajectory/pool/pool_v1_teacher_raw.jsonl

Known difference: the HF first pass used batch_100.jsonl question text, the vLLM run uses the
normalized gsm8k_train.jsonl text; 23 of the 100 questions differ in whitespace only.

Criteria fixed before the run:
  |valid rate (vLLM) - valid rate (HF)| <= 5 percentage points  AND
  |mean length of valid trajectories (vLLM) / (HF) - 1| <= 10%

Exit code 0 = PASS, 1 = FAIL. Report: reports/task6/parity_vllm_hf.json

Usage (from experiments/week2September/manual/):
  python scripts/compare_vllm_hf.py
"""
import argparse
import collections
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from answer_utils import evaluate_output  # noqa: E402
from student_common import MANUAL_DIR, load_config, load_tokenizer, read_jsonl, sha256_file, write_json  # noqa: E402

POOL = MANUAL_DIR / "trajectory" / "pool"
MAX_VALID_DIFF = 0.05
MAX_LEN_RATIO_DIFF = 0.10


def summarize(rows, tok):
    status = collections.Counter(evaluate_output(r["raw_generation"], r["ground_truth"]) for r in rows)
    valid = [r for r in rows if evaluate_output(r["raw_generation"], r["ground_truth"]) == "valid"]
    lengths = [len(tok(r["raw_generation"].strip(), add_special_tokens=False)["input_ids"]) for r in valid]
    problems = {r["problem_id"] for r in rows}
    return {
        "n": len(rows),
        "valid": status["valid"], "invalid_answer": status["invalid_answer"],
        "invalid_format": status["invalid_format"],
        "valid_rate": status["valid"] / len(rows),
        "problems": len(problems),
        "problems_without_valid": len(problems - {r["problem_id"] for r in valid}),
        "mean_valid_tokens": statistics.mean(lengths),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hf", type=Path, default=POOL / "batch_100_teacher_raw.jsonl")
    ap.add_argument("--vllm", type=Path, default=POOL / "pool_v1_teacher_raw.jsonl")
    ap.add_argument("--report", type=Path, default=MANUAL_DIR / "reports" / "task6" / "parity_vllm_hf.json")
    args = ap.parse_args()

    hf = read_jsonl(args.hf)
    vl = [r for r in read_jsonl(args.vllm) if r["metadata"]["problem_index"] < 100]
    hf_ids, vl_ids = {r["trajectory_id"] for r in hf}, {r["trajectory_id"] for r in vl}
    if len(hf) != 500 or len(vl) != 500 or hf_ids != vl_ids:
        raise SystemExit(f"need the same 500 batch_100 trajectory_ids on both sides (HF {len(hf)}, vLLM {len(vl)})")

    t = load_config()["teacher"]
    tok = load_tokenizer(t["model"], t["revision"])
    h, v = summarize(hf, tok), summarize(vl, tok)
    valid_diff = v["valid_rate"] - h["valid_rate"]
    len_ratio = v["mean_valid_tokens"] / h["mean_valid_tokens"] - 1
    passed = abs(valid_diff) <= MAX_VALID_DIFF and abs(len_ratio) <= MAX_LEN_RATIO_DIFF

    rel = lambda p: str(Path(p).resolve().relative_to(MANUAL_DIR))  # noqa: E731
    write_json(args.report, {
        "criteria": {"max_abs_valid_rate_diff": MAX_VALID_DIFF, "max_abs_mean_length_ratio_diff": MAX_LEN_RATIO_DIFF},
        "hf_first_pass": h, "vllm": v,
        "valid_rate_diff": valid_diff, "mean_length_ratio_diff": len_ratio,
        "result": "PASS" if passed else "FAIL",
        "inputs_sha256": {rel(args.hf): sha256_file(args.hf), rel(args.vllm): sha256_file(args.vllm)},
    })
    for name, s in (("HF  ", h), ("vLLM", v)):
        print(f"{name} valid {s['valid']}/{s['n']} ({s['valid_rate']:.3f})  invalid_format {s['invalid_format']}  "
              f"invalid_answer {s['invalid_answer']}  no-valid problems {s['problems_without_valid']}  "
              f"mean valid tokens {s['mean_valid_tokens']:.1f}")
    print(f"valid rate diff {valid_diff:+.3f} (limit ±{MAX_VALID_DIFF}), "
          f"length ratio diff {len_ratio:+.3f} (limit ±{MAX_LEN_RATIO_DIFF}) -> {'PASS' if passed else 'FAIL'}")
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
