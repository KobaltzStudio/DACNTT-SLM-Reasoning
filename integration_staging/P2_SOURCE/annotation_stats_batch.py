import argparse
import json
from collections import Counter
from pathlib import Path


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
    records = []

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    return records


def main():
    parser = argparse.ArgumentParser(
        description="Compute statistics for a manual annotation JSONL file."
    )

    parser.add_argument(
        "--input",
        required=True,
        help="Path to annotation JSONL file.",
    )

    args = parser.parse_args()

    path = Path(args.input)

    if not path.exists():
        raise FileNotFoundError(
            f"Input file does not exist: {path}"
        )

    records = load_jsonl(path)

    capability_counts = Counter()
    difficulty_counts = Counter()

    multi_capability = 0

    for record in records:
        capabilities = record["capabilities_manual"]

        for capability in capabilities:
            capability_counts[capability] += 1

        if len(capabilities) >= 2:
            multi_capability += 1

        difficulty_counts[
            record["difficulty_manual"]
        ] += 1

    print()
    print("=== Manual Annotation Statistics ===")
    print()

    print(f"Total = {len(records)}")
    print()

    print("Capability:")

    for capability in CAPABILITIES:
        count = capability_counts[capability]

        percentage = (
            count / len(records) * 100
            if records
            else 0
        )

        print(
            f"{capability:<15}"
            f"{count:>4} "
            f"({percentage:>5.1f}%)"
        )

    print()

    print(
        f"Multi-capability = "
        f"{multi_capability}"
    )

    print()

    print("Difficulty:")

    for difficulty in DIFFICULTIES:
        print(
            f"{difficulty:<10}"
            f"{difficulty_counts[difficulty]:>4}"
        )

    print()


if __name__ == "__main__":
    main()