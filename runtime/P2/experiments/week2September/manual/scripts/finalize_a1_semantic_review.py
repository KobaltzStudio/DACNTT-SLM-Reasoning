
import csv
import json
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]

INPUT = ROOT / "reports/capability/d3_audit/semantic_review_85.csv"
OUTPUT = ROOT / "reports/capability/d3_audit/semantic_review_85.csv"

REQUIRED_COLUMNS = {
    "problem_id",
    "original_labels",
    "semantic_status",
    "reviewed_labels",
    "issue_type",
    "review_rationale",
    "reviewer",
}

def parse_labels(value, problem_id, field):
    try:
        labels = json.loads(value)
    except Exception as exc:
        raise ValueError(
            f"{problem_id}: cannot parse {field}: {value}"
        ) from exc

    if not isinstance(labels, list):
        raise ValueError(f"{problem_id}: {field} must be a JSON list")

    allowed = {
        "addition",
        "subtraction",
        "multiplication",
        "division",
        "percentage",
        "fraction",
        "ratio",
    }

    if not labels:
        raise ValueError(f"{problem_id}: {field} cannot be empty")

    if len(labels) != len(set(labels)):
        raise ValueError(f"{problem_id}: duplicate labels in {field}")

    invalid = set(labels) - allowed
    if invalid:
        raise ValueError(f"{problem_id}: invalid labels {invalid}")

    return labels


def main():
    if not INPUT.exists():
        raise FileNotFoundError(INPUT)

    with INPUT.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        columns = reader.fieldnames

    missing_columns = REQUIRED_COLUMNS - set(columns or [])
    if missing_columns:
        raise ValueError(f"Missing columns: {sorted(missing_columns)}")

    if len(rows) != 85:
        raise ValueError(f"Expected 85 records, found {len(rows)}")

    ids = [row["problem_id"] for row in rows]

    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate problem_id detected")

    # User approved the semantic-review decision for this case.
    target_id = "gsm8k_train_00769"
    target_rows = [r for r in rows if r["problem_id"] == target_id]

    if len(target_rows) != 1:
        raise ValueError(f"Expected exactly one {target_id}")

    target = target_rows[0]
    target["semantic_status"] = "confirmed"

    # Validate every reviewed record.
    for row in rows:
        pid = row["problem_id"]

        if row["semantic_status"] not in {
            "confirmed",
            "needs_review",
            "reannotate",
        }:
            raise ValueError(f"{pid}: invalid semantic_status")

        parse_labels(row["original_labels"], pid, "original_labels")
        parse_labels(row["reviewed_labels"], pid, "reviewed_labels")

        if not row["reviewer"].strip():
            raise ValueError(f"{pid}: reviewer is empty")

        if not row["review_rationale"].strip():
            raise ValueError(f"{pid}: review_rationale is empty")

    status_counts = Counter(r["semantic_status"] for r in rows)
    issue_counts = Counter(
        r["issue_type"] for r in rows if r["issue_type"].strip()
    )

    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)

    print("A1 SEMANTIC REVIEW FINALIZATION: PASS")
    print(f"Records: {len(rows)}")
    print(f"Unique IDs: {len(set(ids))}")
    print(f"Status: {dict(status_counts)}")
    print(f"Issues: {dict(issue_counts)}")
    print(f"Confirmed 00769: {target['semantic_status']}")
    print(f"Output: {OUTPUT}")


if __name__ == "__main__":
    main()
