import csv
import json
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]

MANIFEST = ROOT / "data/annotation/a2_supplement_manifest.csv"
ANNOTATIONS = ROOT / "data/annotation/a2_supplement_annotations.jsonl"
OUTPUT = ROOT / "reports/capability/d3_audit/a2_validation_report.json"

REQUIRED_FIELDS = {
    "problem_id",
    "capabilities_manual",
    "difficulty_manual",
    "notes",
    "annotator_id",
    "schema_version",
}

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


def load_manifest():
    with MANIFEST.open(
        "r", encoding="utf-8-sig", newline=""
    ) as f:
        rows = list(csv.DictReader(f))

    ids = []

    for row in rows:
        pid = (row.get("problem_id") or "").strip()

        if not pid:
            raise ValueError("Manifest contains an empty problem_id")

        ids.append(pid)

    if len(ids) != len(set(ids)):
        raise ValueError("Manifest contains duplicate problem IDs")

    return ids


def load_jsonl():
    records = []
    errors = []

    with ANNOTATIONS.open("r", encoding="utf-8-sig") as f:
        for line_no, line in enumerate(f, start=1):
            if not line.strip():
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append({
                    "line": line_no,
                    "error": f"Invalid JSON: {exc}"
                })
                continue

            if not isinstance(record, dict):
                errors.append({
                    "line": line_no,
                    "error": "Each JSONL line must be a JSON object"
                })
                continue

            records.append(record)

    return records, errors


def validate_record(record, index):
    errors = []

    missing = REQUIRED_FIELDS - set(record.keys())

    if missing:
        errors.append(
            f"Record {index}: missing fields {sorted(missing)}"
        )

    pid = record.get("problem_id")

    if not isinstance(pid, str) or not pid.strip():
        errors.append(f"Record {index}: invalid problem_id")

    labels = record.get("capabilities_manual")

    if not isinstance(labels, list) or not labels:
        errors.append(
            f"Record {index}: capabilities_manual must be a non-empty list"
        )
    else:
        if any(not isinstance(label, str) for label in labels):
            errors.append(
                f"Record {index}: every capability must be a string"
            )
        else:
            if len(labels) != len(set(labels)):
                errors.append(
                    f"Record {index}: duplicate capability labels"
                )

            invalid = set(labels) - VALID_CAPABILITIES

            if invalid:
                errors.append(
                    f"Record {index}: invalid capabilities {sorted(invalid)}"
                )

    difficulty = record.get("difficulty_manual")

    if difficulty not in VALID_DIFFICULTIES:
        errors.append(
            f"Record {index}: invalid difficulty '{difficulty}'"
        )

    notes = record.get("notes")

    if not isinstance(notes, str) or not notes.strip():
        errors.append(f"Record {index}: notes is empty or invalid")

    if record.get("annotator_id") != "A2":
        errors.append(
            f"Record {index}: annotator_id must be A2"
        )

    if record.get("schema_version") != "v1":
        errors.append(
            f"Record {index}: schema_version must be v1"
        )

    return errors


def main():
    for path in [MANIFEST, ANNOTATIONS]:
        if not path.exists():
            raise FileNotFoundError(
                f"Required input file does not exist: {path}"
            )

    expected_ids = load_manifest()
    records, parse_errors = load_jsonl()

    actual_ids = [
        r.get("problem_id")
        for r in records
        if isinstance(r.get("problem_id"), str)
    ]

    duplicates = sorted({
        pid for pid in actual_ids
        if actual_ids.count(pid) > 1
    })

    expected_set = set(expected_ids)
    actual_set = set(actual_ids)

    missing_ids = sorted(expected_set - actual_set)
    unexpected_ids = sorted(actual_set - expected_set)

    record_errors = []

    for index, record in enumerate(records, start=1):
        record_errors.extend(
            validate_record(record, index)
        )

    all_errors = parse_errors + [
        {"error": e} for e in record_errors
    ]

    capability_support = Counter()
    difficulty_support = Counter()

    for record in records:
        labels = record.get("capabilities_manual", [])

        if isinstance(labels, list):
            for label in labels:
                if isinstance(label, str):
                    capability_support[label] += 1

        difficulty = record.get("difficulty_manual")

        if isinstance(difficulty, str):
            difficulty_support[difficulty] += 1

    passed = (
        len(records) == len(expected_ids)
        and len(actual_ids) == len(set(actual_ids))
        and not missing_ids
        and not unexpected_ids
        and not duplicates
        and not all_errors
    )

    report = {
        "status": "PASS" if passed else "FAIL",
        "expected_records": len(expected_ids),
        "actual_records": len(records),
        "unique_problem_ids": len(set(actual_ids)),
        "missing_ids": missing_ids,
        "unexpected_ids": unexpected_ids,
        "duplicate_ids": duplicates,
        "parse_errors": parse_errors,
        "record_errors": record_errors,
        "capability_support": dict(capability_support),
        "difficulty_support": dict(difficulty_support),
        "annotator_id": "A2",
        "schema_version": "v1",
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("A2 SUPPLEMENT VALIDATION:", report["status"])
    print(f"Expected records: {len(expected_ids)}")
    print(f"Actual records: {len(records)}")
    print(f"Unique problem IDs: {len(set(actual_ids))}")
    print(f"Missing IDs: {len(missing_ids)}")
    print(f"Unexpected IDs: {len(unexpected_ids)}")
    print(f"Duplicate IDs: {len(duplicates)}")
    print(f"Parse errors: {len(parse_errors)}")
    print(f"Invalid records: {len(record_errors)}")
    print(f"Capability support: {dict(capability_support)}")
    print(f"Difficulty support: {dict(difficulty_support)}")
    print(f"Report: {OUTPUT}")

    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
