
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

CANDIDATE_FILES = [
    "data/supplement/supplement_annotations_v2.jsonl",
    "data/supplement/supplement_annotations.jsonl",
    "data/raw/supplement_annotations.jsonl",
    "data/raw/supplement_selected.jsonl",
    "reports/capability/d2_regression/gold_evaluation_input.jsonl",
    "data/pilot/pilot_30_annotations.jsonl",
    "data/pilot/pilot_30_annotations_A2.jsonl",
]

VALID_CAPABILITIES = {
    "addition",
    "subtraction",
    "multiplication",
    "division",
    "percentage",
    "fraction",
    "ratio",
}


def load_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    records = []
    errors = []

    with path.open("r", encoding="utf-8-sig") as f:
        for line_no, line in enumerate(f, start=1):
            if not line.strip():
                continue

            try:
                record = json.loads(line)
                if not isinstance(record, dict):
                    errors.append(
                        f"Line {line_no}: JSON value is not an object"
                    )
                    continue

                record["_inspection_line"] = line_no
                records.append(record)

            except json.JSONDecodeError as exc:
                errors.append(
                    f"Line {line_no}: JSON error: {exc}"
                )

    return records, errors


def get_problem_id(record: dict[str, Any]) -> str | None:
    value = record.get("problem_id")

    if value is None:
        return None

    return str(value).strip()


def get_labels(record: dict[str, Any]) -> list[str]:
    value = record.get("capabilities_manual")

    if isinstance(value, list):
        return [
            str(item).strip()
            for item in value
        ]

    return []


def inspect_file(relative_path: str) -> set[str]:
    path = ROOT / relative_path

    print("\n" + "=" * 90)
    print(f"FILE: {relative_path}")
    print(f"EXISTS: {path.exists()}")

    if not path.exists():
        print("STATUS: NOT FOUND")
        return set()

    records, errors = load_jsonl(path)

    ids = [
        get_problem_id(record)
        for record in records
    ]

    valid_ids = [
        value for value in ids
        if value
    ]

    duplicate_ids = [
        problem_id
        for problem_id, count in Counter(valid_ids).items()
        if count > 1
    ]

    missing_id_count = sum(
        1 for value in ids if not value
    )

    fields = sorted({
        key
        for record in records
        for key in record.keys()
        if key != "_inspection_line"
    })

    label_counter = Counter()

    missing_label_count = 0
    invalid_label_records = []

    for record in records:
        labels = get_labels(record)

        if "capabilities_manual" not in record:
            missing_label_count += 1
            continue

        for label in labels:
            label_counter[label] += 1

            if label not in VALID_CAPABILITIES:
                invalid_label_records.append({
                    "problem_id": get_problem_id(record),
                    "label": label,
                    "line": record.get("_inspection_line"),
                })

    print(f"Records: {len(records)}")
    print(f"Unique problem IDs: {len(set(valid_ids))}")
    print(f"Duplicate IDs: {len(duplicate_ids)}")
    print(f"Missing problem_id: {missing_id_count}")
    print(f"Missing capabilities_manual: {missing_label_count}")
    print(f"JSON parsing errors: {len(errors)}")
    print(f"Fields: {fields}")
    print(f"Capability support: {dict(label_counter)}")

    if duplicate_ids:
        print("Duplicate ID examples:", duplicate_ids[:10])

    if invalid_label_records:
        print("Invalid capability examples:")
        for item in invalid_label_records[:10]:
            print(item)

    if errors:
        print("Parsing error examples:")
        for error in errors[:5]:
            print(error)

    if records:
        print("\nFIRST RECORD:")
        first_record = {
            key: value
            for key, value in records[0].items()
            if key != "_inspection_line"
        }
        print(json.dumps(
            first_record,
            ensure_ascii=False,
            indent=2
        ))

    return set(valid_ids)


def main() -> None:
    print("SUPPLEMENT SOURCE INSPECTION")
    print("=" * 90)
    print(f"Repository root: {ROOT}")

    all_ids: dict[str, set[str]] = {}

    for relative_path in CANDIDATE_FILES:
        all_ids[relative_path] = inspect_file(relative_path)

    print("\n" + "=" * 90)
    print("PAIRWISE ID OVERLAP")
    print("=" * 90)

    paths = list(all_ids.keys())

    for i in range(len(paths)):
        for j in range(i + 1, len(paths)):
            ids_a = all_ids[paths[i]]
            ids_b = all_ids[paths[j]]

            if not ids_a or not ids_b:
                continue

            overlap = ids_a & ids_b

            print(
                f"{paths[i]} <-> {paths[j]}: "
                f"{len(overlap)} shared IDs"
            )

    print("\nInspection completed.")
    print("No source files were modified.")


if __name__ == "__main__":
    main()
