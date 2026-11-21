import json
import sys
from collections import Counter
from pathlib import Path


BASE = Path(__file__).resolve().parents[1]


CAPABILITIES = [
    "addition",
    "subtraction",
    "multiplication",
    "division",
    "percentage",
    "fraction",
    "ratio",
]


TARGETS = {
    "percentage": 25,
    "fraction": 30,
    "ratio": 10,
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


def count_capabilities(records):
    counts = Counter()

    for record in records:
        capabilities = record.get(
            "capabilities_manual"
        )

        if not isinstance(
            capabilities,
            list,
        ):
            raise ValueError(
                f"{record.get('problem_id')}: "
                "capabilities_manual must be a list."
            )

        for capability in capabilities:
            if capability not in CAPABILITIES:
                raise ValueError(
                    f"{record.get('problem_id')}: "
                    f"unknown capability "
                    f"{capability!r}"
                )

            counts[capability] += 1

    return counts


def main():
    if len(sys.argv) != 3:
        print(
            "Usage:\n"
            "python report_capability_coverage.py "
            "<batch_annotations.jsonl> "
            "<supplement_annotations.jsonl>"
        )
        sys.exit(1)

    batch_path = Path(sys.argv[1])
    supplement_path = Path(sys.argv[2])

    batch = load_jsonl(
        batch_path
    )

    supplement = load_jsonl(
        supplement_path
    )

    batch_counts = count_capabilities(
        batch
    )

    supplement_counts = count_capabilities(
        supplement
    )

    final_counts = (
        batch_counts
        + supplement_counts
    )

    print(
        f"Batch records: {len(batch)}"
    )

    print(
        f"Supplement records: "
        f"{len(supplement)}"
    )

    print(
        f"Final records: "
        f"{len(batch) + len(supplement)}"
    )

    print()

    print(
        f"{'Capability':<16}"
        f"{'Batch':>8}"
        f"{'Supplement':>12}"
        f"{'Final':>8}"
        f"{'Target':>10}"
        f"{'Status':>10}"
    )

    print("-" * 66)

    for capability in CAPABILITIES:
        batch_count = batch_counts[
            capability
        ]

        supplement_count = supplement_counts[
            capability
        ]

        final_count = final_counts[
            capability
        ]

        target = TARGETS.get(
            capability
        )

        if target is None:
            status = "INFO"
            target_text = "-"
        else:
            target_text = str(target)

            if final_count >= target:
                status = "PASS"
            else:
                status = "BELOW"

        print(
            f"{capability:<16}"
            f"{batch_count:>8}"
            f"{supplement_count:>12}"
            f"{final_count:>8}"
            f"{target_text:>10}"
            f"{status:>10}"
        )

    print()
    print(
        "Coverage interpretation:"
    )

    print(
        "- Target values are sampling targets, "
        "not scientific validity thresholds."
    )

    print(
        "- Capability labels must still be "
        "assigned from the guideline."
    )

    print(
        "- Candidate filtering must not use "
        "ground-truth capability labels."
    )


if __name__ == "__main__":
    main()