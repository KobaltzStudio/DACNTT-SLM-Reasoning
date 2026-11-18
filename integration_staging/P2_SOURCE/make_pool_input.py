#!/usr/bin/env python3
"""
Build the canonical input file of the official Task 6 pool (task6_decisions.md T6-1, T6-2).

  1. Candidates = D_pool minus the 100 batch_100 problems, sorted by problem_id, then shuffled once
     with random.Random(POOL_SAMPLE_SEED). The full order is saved; it is the source of truth
     (the shuffle algorithm may differ across Python versions, the saved list does not).
  2. pool_v1_input.jsonl = batch_100 in its original order (problem_index 0-99), then the first
     --n-new problems of the shuffled order (problem_index 100, 101, ...). problem_index is the row
     order, so generation_seed = generation_seed_base + problem_index * K + k (config) is unchanged.
  3. Extra blocks (T6-1): rerun with a larger --n-new (1100, 1200, ...). The new file must keep the
     old file as an exact prefix, otherwise the script refuses to write.

Question text and ground truth come from data/raw/gsm8k_train.jsonl (the normalized copy also used
for D_dev), not from data/batch_100/batch_100.jsonl: 23 of its 100 questions differ in whitespace only.

Outputs (trajectory/pool/):
  pool_v1_candidate_order.txt      6,868 candidate problem_ids in shuffled order
  pool_v1_input.jsonl              problem_index, problem_id, source, question, ground_truth
  pool_v1_input_manifest.json      seeds, counts, input/output SHA-256, Python version

Usage (from experiments/week2September/manual/):
  python scripts/make_pool_input.py --n-new 1000
"""
import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from student_common import GSM8K_TRAIN, MANUAL_DIR, read_jsonl, sha256_file, write_json  # noqa: E402

POOL_SAMPLE_SEED = 20261021  # task6_decisions.md T6-1; distinct from split_seed and generation_seed_base
SPLITS = MANUAL_DIR / "splits"
BATCH_100 = MANUAL_DIR / "data" / "batch_100" / "batch_100.jsonl"
POOL_DIR = MANUAL_DIR / "trajectory" / "pool"
ORDER_PATH = POOL_DIR / "pool_v1_candidate_order.txt"
INPUT_PATH = POOL_DIR / "pool_v1_input.jsonl"
MANIFEST_PATH = POOL_DIR / "pool_v1_input_manifest.json"


def read_ids(path):
    return [x.strip() for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n-new", type=int, default=1000, help="new problems after batch_100 (blocks of 100)")
    args = ap.parse_args()
    if args.n_new < 1 or args.n_new % 100:
        raise SystemExit("--n-new must be a positive multiple of 100 (T6-1 blocks)")

    pool = read_ids(SPLITS / "d_pool_ids.txt")
    held_out = set(read_ids(SPLITS / "d_dev_ids.txt")) | set(read_ids(SPLITS / "d_test_ids.txt"))
    batch = [r["problem_id"] for r in read_jsonl(BATCH_100)]
    if len(batch) != 100 or len(set(batch)) != 100 or not set(batch) <= set(pool):
        raise SystemExit("batch_100 must be 100 distinct D_pool problems")
    if set(pool) & held_out:
        raise SystemExit("D_pool overlaps D_dev/D_test")

    candidates = sorted(set(pool) - set(batch))
    order = list(candidates)
    random.Random(POOL_SAMPLE_SEED).shuffle(order)
    if args.n_new > len(order):
        raise SystemExit(f"--n-new {args.n_new} exceeds {len(order)} candidates")

    train = {r["problem_id"]: r for r in read_jsonl(GSM8K_TRAIN)}
    chosen = [(pid, "batch_100") for pid in batch] + [(pid, "new") for pid in order[: args.n_new]]
    rows = []
    for index, (pid, source) in enumerate(chosen):
        r = train[pid]
        rows.append({"problem_index": index, "problem_id": pid, "source": source,
                     "question": r["question"], "ground_truth": r["ground_truth"]})

    text = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
    if INPUT_PATH.exists():
        old = INPUT_PATH.read_text(encoding="utf-8")
        if not text.startswith(old):
            raise SystemExit(f"{INPUT_PATH.name} exists and is not a prefix of the new file; refusing to overwrite")

    POOL_DIR.mkdir(parents=True, exist_ok=True)
    ORDER_PATH.write_text("\n".join(order) + "\n", encoding="utf-8")
    INPUT_PATH.write_text(text, encoding="utf-8")

    rel = lambda p: str(Path(p).relative_to(MANUAL_DIR))  # noqa: E731
    write_json(MANIFEST_PATH, {
        "purpose": "Task 6 official pool input (task6_decisions.md T6-1, T6-2)",
        "pool_sample_seed": POOL_SAMPLE_SEED,
        "shuffle_rule": "random.Random(pool_sample_seed).shuffle(sorted(D_pool - batch_100))",
        "index_rule": "batch_100 in batch_100.jsonl order = problem_index 0-99; new problems from index 100 "
                      "in candidate order; generation_seed = generation_seed_base + problem_index * K + k",
        "question_source": rel(GSM8K_TRAIN),
        "python": sys.version.split()[0],
        "n_candidates": len(order),
        "n_batch_100": len(batch),
        "n_new": args.n_new,
        "n_rows": len(rows),
        "inputs_sha256": {rel(p): sha256_file(p) for p in
                          [SPLITS / "d_pool_ids.txt", SPLITS / "d_dev_ids.txt", SPLITS / "d_test_ids.txt",
                           BATCH_100, GSM8K_TRAIN]},
        "outputs_sha256": {rel(ORDER_PATH): sha256_file(ORDER_PATH), rel(INPUT_PATH): sha256_file(INPUT_PATH)},
    })
    print(f"{len(rows)} rows ({len(batch)} batch_100 + {args.n_new} new) -> {rel(INPUT_PATH)}")
    print(f"candidate order ({len(order)}) -> {rel(ORDER_PATH)}; manifest -> {rel(MANIFEST_PATH)}")


if __name__ == "__main__":
    main()
