
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any


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
    "problem_id",
    "capabilities_manual",
}


def load_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    records = []
    errors = []

    with path.open("r", encoding="utf-8-sig") as f:
        for line_no, line in enumerate(f, start=1):
            if not line.strip():
                continue

            try:
                record = json.loads(line)

                if not isinstance(record, dict):
                    errors.append({
                        "line": line_no,
                        "error": "JSON value is not an object",
                    })
                    continue

                record["_source_line"] = line_no
                records.append(record)

            except json.JSONDecodeError as exc:
                errors.append({
                    "line": line_no,
                    "error": str(exc),
                })

    return records, errors


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit supplement capability annotations."
    )

    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--expected-count", type=int, default=None)

    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output_dir)

    if not input_path.exists():
        raise FileNotFoundError(
            f"Input file does not exist: {input_path}"
        )

    output_dir.mkdir(parents=True, exist_ok=True)

    records, parse_errors = load_jsonl(input_path)

    id_counter = Counter()
    capability_counter = Counter()

    audit_rows = []

    for record in records:
        problem_id = record.get("problem_id")
        labels = record.get("capabilities_manual")

        issues = []

        if not problem_id or not str(problem_id).strip():
            issues.append("MISSING_PROBLEM_ID")

        if "capabilities_manual" not in record:
            issues.append("MISSING_CAPABILITIES_FIELD")

        elif not isinstance(labels, list):
            issues.append("INVALID_CAPABILITIES_TYPE")
            labels = []

        elif not labels:
            issues.append("EMPTY_CAPABILITY_LABELS")

        normalized_labels = []

        for label in labels:
            if not isinstance(label, str):
                issues.append("NON_STRING_CAPABILITY")
                continue

            normalized = label.strip()

            if not normalized:
                issues.append("EMPTY_CAPABILITY_LABEL")
                continue

            normalized_labels.append(normalized)

            if normalized not in VALID_CAPABILITIES:
                issues.append(
                    f"UNKNOWN_CAPABILITY:{normalized}"
                )

        if problem_id:
            id_counter[str(problem_id).strip()] += 1

        for label in normalized_labels:
            capability_counter[label] += 1

        if len(normalized_labels) != len(set(normalized_labels)):
            issues.append("DUPLICATE_LABEL_WITHIN_RECORD")

        audit_rows.append({
            "problem_id": problem_id or "",
            "source_line": record.get("_source_line", ""),
            "status": "PASS" if not issues else "REVIEW",
            "issues": ";".join(sorted(set(issues))),
            "capabilities_manual": json.dumps(
                normalized_labels,
                ensure_ascii=False,
            ),
            "available_fields": ";".join(
                sorted(
                    key for key in record.keys()
                    if key != "_source_line"
                )
            ),
        })

    duplicate_ids = {
        problem_id: count
        for problem_id, count in id_counter.items()
        if count > 1
    }

    for row in audit_rows:
        problem_id = str(row["problem_id"]).strip()

        if problem_id in duplicate_ids:
            row["status"] = "REVIEW"

            duplicate_issue = "DUPLICATE_PROBLEM_ID"

            if row["issues"]:
                row["issues"] += ";" + duplicate_issue
            else:
                row["issues"] = duplicate_issue

    csv_path = output_dir / "supplement_audit.csv"

    with csv_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        fieldnames = [
            "problem_id",
            "source_line",
            "status",
            "issues",
            "capabilities_manual",
            "available_fields",
        ]

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(audit_rows)

    pass_count = sum(
        row["status"] == "PASS"
        for row in audit_rows
    )

    review_count = sum(
        row["status"] == "REVIEW"
        for row in audit_rows
    )

    expected_count_ok = (
        args.expected_count is None
        or len(records) == args.expected_count
    )

    summary = {
        "input_file": str(input_path),
        "input_records": len(records),
        "expected_records": args.expected_count,
        "count_check": expected_count_ok,
        "unique_ids": len(id_counter),
        "duplicate_id_count": len(duplicate_ids),
        "duplicate_ids": duplicate_ids,
        "pass_count": pass_count,
        "review_count": review_count,
        "json_parse_error_count": len(parse_errors),
        "json_parse_errors": parse_errors,
        "capability_support": dict(capability_counter),
        "semantic_review_completed": False,
        "audit_scope": (
            "Structural validation only. "
            "Does not establish semantic label correctness."
        ),
    }

    summary_path = (
        output_dir / "supplement_audit_summary.json"
    )

    summary_path.write_text(
        json.dumps(
            summary,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("SUPPLEMENT AUDIT")
    print("-" * 60)
    print(f"Input: {input_path}")
    print(f"Input records: {len(records)}")
    print(f"Expected records: {args.expected_count}")
    print(f"Count check: {expected_count_ok}")
    print(f"Unique IDs: {len(id_counter)}")
    print(f"Duplicate IDs: {len(duplicate_ids)}")
    print(f"PASS: {pass_count}")
    print(f"REVIEW: {review_count}")
    print(f"JSON parsing errors: {len(parse_errors)}")
    print(f"Capability support: {dict(capability_counter)}")
    print(f"CSV: {csv_path}")
    print(f"Summary: {summary_path}")

    if not expected_count_ok:
        print(
            "WARNING: Record count does not match "
            "the expected count."
        )

    print(
        "NOTE: PASS means structural checks passed, "
        "not semantic correctness."
    )


if __name__ == "__main__":
    main()
