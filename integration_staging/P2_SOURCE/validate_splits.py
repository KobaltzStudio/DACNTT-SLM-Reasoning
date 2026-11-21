"""
Validate the frozen Task 5 splits independently of create_splits.py.

Checks:
  1. Split files exist, one problem_id per line, sorted, no duplicates.
  2. D_pool, D_dev, D_test are pairwise disjoint.
  3. Every id exists in its source (D_pool/D_dev in gsm8k_train, D_test in gsm8k_test).
  4. D_test == all of gsm8k_test; D_pool + D_dev + near_duplicates == all of gsm8k_train.
  5. batch_100 is in D_pool; supplement is in D_dev.
  6. Counts and sha256 match split_manifest.json (split files and source files).
  7. No D_pool question shares a word n-gram with any D_dev or D_test question.

Usage:
  python3 scripts/validate_splits.py [--split-dir splits]
"""

from pathlib import Path
import argparse
import json
import sys

from create_splits import (
    BASE,
    find_near_duplicates,
    load_ids,
    load_jsonl,
    load_questions,
    sha256_file,
)


def read_ids(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    return lines


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split-dir", type=Path, default=BASE / "splits")
    args = parser.parse_args()

    errors = []

    def check(condition, message):
        print(("[PASS] " if condition else "[FAIL] ") + message)
        if not condition:
            errors.append(message)

    manifest_path = args.split_dir / "split_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    def resolve(rel):
        p = Path(rel)
        return p if p.is_absolute() else BASE / p

    # 6a. Source hashes
    for name, info in manifest["sources"].items():
        check(sha256_file(resolve(info["path"])) == info["sha256"], f"source sha256 matches: {name}")

    # 6b. Split file hashes
    for name, info in manifest["files"].items():
        check(sha256_file(resolve(info["path"])) == info["sha256"], f"file sha256 matches: {name}")

    # 1. Format
    splits = {}
    for name in ("d_pool", "d_dev", "d_test"):
        ids = read_ids(resolve(manifest["files"][name]["path"]))
        check(ids == sorted(ids), f"{name}: sorted")
        check(len(ids) == len(set(ids)), f"{name}: no duplicate ids")
        check(all(ids), f"{name}: no empty lines")
        splits[name] = set(ids)

    pool, dev, test = splits["d_pool"], splits["d_dev"], splits["d_test"]

    # 2. Disjoint
    check(not (pool & dev), "d_pool and d_dev disjoint")
    check(not (pool & test), "d_pool and d_test disjoint")
    check(not (dev & test), "d_dev and d_test disjoint")

    # 3-4. Coverage of sources
    train = load_questions(resolve(manifest["sources"]["gsm8k_train"]["path"]))
    test_q = load_questions(resolve(manifest["sources"]["gsm8k_test"]["path"]))
    near_dups = {r["problem_id"] for r in load_jsonl(resolve(manifest["files"]["near_duplicates"]["path"]))}

    check(pool <= set(train) and dev <= set(train), "d_pool and d_dev ids exist in gsm8k_train")
    check(test == set(test_q), "d_test == all gsm8k_test")
    check(not (near_dups & (pool | dev)), "near_duplicates not in d_pool or d_dev")
    check(pool | dev | near_dups == set(train), "d_pool + d_dev + near_duplicates == all gsm8k_train")

    # 5. Required memberships
    batch = load_ids(resolve(manifest["sources"]["batch_100"]["path"]))
    supplement = load_ids(resolve(manifest["sources"]["supplement_selected"]["path"]))
    check(batch <= pool, f"batch_100 ({len(batch)}) in d_pool")
    check(supplement <= dev, f"supplement ({len(supplement)}) in d_dev")

    # 6c. Counts
    counts = manifest["counts"]
    check(counts["d_pool"] == len(pool), f"count d_pool = {len(pool)}")
    check(counts["d_dev"] == len(dev) == manifest["n_dev"], f"count d_dev = {len(dev)}")
    check(counts["d_test"] == len(test), f"count d_test = {len(test)}")
    check(counts["near_duplicates_removed"] == len(near_dups), f"count near_duplicates = {len(near_dups)}")

    # 7. Leakage
    references = {pid: train[pid] for pid in dev}
    references.update(test_q)
    leaked = find_near_duplicates({pid: train[pid] for pid in pool}, references, manifest["ngram"])
    check(not leaked, f"no d_pool question shares a {manifest['ngram']}-gram with d_dev/d_test ({len(leaked)} found)")

    print()
    if errors:
        print(f"[FAIL] {len(errors)} check(s) failed")
        sys.exit(1)
    print("[PASS] All split checks passed")


if __name__ == "__main__":
    main()
