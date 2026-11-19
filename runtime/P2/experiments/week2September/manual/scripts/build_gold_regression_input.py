#!/usr/bin/env python3

import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]

GOLD_FILES = [
    BASE / "data" / "batch_100" / "batch_100_annotations_v2.jsonl",
    BASE / "data" / "supplement" / "supplement_annotations_v2.jsonl",
]

SOURCE_FILE = BASE / "data" / "raw" / "gsm8k_train.jsonl"

OUTPUT_FILE = (
    BASE / "reports" / "capability" / "d2_regression"
    / "gold_evaluation_input.jsonl"
)

CAPABILITIES = {
    "addition",
    "subtraction",
    "multiplication",
    "division",
    "percentage",
    "fraction",
    "ratio",
}


def read_jsonl(path):
    with path.open("r", encoding="utf-8") as f:
        return [
            json.loads(line)
            for line in f
            if line.strip()
        ]


def main():
    source_records = read_jsonl(SOURCE_FILE)

    source_by_id = {
        row["problem_id"]: row
        for row in source_records
    }

    if len(source_by_id) != len(source_records):
        raise ValueError("Duplicate problem IDs in source dataset")

    gold_records = []

    for path in GOLD_FILES:
        if not path.exists():
            raise FileNotFoundError(path)

        gold_records.extend(read_jsonl(path))

    gold_ids = [
        row["problem_id"]
        for row in gold_records
    ]

    if len(gold_ids) != len(set(gold_ids)):
        raise ValueError("Duplicate problem IDs across Gold files")

    output = []
    missing_source = []

    for gold in gold_records:
        problem_id = gold["problem_id"]

        source = source_by_id.get(problem_id)

        if source is None:
            missing_source.append(problem_id)
            continue

        question = source.get("question")

        if not isinstance(question, str) or not question.strip():
            raise ValueError(
                f"Missing/empty question for {problem_id}"
            )

        labels = set(gold["capabilities_manual"])

        unknown = labels - CAPABILITIES

        if unknown:
            raise ValueError(
                f"Unknown Gold labels for {problem_id}: {unknown}"
            )

        output.append({
            "problem_id": problem_id,
            "question": question,
            "gold_capabilities": sorted(labels),
        })

    if missing_source:
        raise ValueError(
            f"Missing source problems: {missing_source[:10]}"
        )

    if len(output) != 185:
        raise ValueError(
            f"Expected 185 records, got {len(output)}"
        )

    output_ids = [
        row["problem_id"]
        for row in output
    ]

    if len(output_ids) != len(set(output_ids)):
        raise ValueError("Duplicate IDs in evaluation input")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        for row in output:
            f.write(
                json.dumps(row, ensure_ascii=False) + "\n"
            )

    print("GOLD EVALUATION INPUT")
    print(f"Gold records: {len(gold_records)}")
    print(f"Output records: {len(output)}")
    print(f"Unique IDs: {len(set(output_ids))}")
    print(f"Output: {OUTPUT_FILE}")
    print("[PASS]")


if __name__ == "__main__":
    main()