"""
Create the frozen problem-level splits for Task 5 (see task5_decisions.md, section B).

Rules:
  D_test = every problem in data/raw/gsm8k_test.jsonl (official GSM8K test).
  D_dev  = all supplement problems (data/raw/supplement_selected.jsonl)
           + a seeded random sample from the remaining GSM8K train problems
             (excluding batch_100 and supplement) up to --n-dev problems.
  D_pool = remaining GSM8K train problems, minus problems flagged as near-duplicates
           of any D_dev or D_test question (shared word 13-gram).
  batch_100 must end up in D_pool; the script fails if a batch_100 problem is flagged.

Outputs (in --out-dir, default splits/):
  d_pool_ids.txt, d_dev_ids.txt, d_test_ids.txt   one problem_id per line, sorted
  near_duplicates.jsonl                           problems removed from D_pool, with evidence
  split_manifest.json                             sources, seed, rules, counts, sha256

The script refuses to write into an existing --out-dir.
"""

from pathlib import Path
import argparse
import hashlib
import json
import random
import re
import sys


BASE = Path(__file__).resolve().parents[1]

TRAIN_FILE = BASE / "data" / "raw" / "gsm8k_train.jsonl"
TEST_FILE = BASE / "data" / "raw" / "gsm8k_test.jsonl"
BATCH_FILE = BASE / "data" / "batch_100" / "batch_100.jsonl"
SUPPLEMENT_FILE = BASE / "data" / "raw" / "supplement_selected.jsonl"

DEFAULT_SEED = 363636
DEFAULT_N_DEV = 500
DEFAULT_NGRAM = 13


def sha256_file(path):
    """
    Calculate SHA256 using canonical LF line endings.

    This ensures consistent manifest verification across
    Windows (CRLF) and Unix-like systems (LF).
    """
    content = path.read_bytes()

    # Normalize Windows and legacy Mac line endings to LF.
    content = content.replace(b"\r\n", b"\n")
    content = content.replace(b"\r", b"\n")

    return hashlib.sha256(content).hexdigest()


def load_jsonl(path):
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_questions(path):
    records = load_jsonl(path)
    questions = {}
    for r in records:
        pid = r["problem_id"]
        if pid in questions:
            raise ValueError(f"Duplicate problem_id {pid} in {path}")
        questions[pid] = r["question"]
    return questions


def load_ids(path):
    ids = [r["problem_id"] for r in load_jsonl(path)]
    if len(ids) != len(set(ids)):
        raise ValueError(f"Duplicate problem_id in {path}")
    return set(ids)


def word_ngrams(text, n):
    """Word n-grams in order of appearance (deduplicated), so outputs do not depend on set ordering."""
    words = re.findall(r"\w+", text.lower())
    if len(words) < n:
        return [tuple(words)]
    return list(dict.fromkeys(tuple(words[i:i + n]) for i in range(len(words) - n + 1)))


def find_near_duplicates(candidates, references, n):
    """Return {candidate_id: [matched reference ids]} for candidates sharing any n-gram."""
    index = {}
    for rid, question in references.items():
        for gram in word_ngrams(question, n):
            index.setdefault(gram, set()).add(rid)

    flagged = {}
    for cid, question in candidates.items():
        matched = set()
        example = None
        for gram in word_ngrams(question, n):
            if gram in index:
                matched |= index[gram]
                if example is None:
                    example = " ".join(gram)
        if matched:
            flagged[cid] = {"matched_ids": sorted(matched), "example_ngram": example}
    return flagged


def write_ids(path, ids):
    with path.open("w", encoding="utf-8") as f:
        for pid in sorted(ids):
            f.write(pid + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=BASE / "splits")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--n-dev", type=int, default=DEFAULT_N_DEV)
    parser.add_argument("--ngram", type=int, default=DEFAULT_NGRAM)
    args = parser.parse_args()

    if args.out_dir.exists():
        print(f"[FAIL] {args.out_dir} already exists. Refusing to overwrite a split.")
        sys.exit(1)

    train = load_questions(TRAIN_FILE)
    test = load_questions(TEST_FILE)
    batch_ids = load_ids(BATCH_FILE)
    supplement_ids = load_ids(SUPPLEMENT_FILE)

    for name, ids in (("batch_100", batch_ids), ("supplement", supplement_ids)):
        missing = ids - set(train)
        if missing:
            raise ValueError(f"{name} ids not in gsm8k_train: {sorted(missing)[:5]}")
    if batch_ids & supplement_ids:
        raise ValueError("batch_100 and supplement overlap")
    if len(supplement_ids) > args.n_dev:
        raise ValueError("supplement is larger than --n-dev")

    # D_dev: supplement + seeded random sample of the rest
    dev_candidates = sorted(set(train) - batch_ids - supplement_ids)
    n_random = args.n_dev - len(supplement_ids)
    rng = random.Random(args.seed)
    dev_random = set(rng.sample(dev_candidates, n_random))
    dev_ids = supplement_ids | dev_random

    test_ids = set(test)

    # D_pool before near-duplicate removal
    pool_candidates = set(train) - dev_ids

    references = {pid: train[pid] for pid in dev_ids}
    references.update(test)
    flagged = find_near_duplicates({pid: train[pid] for pid in pool_candidates}, references, args.ngram)

    flagged_batch = sorted(set(flagged) & batch_ids)
    if flagged_batch:
        print("[FAIL] batch_100 problems flagged as near-duplicates (must stay in D_pool):")
        for pid in flagged_batch:
            print(f"       {pid}: {flagged[pid]}")
        sys.exit(1)

    pool_ids = pool_candidates - set(flagged)

    # Sanity checks
    assert not (pool_ids & dev_ids) and not (pool_ids & test_ids) and not (dev_ids & test_ids)
    assert batch_ids <= pool_ids and supplement_ids <= dev_ids
    assert len(dev_ids) == args.n_dev

    args.out_dir.mkdir(parents=True)
    files = {
        "d_pool": args.out_dir / "d_pool_ids.txt",
        "d_dev": args.out_dir / "d_dev_ids.txt",
        "d_test": args.out_dir / "d_test_ids.txt",
    }
    write_ids(files["d_pool"], pool_ids)
    write_ids(files["d_dev"], dev_ids)
    write_ids(files["d_test"], test_ids)

    near_dup_file = args.out_dir / "near_duplicates.jsonl"
    with near_dup_file.open("w", encoding="utf-8") as f:
        for pid in sorted(flagged):
            f.write(json.dumps({"problem_id": pid, **flagged[pid]}, ensure_ascii=False) + "\n")

    def rel(path):
        path = Path(path).resolve()
        return str(path.relative_to(BASE)) if path.is_relative_to(BASE) else str(path)

    manifest = {
        "split_version": "v1",
        "created_by": rel(__file__),
        "script_sha256": sha256_file(Path(__file__)),
        "split_seed": args.seed,
        "rules": {
            "level": "problem_id; all trajectories of a problem share its split",
            "d_test": "all problems in gsm8k_test.jsonl (official GSM8K test)",
            "d_dev": f"all supplement_selected problems + random.Random(split_seed).sample(sorted(gsm8k_train - batch_100 - supplement), n_dev - |supplement|)",
            "d_pool": "gsm8k_train - d_dev - near_duplicates",
            "near_duplicate": f"D_pool candidate shares >= 1 lowercase word {args.ngram}-gram (regex \\w+) with any D_dev or D_test question; whole question used if shorter than {args.ngram} words",
            "batch_100": "must be in d_pool",
        },
        "n_dev": args.n_dev,
        "ngram": args.ngram,
        "sources": {
            name: {"path": rel(path), "sha256": sha256_file(path)}
            for name, path in (
                ("gsm8k_train", TRAIN_FILE),
                ("gsm8k_test", TEST_FILE),
                ("batch_100", BATCH_FILE),
                ("supplement_selected", SUPPLEMENT_FILE),
            )
        },
        "counts": {
            "gsm8k_train": len(train),
            "gsm8k_test": len(test),
            "d_pool": len(pool_ids),
            "d_dev": len(dev_ids),
            "d_dev_supplement": len(supplement_ids),
            "d_dev_random": len(dev_random),
            "d_test": len(test_ids),
            "near_duplicates_removed": len(flagged),
            "batch_100_in_pool": len(batch_ids & pool_ids),
        },
        "files": {
            name: {"path": rel(path), "sha256": sha256_file(path)}
            for name, path in {**files, "near_duplicates": near_dup_file}.items()
        },
    }
    with (args.out_dir / "split_manifest.json").open("w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(json.dumps(manifest["counts"], indent=2))
    print(f"[PASS] Wrote splits to {args.out_dir}")


if __name__ == "__main__":
    main()
