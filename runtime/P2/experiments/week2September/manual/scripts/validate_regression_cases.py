import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]

INPUT = BASE / "data" / "regression" / "capability_regression_cases_v1.jsonl"

VALID_CAPABILITIES = {
    "addition",
    "subtraction",
    "multiplication",
    "division",
    "percentage",
    "fraction",
    "ratio",
}

REQUIRED_FIELDS = {
    "test_id",
    "problem",
    "expected_capabilities",
    "category",
    "must_not_include",
    "guideline_version",
    "rules_version",
    "source",
}


def main():
    records = []
    seen_ids = set()

    with INPUT.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            if not line.strip():
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON at line {line_number}: {exc}"
                )

            missing = REQUIRED_FIELDS - record.keys()
            if missing:
                raise ValueError(
                    f"Missing fields at line {line_number}: {sorted(missing)}"
                )

            test_id = record["test_id"]

            if test_id in seen_ids:
                raise ValueError(f"Duplicate test_id: {test_id}")

            seen_ids.add(test_id)

            if not record["problem"].strip():
                raise ValueError(f"Empty problem: {test_id}")

            expected = set(record["expected_capabilities"])
            forbidden = set(record["must_not_include"])

            if not expected:
                raise ValueError(f"Empty expected capabilities: {test_id}")

            if not expected <= VALID_CAPABILITIES:
                raise ValueError(f"Invalid expected capability: {test_id}")

            if not forbidden <= VALID_CAPABILITIES:
                raise ValueError(f"Invalid forbidden capability: {test_id}")

            if expected & forbidden:
                raise ValueError(
                    f"Capability both expected and forbidden: {test_id}"
                )

            records.append(record)

    if len(records) != 30:
        raise ValueError(
            f"Expected 30 cases, found {len(records)}"
        )

    categories = {}
    for record in records:
        category = record["category"]
        categories[category] = categories.get(category, 0) + 1

    print("REGRESSION DATASET VALIDATION")
    print(f"Records: {len(records)}")
    print(f"Unique IDs: {len(seen_ids)}")
    print(f"Categories: {categories}")
    print("[PASS] Regression dataset structure is valid")


if __name__ == "__main__":
    main()