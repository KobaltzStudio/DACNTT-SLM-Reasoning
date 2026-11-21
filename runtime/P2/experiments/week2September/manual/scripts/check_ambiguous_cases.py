import json
import sys
from pathlib import Path


BASE = Path(__file__).resolve().parents[1]


EXPECTED_IDS = {
    "gsm8k_train_00023",
    "gsm8k_train_00029",
    "gsm8k_train_00056",
    "gsm8k_train_00073",
    "gsm8k_train_00082",
}


VALID_STATUSES = {
    "open",
    "resolved",
}


def load_jsonl(path: Path):
    if not path.exists():
        raise FileNotFoundError(
            f"File not found: {path}"
        )

    records = []

    with path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON at {path}, "
                    f"line {line_number}: {exc}"
                ) from exc

    return records


def main():
    if len(sys.argv) != 2:
        print(
            "Usage:\n"
            "python check_ambiguous_cases.py "
            "<ambiguous_cases.jsonl>"
        )
        sys.exit(1)

    path = Path(sys.argv[1])

    records = load_jsonl(path)

    if not records:
        raise ValueError(
            "Ambiguous-case file is empty."
        )

    ids = [
        record.get("problem_id")
        for record in records
    ]

    if any(problem_id is None for problem_id in ids):
        raise ValueError(
            "Every ambiguous-case record "
            "must contain problem_id."
        )

    duplicate_ids = sorted(
        {
            problem_id
            for problem_id in ids
            if ids.count(problem_id) > 1
        }
    )

    if duplicate_ids:
        raise ValueError(
            f"Duplicate ambiguous-case IDs: "
            f"{duplicate_ids}"
        )

    id_set = set(ids)

    missing = sorted(
        EXPECTED_IDS - id_set
    )

    extra = sorted(
        id_set - EXPECTED_IDS
    )

    if missing:
        raise ValueError(
            "Missing expected issue IDs: "
            f"{missing}"
        )

    if extra:
        print(
            "WARNING: extra issue IDs:"
        )

        for problem_id in extra:
            print(
                f"  {problem_id}"
            )

    print(
        f"Total issue records: "
        f"{len(records)}"
    )

    open_count = 0
    resolved_count = 0

    for record in records:
        problem_id = record[
            "problem_id"
        ]

        status = record.get(
            "status"
        )

        if status not in VALID_STATUSES:
            raise ValueError(
                f"{problem_id}: unsupported "
                f"status={status!r}"
            )

        if status == "open":
            open_count += 1

            decision = record.get(
                "decision"
            )

            review_reason = record.get(
                "review_reason"
            )

            if decision != (
                "pending_source_verification"
            ):
                raise ValueError(
                    f"{problem_id}: open case must "
                    "have decision="
                    "'pending_source_verification'."
                )

            if not review_reason:
                raise ValueError(
                    f"{problem_id}: open case has "
                    "no review_reason."
                )

            print(
                f"{problem_id}: "
                "OPEN - explicitly justified"
            )

        elif status == "resolved":
            resolved_count += 1

            decision = record.get(
                "decision"
            )

            final_interpretation = record.get(
                "final_interpretation"
            )

            if not decision:
                raise ValueError(
                    f"{problem_id}: resolved case "
                    "has no decision."
                )

            if not final_interpretation:
                raise ValueError(
                    f"{problem_id}: resolved case "
                    "has no final_interpretation."
                )

            if (
                "ground_truth_consistent"
                not in record
            ):
                raise ValueError(
                    f"{problem_id}: resolved case "
                    "must explicitly state "
                    "ground_truth_consistent."
                )

            print(
                f"{problem_id}: RESOLVED"
            )

    print()
    print(
        f"Open cases: {open_count}"
    )

    print(
        f"Resolved cases: {resolved_count}"
    )

    print()
    print(
        "Ambiguous-case audit: PASS"
    )


if __name__ == "__main__":
    main()