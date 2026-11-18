
from __future__ import annotations

import argparse
import csv
import json
import random
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

VALID_CAPABILITIES = [
    "addition",
    "subtraction",
    "multiplication",
    "division",
    "percentage",
    "fraction",
    "ratio",
]


def load_records(path: Path) -> list[dict]:
    records = []

    with path.open("r", encoding="utf-8-sig") as f:
        for line_no, line in enumerate(f, start=1):
            if not line.strip():
                continue

            record = json.loads(line)

            if not record.get("problem_id"):
                raise ValueError(
                    f"Missing problem_id at line {line_no}"
                )

            if not isinstance(record.get("capabilities_manual"), list):
                raise ValueError(
                    f"Invalid capabilities_manual at line {line_no}"
                )

            records.append(record)

    return records


def select_stratified(
    records: list[dict],
    sample_size: int,
    seed: int,
) -> list[dict]:
    if sample_size > len(records):
        raise ValueError(
            "Sample size exceeds the number of available records."
        )

    rng = random.Random(seed)

    candidates = records.copy()
    rng.shuffle(candidates)

    selected = []
    covered = set()

    # First, prioritize coverage of all capabilities.
    while candidates and len(selected) < sample_size:
        best_record = None
        best_gain = 0

        for record in candidates:
            labels = set(record["capabilities_manual"])
            gain = len(labels - covered)

            if gain > best_gain:
                best_gain = gain
                best_record = record

        if best_record is None or best_gain == 0:
            break

        selected.append(best_record)
        covered.update(best_record["capabilities_manual"])
        candidates.remove(best_record)

    # Fill the remaining slots reproducibly.
    rng.shuffle(candidates)

    while candidates and len(selected) < sample_size:
        selected.append(candidates.pop())

    return selected


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--input",
        default="data/supplement/supplement_annotations_v2.jsonl",
    )

    parser.add_argument(
        "--raw",
        default="data/raw/supplement_annotations.jsonl",
    )

    parser.add_argument(
        "--output",
        default="data/annotation/a2_supplement_manifest.csv",
    )

    parser.add_argument(
        "--sample-size",
        type=int,
        default=25,
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=42,
    )

    args = parser.parse_args()

    annotation_path = ROOT / args.input
    raw_path = ROOT / args.raw
    output_path = ROOT / args.output

    annotations = load_records(annotation_path)
    raw_records = load_records(raw_path)

    raw_by_id = {
        str(record["problem_id"]): record
        for record in raw_records
    }

    annotation_ids = {
        str(record["problem_id"])
        for record in annotations
    }

    if annotation_ids != set(raw_by_id):
        raise ValueError(
            "Annotation IDs and raw supplement IDs do not match."
        )

    selected = select_stratified(
        annotations,
        args.sample_size,
        args.seed,
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "problem_id",
                "question",
                "annotator_id",
                "annotation_status",
            ],
        )

        writer.writeheader()

        for record in selected:
            problem_id = str(record["problem_id"])
            raw = raw_by_id[problem_id]

            # Do not expose A1 labels, notes, or difficulty to A2.
            writer.writerow({
                "problem_id": problem_id,
                "question": raw.get("question", ""),
                "annotator_id": "A2",
                "annotation_status": "pending",
            })

    covered = set()

    for record in selected:
        covered.update(record["capabilities_manual"])

    print("A2 SUPPLEMENT SAMPLE MANIFEST")
    print("-" * 60)
    print("Input records:", len(annotations))
    print("Selected records:", len(selected))
    print("Seed:", args.seed)
    print("Covered capabilities:", sorted(covered))
    print("Output:", output_path)


if __name__ == "__main__":
    main()
