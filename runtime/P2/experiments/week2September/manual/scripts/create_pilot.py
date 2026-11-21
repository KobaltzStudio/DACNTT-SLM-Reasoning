import argparse
import json
from pathlib import Path


BASE = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    BASE
    / "processed"
    / "baseline_with_difficulty_100.jsonl"
)

DEFAULT_OUTPUT_DIR = (
    BASE
    / "manual"
    / "data"
    / "pilot"
)


def load_jsonl(path):
    with path.open(
        "r",
        encoding="utf-8"
    ) as f:

        return [
            json.loads(line)
            for line in f
            if line.strip()
        ]


def create_batch(
    records,
    size,
    output_file
):

    if size <= 0:
        raise ValueError(
            "Size must be greater than 0."
        )

    if len(records) < size:
        raise RuntimeError(
            f"Baseline contains only "
            f"{len(records)} records, "
            f"but {size} requested."
        )

    selected = records[:size]

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with output_file.open(
        "w",
        encoding="utf-8"
    ) as f:

        for record in selected:

            output = {
                "problem_id":
                    record["id"],

                "question":
                    record["question"],

                "ground_truth":
                    record["ground_truth"]
            }

            f.write(
                json.dumps(
                    output,
                    ensure_ascii=False
                )
                + "\n"
            )

    print(
        f"Created: {output_file}"
    )

    print(
        f"Problems: {len(selected)}"
    )


def main():

    parser = argparse.ArgumentParser(
        description=(
            "Create a manual annotation "
            "batch from the baseline dataset."
        )
    )

    parser.add_argument(
        "--size",
        type=int,
        default=30,
        help=(
            "Number of problems to export "
            "(default: 30)"
        )
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "Output JSONL path. "
            "If omitted, an automatic filename "
            "is generated."
        )
    )

    args = parser.parse_args()

    records = load_jsonl(
        INPUT_FILE
    )

    print(
        f"Baseline records: {len(records)}"
    )

    if args.output is None:

        if args.size == 30:

            output_file = (
                DEFAULT_OUTPUT_DIR
                / "pilot_30.jsonl"
            )

        else:

            output_file = (
                BASE
                / "manual"
                / "data"
                / f"batch_{args.size}"
                / f"batch_{args.size}.jsonl"
            )

    else:

        output_file = args.output

    create_batch(
        records,
        args.size,
        output_file
    )


if __name__ == "__main__":
    main()