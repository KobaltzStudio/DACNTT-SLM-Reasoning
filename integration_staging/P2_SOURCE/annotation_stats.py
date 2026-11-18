import json
from pathlib import Path
from collections import Counter


BASE = Path(__file__).resolve().parents[1]

ANNOTATION_FILE = (
    BASE
    / "data"
    / "pilot"
    / "pilot_30_annotations.jsonl"
)

AMBIGUOUS_FILE = (
    BASE
    / "data"
    / "issues"
    / "ambiguous_cases.jsonl"
)

REPORT_FILE = (
    BASE
    / "reports"
    / "pilot_report.json"
)


CAPABILITIES = [
    "addition",
    "subtraction",
    "multiplication",
    "division",
    "percentage",
    "fraction",
    "ratio",
]

DIFFICULTIES = [
    "easy",
    "medium",
    "hard",
]


def load_jsonl(path):
    if not path.exists():
        return []

    with path.open(
        "r",
        encoding="utf-8"
    ) as f:
        return [
            json.loads(line)
            for line in f
            if line.strip()
        ]


def main():

    annotations = load_jsonl(
        ANNOTATION_FILE
    )

    if not annotations:
        raise RuntimeError(
            f"No annotations found: {ANNOTATION_FILE}"
        )

    capability_counts = Counter()

    difficulty_counts = Counter()

    multi_capability_count = 0

    ambiguous_problem_ids = set()

    for record in annotations:

        capabilities = record.get(
            "capabilities_manual",
            []
        )

        difficulty = record.get(
            "difficulty_manual",
            ""
        )

        for capability in capabilities:
            capability_counts[capability] += 1

        if len(capabilities) > 1:
            multi_capability_count += 1

        if difficulty:
            difficulty_counts[difficulty] += 1

        notes = record.get(
            "notes",
            ""
        ).strip().lower()

        if notes:
            ambiguity_keywords = [
                "ambiguous",
                "ambiguity",
                "unclear",
                "uncertain",
                "overlap",
                "calibration",
                "manual verification",
                "manual review",
                "review",
            ]

            if any(
                keyword in notes
                for keyword in ambiguity_keywords
            ):
                ambiguous_problem_ids.add(
                    record["problem_id"]
                )

    issue_records = load_jsonl(
        AMBIGUOUS_FILE
    )

    for issue in issue_records:

        problem_id = issue.get(
            "problem_id"
        )

        if problem_id:
            ambiguous_problem_ids.add(
                problem_id
            )

    total = len(annotations)

    report = {
        "total": total,

        "capability_counts": {
            capability:
                capability_counts.get(
                    capability,
                    0
                )
            for capability in CAPABILITIES
        },

        "capability_coverage": {
            capability:
                capability_counts.get(
                    capability,
                    0
                ) > 0
            for capability in CAPABILITIES
        },

        "multi_capability": (
            multi_capability_count
        ),

        "difficulty_counts": {
            difficulty:
                difficulty_counts.get(
                    difficulty,
                    0
                )
            for difficulty in DIFFICULTIES
        },

        "ambiguous": len(
            ambiguous_problem_ids
        ),

        "ambiguous_problem_ids": sorted(
            ambiguous_problem_ids
        ),
    }

    REPORT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with REPORT_FILE.open(
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            report,
            f,
            indent=2,
            ensure_ascii=False
        )

    print()
    print("=== Manual Annotation Statistics ===")
    print()

    print(
        f"Total = {total}"
    )

    print()
    print("Capability:")

    for capability in CAPABILITIES:

        count = capability_counts.get(
            capability,
            0
        )

        coverage = (
            count / total * 100
            if total > 0
            else 0
        )

        print(
            f"{capability:<15} "
            f"{count:>2} "
            f"({coverage:.1f}%)"
        )

    print()
    print(
        f"Multi-capability = "
        f"{multi_capability_count}"
    )

    print()
    print("Difficulty:")

    for difficulty in DIFFICULTIES:

        print(
            f"{difficulty:<15} "
            f"{difficulty_counts.get(difficulty, 0):>2}"
        )

    print()
    print(
        f"Ambiguous = "
        f"{len(ambiguous_problem_ids)}"
    )

    if ambiguous_problem_ids:

        print()
        print("Ambiguous / review cases:")

        for problem_id in sorted(
            ambiguous_problem_ids
        ):
            print(
                f" - {problem_id}"
            )

    print()
    print(
        f"Report written to: "
        f"{REPORT_FILE}"
    )


if __name__ == "__main__":
    main()