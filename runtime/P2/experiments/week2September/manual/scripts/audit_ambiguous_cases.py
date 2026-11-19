#!/usr/bin/env python3

import argparse
import json
from pathlib import Path


REQUIRED = [
    "problem_id",
    "issue_type",
    "status",
    "description",
    "action",
    "decision",
    "final_interpretation",
    "ground_truth_consistent",
]


def load_jsonl(path):
    rows = []

    with open(path, encoding="utf-8") as f:
        for line_number, line in enumerate(f, 1):
            if not line.strip():
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON at line {line_number}: {exc}"
                ) from exc

            rows.append(record)

    return rows


def main():
    parser = argparse.ArgumentParser(
        description="Audit ambiguous GSM8K manual-annotation cases."
    )

    parser.add_argument(
        "input",
        help="Path to ambiguous_cases.jsonl",
    )

    parser.add_argument(
        "--output",
        required=True,
        help="Path for audited JSONL output.",
    )

    parser.add_argument(
        "--report",
        required=True,
        help="Path for audit report JSON.",
    )

    args = parser.parse_args()

    rows = load_jsonl(args.input)

    seen = set()

    for index, row in enumerate(rows, start=1):
        missing = [
            field
            for field in REQUIRED
            if field not in row
        ]

        if missing:
            raise ValueError(
                f"Line {index}: missing fields {missing}"
            )

        problem_id = row["problem_id"]

        if problem_id in seen:
            raise ValueError(
                f"Duplicate problem_id: {problem_id}"
            )

        seen.add(problem_id)

    report = {
        "schema_version": "v1",
        "task": "Task 3 - ambiguous case audit",
        "total_cases": len(rows),
        "resolved": sum(
            row["status"] == "resolved"
            for row in rows
        ),
        "open": sum(
            row["status"] != "resolved"
            for row in rows
        ),
        "ground_truth_inconsistent": sum(
            row["ground_truth_consistent"] is False
            for row in rows
        ),
        "annotation_revised": sum(
            row["decision"].startswith(
                "revise_annotation"
            )
            for row in rows
        ),
        "annotation_retained": sum(
            row["decision"].startswith(
                "retain_annotation"
            )
            for row in rows
        ),
        "guideline_revisions_required": 0,
        "cases": [
            {
                "problem_id": row["problem_id"],
                "decision": row["decision"],
                "ground_truth_consistent": row[
                    "ground_truth_consistent"
                ],
            }
            for row in rows
        ],
    }

    pass_criteria = {
        "all_cases_audited": (
            len(rows) > 0
            and all(
                row["status"] == "resolved"
                for row in rows
            )
        ),
        "clear_decision": all(
            bool(row["decision"])
            for row in rows
        ),
        "justification": all(
            bool(row["description"])
            and bool(row["final_interpretation"])
            for row in rows
        ),
        "literal_or_reference_interpretation_recorded": all(
            bool(row["final_interpretation"])
            for row in rows
        ),
        "ground_truth_inconsistency_flagged": all(
            row["ground_truth_consistent"] is not False
            or "ground_truth_inconsistency"
            in row["decision"]
            for row in rows
        ),
        "no_forced_annotation_change": all(
            not row["decision"].startswith(
                "revise_annotation"
            )
            or row["ground_truth_consistent"] is not True
            for row in rows
        ),
        "no_unresolved_cases": all(
            row["status"] == "resolved"
            for row in rows
        ),
    }

    report["pass_criteria"] = pass_criteria

    report["status"] = (
        "PASS"
        if all(pass_criteria.values())
        else "FAIL"
    )

    output_path = Path(args.output)
    report_path = Path(args.report)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    report_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as f:
        for row in rows:
            f.write(
                json.dumps(
                    row,
                    ensure_ascii=False,
                )
                + "\n"
            )

    with report_path.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            report,
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()