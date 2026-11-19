import json
from pathlib import Path


BASE = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    BASE
    / "data"
    / "pilot"
    / "pilot_30.jsonl"
)

OUTPUT_FILE = (
    BASE
    / "data"
    / "pilot"
    / "pilot_30_annotations_A2.jsonl"
)


def load_jsonl(path):
    records = []

    with path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            if not line.strip():
                continue

            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"Invalid JSON at line {line_number}: {error}"
                )

    return records


def main():
    problems = load_jsonl(INPUT_FILE)

    if len(problems) != 30:
        raise ValueError(
            f"Expected 30 pilot problems, got {len(problems)}"
        )

    output_records = []

    for problem in problems:
        problem_id = problem["problem_id"]

        output_records.append(
            {
                "problem_id": problem_id,
                "capabilities_manual": [],
                "difficulty_manual": "",
                "notes": "",
                "annotator_id": "A2",
                "schema_version": "v1"
            }
        )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8"
    ) as f:
        for record in output_records:
            f.write(
                json.dumps(
                    record,
                    ensure_ascii=False
                )
                + "\n"
            )

    print(
        f"Created A2 template: {OUTPUT_FILE}"
    )

    print(
        f"Records: {len(output_records)}"
    )

    print(
        "IMPORTANT: capabilities_manual and difficulty_manual "
        "must be completed manually before validation."
    )


if __name__ == "__main__":
    main()