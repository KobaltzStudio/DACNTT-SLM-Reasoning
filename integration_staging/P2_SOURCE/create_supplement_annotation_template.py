import json
import sys
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


def load_jsonl(path):
    records = []

    with path.open(
        "r",
        encoding="utf-8"
    ) as f:

        for line in f:

            line = line.strip()

            if line:
                records.append(
                    json.loads(line)
                )

    return records


def main():

    if len(sys.argv) != 3:

        print(
            "Usage:\n"
            "python create_supplement_annotation_template.py "
            "<selected.jsonl> "
            "<annotations.jsonl>"
        )

        sys.exit(1)

    input_path = Path(
        sys.argv[1]
    )

    output_path = Path(
        sys.argv[2]
    )

    records = load_jsonl(
        input_path
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with output_path.open(
        "w",
        encoding="utf-8"
    ) as f:

        for record in records:

            annotation = {
                "problem_id": record["problem_id"],
                "question": record["question"],
                "ground_truth": record.get(
                    "ground_truth",
                    ""
                ),
                "capabilities_manual": [],
                "difficulty_manual": "",
                "notes": "",
            }

            f.write(
                json.dumps(
                    annotation,
                    ensure_ascii=False
                )
                + "\n"
            )

    print(
        f"Input records: {len(records)}"
    )

    print(
        f"Annotation template written to:"
    )

    print(
        f"  {output_path}"
    )

    print()
    print(
        "Annotate capabilities according to "
        "guideline_v2.md."
    )

    print(
        "Do NOT copy candidate_types into "
        "capabilities_manual."
    )


if __name__ == "__main__":
    main()