
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

A1_SOURCE = ROOT / "data/supplement/supplement_annotations_v2.jsonl"
MANIFEST = ROOT / "data/annotation/a2_supplement_manifest.csv"
OUTPUT = ROOT / "data/annotation/a1_supplement_agreement_25.jsonl"

VALID_CAPABILITIES = {
    "addition",
    "subtraction",
    "multiplication",
    "division",
    "percentage",
    "fraction",
    "ratio",
}

VALID_DIFFICULTIES = {"easy", "medium", "hard"}


def read_jsonl(path):
    records = []

    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            if not line.strip():
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON at {path}, line {line_no}"
                ) from exc

            records.append(record)

    return records


def validate_record(record, expected_id):
    pid = record.get("problem_id")

    if pid != expected_id:
        raise ValueError(
            f"Unexpected problem_id: expected {expected_id}, got {pid}"
        )

    required = {
        "problem_id",
        "capabilities_manual",
        "difficulty_manual",
        "notes",
    }

    missing = required - set(record)

    if missing:
        raise ValueError(
            f"{pid}: missing fields {sorted(missing)}"
        )

    labels = record["capabilities_manual"]

    if not isinstance(labels, list) or not labels:
        raise ValueError(
            f"{pid}: capabilities_manual must be a non-empty list"
        )

    if any(not isinstance(x, str) for x in labels):
        raise ValueError(
            f"{pid}: capability labels must be strings"
        )

    if len(labels) != len(set(labels)):
        raise ValueError(
            f"{pid}: duplicate capability labels"
        )

    invalid = set(labels) - VALID_CAPABILITIES

    if invalid:
        raise ValueError(
            f"{pid}: invalid capabilities {sorted(invalid)}"
        )

    difficulty = record["difficulty_manual"]

    if difficulty not in VALID_DIFFICULTIES:
        raise ValueError(
            f"{pid}: invalid difficulty {difficulty}"
        )


def main():
    for path in [A1_SOURCE, MANIFEST]:
        if not path.exists():
            raise FileNotFoundError(path)

    # Load A2 manifest.
    with MANIFEST.open(
        "r", encoding="utf-8-sig", newline=""
    ) as f:
        manifest = list(csv.DictReader(f))

    expected_ids = [
        row["problem_id"].strip()
        for row in manifest
    ]

    if len(expected_ids) != 25:
        raise ValueError(
            f"Expected 25 manifest IDs, found {len(expected_ids)}"
        )

    if len(expected_ids) != len(set(expected_ids)):
        raise ValueError("Duplicate problem IDs in manifest")

    # Load original A1 annotations.
    a1_records = read_jsonl(A1_SOURCE)

    a1_by_id = {}

    for record in a1_records:
        pid = record.get("problem_id")

        if not pid:
            raise ValueError("A1 record missing problem_id")

        if pid in a1_by_id:
            raise ValueError(f"Duplicate A1 ID: {pid}")

        a1_by_id[pid] = record

    # Match A1 records against the manifest.
    missing = sorted(set(expected_ids) - set(a1_by_id))

    if missing:
        raise ValueError(
            f"Manifest IDs missing from A1: {missing}"
        )

    subset = []

    for pid in expected_ids:
        source = a1_by_id[pid]

        validate_record(source, pid)

        # Explicitly preserve ORIGINAL A1 annotations.
        # Do not read semantic_review_85.csv here.
        record = {
            "problem_id": pid,
            "capabilities_manual": source["capabilities_manual"],
            "difficulty_manual": source["difficulty_manual"],
            "notes": source["notes"],
            "annotator_id": "A1",
            "schema_version": source.get("schema_version", "v1"),
        }

        subset.append(record)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT.open("w", encoding="utf-8") as f:
        for record in subset:
            f.write(
                json.dumps(record, ensure_ascii=False) + "\n"
            )

    print("A1 AGREEMENT SUBSET: PASS")
    print(f"A1 source records: {len(a1_records)}")
    print(f"Manifest records: {len(expected_ids)}")
    print(f"Subset records: {len(subset)}")
    print(
        "Unique subset IDs:",
        len({r["problem_id"] for r in subset})
    )
    print("Label source: original A1 annotations")
    print(f"Output: {OUTPUT}")


if __name__ == "__main__":
    main()
