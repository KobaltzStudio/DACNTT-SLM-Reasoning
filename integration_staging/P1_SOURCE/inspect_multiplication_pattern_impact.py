import csv
import json
from pathlib import Path

MANUAL = Path("experiments/week2September/manual")

APPROVED = (
    MANUAL
    / "reports/capability/p1_day14_final_2026-11-14/approved/"
    / "priority_error_review_170_approved.csv"
)

CHANGES = (
    MANUAL
    / "reports/capability/p1_extractor_v3_1_2026-11-14/"
    / "candidate_analysis/candidate_changes_170.csv"
)

TARGET_FP = "gsm8k_train_00011"


def parse_value(value):
    if value is None:
        return value

    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return value


def parse_labels(value):
    parsed = parse_value(value)

    if isinstance(parsed, list):
        return set(parsed)

    if isinstance(parsed, str):
        return {parsed} if parsed else set()

    return set()


def load_csv(path):
    if not path.exists():
        raise FileNotFoundError(path)

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        return list(csv.DictReader(f))


def print_field(row, key):
    if key in row and row[key] not in (None, ""):
        print(f"{key}: {row[key]}")


def main():
    approved_rows = load_csv(APPROVED)
    change_rows = load_csv(CHANGES)

    approved_by_id = {
        row["problem_id"]: row
        for row in approved_rows
    }

    if len(approved_rows) != 170:
        raise ValueError(
            f"Expected 170 approved rows, got {len(approved_rows)}"
        )

    selected = []

    for change in change_rows:
        problem_id = change["problem_id"]

        new_fp = parse_labels(
            change.get("new_false_positive")
        )

        fixed_fn = parse_labels(
            change.get("fixed_false_negative")
        )

        if (
            "multiplication" in new_fp
            or "multiplication" in fixed_fn
        ):
            selected.append(change)

    selected.sort(
        key=lambda row: (
            row["problem_id"] != TARGET_FP,
            row["problem_id"],
        )
    )

    print("=" * 110)
    print("MULTIPLICATION PATTERN IMPACT REVIEW")
    print("=" * 110)

    print("Approved rows:", len(approved_rows))
    print("Selected affected rows:", len(selected))

    fp_count = 0
    fixed_count = 0

    for index, change in enumerate(selected, start=1):
        problem_id = change["problem_id"]
        approved = approved_by_id.get(problem_id, {})

        new_fp = parse_labels(
            change.get("new_false_positive")
        )

        fixed_fn = parse_labels(
            change.get("fixed_false_negative")
        )

        if "multiplication" in new_fp:
            classification = "NEW FALSE POSITIVE"
            fp_count += 1
        elif "multiplication" in fixed_fn:
            classification = "FIXED FALSE NEGATIVE"
            fixed_count += 1
        else:
            classification = "OTHER"

        print("\n" + "=" * 110)
        print(f"CASE {index}/{len(selected)}")
        print("PROBLEM ID:", problem_id)
        print("CLASSIFICATION:", classification)

        print("\nQUESTION:")
        print(
            approved.get("question")
            or change.get("question")
            or "[QUESTION NOT FOUND]"
        )

        print("\nGOLD:")
        print(
            approved.get("gold_capabilities")
            or change.get("gold_capabilities")
        )

        print("\nCANDIDATE CHANGE:")
        for key in (
            "predicted_capabilities",
            "candidate_predictions",
            "false_negatives",
            "false_positives",
            "new_false_positive",
            "fixed_false_negative",
            "evidence",
            "rules_fired",
        ):
            print_field(change, key)

        print("\nANNOTATION METADATA:")
        for key in (
            "solution_trace_available",
            "gold_label_correct",
            "human_approval",
            "review_status",
            "error_classification",
            "review_notes",
            "source_annotation_notes",
            "proposed_action",
        ):
            print_field(approved, key)

    print("\n" + "=" * 110)
    print("SUMMARY")
    print("=" * 110)
    print("New multiplication false positives:", fp_count)
    print("Fixed multiplication false negatives:", fixed_count)
    print("Total selected:", len(selected))

    if len(selected) != 16:
        print(
            "WARNING: Expected 16 affected rows. "
            "Check the candidate_changes CSV schema and contents."
        )

    print("\nInspection completed. No files modified.")


if __name__ == "__main__":
    main()
