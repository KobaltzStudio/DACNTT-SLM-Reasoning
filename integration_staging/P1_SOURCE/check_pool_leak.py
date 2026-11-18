#!/usr/bin/env python3
"""
Leak check for the official Task 6 pool (Instruction_task6.md section 9, step 1).

Checks that no problem in the pool belongs to, or overlaps with, D_dev or D_test:
  1. the split files still match the hashes in splits/split_manifest.json;
  2. every pool problem_id is in D_pool and in none of D_dev, D_test, near_duplicates;
  3. question and ground_truth of every pool row equal data/raw/gsm8k_train.jsonl for that id
     (so the id cannot point to one problem while the text is another);
  4. no pool question equals a D_dev / D_test question after lowercasing and keeping word characters;
  5. no pool question shares a word 13-gram with a D_dev / D_test question (the split rule,
     re-run on the pool with create_splits.find_near_duplicates).

Exit code 0 = PASS, 1 = FAIL. Report: reports/task6/leak_check.json

Usage (from experiments/week2September/manual/):
  python scripts/check_pool_leak.py
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from create_splits import find_near_duplicates  # noqa: E402
from student_common import MANUAL_DIR, read_jsonl, sha256_file, write_json  # noqa: E402

SPLITS = MANUAL_DIR / "splits"
RAW = MANUAL_DIR / "data" / "raw"
POOL = MANUAL_DIR / "trajectory" / "pool"


def ids(name):
    return set((SPLITS / name).read_text().split())


def norm(text):
    return " ".join(re.findall(r"\w+", text.lower()))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pool", type=Path, default=POOL / "pool_v1_teacher_raw.jsonl")
    ap.add_argument("--report", type=Path, default=MANUAL_DIR / "reports" / "task6" / "leak_check.json")
    ap.add_argument("--ngram", type=int, default=13)
    args = ap.parse_args()

    manifest = json.loads((SPLITS / "split_manifest.json").read_text())
    split_hashes = {k: sha256_file(MANUAL_DIR / f["path"]) == f["sha256"] for k, f in manifest["files"].items()}

    d_pool, d_dev, d_test = ids("d_pool_ids.txt"), ids("d_dev_ids.txt"), ids("d_test_ids.txt")
    near_dup = {r["problem_id"] for r in read_jsonl(SPLITS / "near_duplicates.jsonl")}
    train = {r["problem_id"]: r for r in read_jsonl(RAW / "gsm8k_train.jsonl")}
    test = {r["problem_id"]: r for r in read_jsonl(RAW / "gsm8k_test.jsonl")}

    rows = read_jsonl(args.pool)
    pool_q = {}
    text_mismatch = set()
    for r in rows:
        pid = r["problem_id"]
        src = train.get(pid)
        if src is None or r["question"] != src["question"] or str(r["ground_truth"]) != str(src["ground_truth"]):
            text_mismatch.add(pid)
        pool_q[pid] = r["question"]
    pids = set(pool_q)

    refs = {pid: train[pid]["question"] for pid in d_dev}
    refs.update({pid: test[pid]["question"] for pid in d_test})
    ref_norm = {norm(q): rid for rid, q in refs.items()}
    exact = {pid: ref_norm[norm(q)] for pid, q in pool_q.items() if norm(q) in ref_norm}
    ngram = find_near_duplicates(pool_q, refs, args.ngram)

    checks = {
        "split_files_match_manifest": all(split_hashes.values()),
        "not_in_d_pool": sorted(pids - d_pool),
        "in_d_dev": sorted(pids & d_dev),
        "in_d_test": sorted(pids & d_test),
        "in_near_duplicates": sorted(pids & near_dup),
        "text_differs_from_gsm8k_train": sorted(text_mismatch),
        "exact_question_match_dev_test": exact,
        f"shared_{args.ngram}gram_with_dev_test": ngram,
    }
    passed = checks["split_files_match_manifest"] and not any(v for k, v in checks.items()
                                                              if k != "split_files_match_manifest")

    rel = lambda p: str(Path(p).resolve().relative_to(MANUAL_DIR))  # noqa: E731
    write_json(args.report, {
        "pool": {"path": rel(args.pool), "sha256": sha256_file(args.pool),
                 "rows": len(rows), "problems": len(pids)},
        "references": {"d_dev": len(d_dev), "d_test": len(d_test), "d_pool": len(d_pool),
                       "near_duplicates": len(near_dup), "ngram": args.ngram},
        "split_file_hashes_ok": split_hashes,
        "checks": checks,
        "result": "PASS" if passed else "FAIL",
    })
    print(f"pool {len(rows)} rows, {len(pids)} problems | split hashes ok: {checks['split_files_match_manifest']}")
    for k, v in checks.items():
        if k != "split_files_match_manifest":
            print(f"  {k}: {len(v)}")
    print("PASS" if passed else "FAIL")
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
