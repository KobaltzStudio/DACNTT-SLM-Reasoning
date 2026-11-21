
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    ROOT / "data/supplement/supplement_annotations_v2.jsonl"
)

SCHEMA_FILE = (
    ROOT / "schemas/manual_annotation_schema.json"
)

OUTPUT_FILE = (
    ROOT / "reports/capability/d3_audit/schema_validation.json"
)

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

VALID_DIFFICULTIES = {
    "easy",
    "medium",
    "hard",
}


def main() -> None:
    schema = json.loads(
        SCHEMA_FILE.read_text(encoding="utf-8-sig")
    )

    schema_required = set(schema.get("required", []))

    if schema_required != REQUIRED_FIELDS:
        raise ValueError(
            "The validator's required fields do not match "
            "manual_annotation_schema.json"
        )

    results = []
    capability_support = Counter()
    difficulty_support = Counter()
    annotator_support = Counter()
    version_support = Counter()

    with INPUT_FILE.open("r", encoding="utf-8-sig") as f:
        for line_no, line in enumerate(f, start=1):
            if not line.strip():
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                results.append({
                    "line": line_no,
                    "problem_id": "",
                    "status": "FAIL",
                    "errors": [f"INVALID_JSON: {exc}"],
                })
                continue

            errors = []

            if not isinstance(record, dict):
                results.append({
                    "line": line_no,
                    "problem_id": "",
                    "status": "FAIL",
                    "errors": ["RECORD_NOT_OBJECT"],
                })
                continue

            problem_id = record.get("problem_id", "")

            missing = REQUIRED_FIELDS - set(record.keys())

            for field in sorted(missing):
                errors.append(f"MISSING_REQUIRED_FIELD:{field}")

            for field in REQUIRED_FIELDS:
                if field in record and not isinstance(record[field], str) \
                        and field != "capabilities_manual":
                    errors.append(f"INVALID_TYPE:{field}")

            labels = record.get("capabilities_manual")

            if not isinstance(labels, list):
                errors.append("INVALID_TYPE:capabilities_manual")
                labels = []
            else:
                if len(labels) < 1:
                    errors.append("EMPTY_CAPABILITIES")

                if len(labels) != len(set(
                    x for x in labels if isinstance(x, str)
                )):
                    errors.append("DUPLICATE_CAPABILITIES")

                for label in labels:
                    if not isinstance(label, str):
                        errors.append("NON_STRING_CAPABILITY")
                    elif label not in VALID_CAPABILITIES:
                        errors.append(
                            f"INVALID_CAPABILITY:{label}"
                        )
                    else:
                        capability_support[label] += 1

            difficulty = record.get("difficulty_manual")

            if isinstance(difficulty, str):
                if difficulty not in VALID_DIFFICULTIES:
                    errors.append(
                        f"INVALID_DIFFICULTY:{difficulty}"
                    )
                else:
                    difficulty_support[difficulty] += 1

            annotator = record.get("annotator_id")
            if isinstance(annotator, str):
                annotator_support[annotator] += 1

            version = record.get("schema_version")
            if isinstance(version, str):
                version_support[version] += 1

            results.append({
                "line": line_no,
                "problem_id": problem_id,
                "status": "PASS" if not errors else "FAIL",
                "errors": errors,
            })

    pass_count = sum(
        item["status"] == "PASS"
        for item in results
    )

    fail_count = sum(
        item["status"] == "FAIL"
        for item in results
    )

    summary = {
        "input_file": str(INPUT_FILE.relative_to(ROOT)),
        "schema_file": str(SCHEMA_FILE.relative_to(ROOT)),
        "records": len(results),
        "pass_count": pass_count,
        "fail_count": fail_count,
        "schema_required_fields": sorted(schema_required),
        "capability_support": dict(capability_support),
        "difficulty_support": dict(difficulty_support),
        "annotator_support": dict(annotator_support),
        "schema_version_support": dict(version_support),
        "semantic_review_completed": False,
        "record_results": results,
    }

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_FILE.write_text(
        json.dumps(
            summary,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("SUPPLEMENT SCHEMA VALIDATION")
    print("-" * 60)
    print("Records:", len(results))
    print("PASS:", pass_count)
    print("FAIL:", fail_count)
    print("Capability support:", dict(capability_support))
    print("Difficulty support:", dict(difficulty_support))
    print("Annotator support:", dict(annotator_support))
    print("Schema version support:", dict(version_support))
    print("Output:", OUTPUT_FILE)

    if fail_count:
        print("\nFAILED RECORDS:")
        for item in results:
            if item["status"] == "FAIL":
                print(
                    item["problem_id"],
                    item["errors"],
                )


if __name__ == "__main__":
    main()
