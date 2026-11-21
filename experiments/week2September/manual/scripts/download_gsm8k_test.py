"""
Download the official GSM8K test split (Task 5: D_test).

Output:
  data/raw/gsm8k_test.jsonl          problem_id, source_index, question, ground_truth
  data/raw/gsm8k_test_source.json    dataset name/config/split, HF revision, count, sha256

problem_id = gsm8k_test_{HF index:05d}, so the mapping to the HF split is the identity.
Question text and ground truth are normalized exactly like gsm8k_train.jsonl.
The script refuses to overwrite an existing output file.
"""

from pathlib import Path
import hashlib
import json
import sys

from download_gsm8k_train import extract_gsm8k_answer, normalize_text


BASE = Path(__file__).resolve().parents[1]

OUTPUT_FILE = BASE / "data" / "raw" / "gsm8k_test.jsonl"
SOURCE_FILE = BASE / "data" / "raw" / "gsm8k_test_source.json"

DATASET_NAME = "openai/gsm8k"
DATASET_CONFIG = "main"
DATASET_SPLIT = "test"

EXPECTED_COUNT = 1319


def sha256_file(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def get_revision():
    try:
        from huggingface_hub import HfApi
        return HfApi().dataset_info(DATASET_NAME).sha
    except Exception as e:
        print(f"[WARN] Could not read HF revision: {e}")
        return None


def main():
    for path in (OUTPUT_FILE, SOURCE_FILE):
        if path.exists():
            print(f"[FAIL] {path} already exists. Refusing to overwrite.")
            sys.exit(1)

    from datasets import load_dataset

    revision = get_revision()
    dataset = load_dataset(DATASET_NAME, DATASET_CONFIG, split=DATASET_SPLIT, revision=revision)

    if len(dataset) != EXPECTED_COUNT:
        print(f"[FAIL] Expected {EXPECTED_COUNT} records, got {len(dataset)}")
        sys.exit(1)

    records = []
    seen_questions = set()

    for index, row in enumerate(dataset):
        question = normalize_text(row["question"])
        if not question:
            raise ValueError(f"Empty question at HF index {index}")
        if question in seen_questions:
            raise ValueError(f"Duplicate question at HF index {index}")
        seen_questions.add(question)

        records.append(
            {
                "problem_id": f"gsm8k_test_{index:05d}",
                "source_index": index,
                "question": question,
                "ground_truth": normalize_text(extract_gsm8k_answer(row["answer"])),
            }
        )

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    source = {
        "dataset": DATASET_NAME,
        "config": DATASET_CONFIG,
        "split": DATASET_SPLIT,
        "revision": revision,
        "count": len(records),
        "problem_id_rule": "gsm8k_test_{hf_index:05d}",
        "output_file": str(OUTPUT_FILE.relative_to(BASE)),
        "output_sha256": sha256_file(OUTPUT_FILE),
    }
    with SOURCE_FILE.open("w", encoding="utf-8") as f:
        json.dump(source, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"[PASS] Wrote {len(records)} records to {OUTPUT_FILE}")
    print(f"[PASS] Revision: {revision}")
    print(f"[PASS] sha256: {source['output_sha256']}")


if __name__ == "__main__":
    main()
