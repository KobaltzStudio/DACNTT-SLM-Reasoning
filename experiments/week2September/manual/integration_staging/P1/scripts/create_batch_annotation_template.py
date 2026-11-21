import json
from pathlib import Path


BASE = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    BASE
    / "manual"
    / "data"
    / "batch_100"
    / "batch_100.jsonl"
)

OUTPUT_FILE = (
    BASE
    / "manual"
    / "data"
    / "batch_100"
    / "batch_100_annotations_partial.jsonl"
)


def load_jsonl(path):
    records = []

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    return records


def main():

    records = load_jsonl(INPUT_FILE)

    records = [
        record
        for record in records
        if int(record["problem_id"].split("_")[-1]) >= 30
    ]

    print(f"Records for manual annotation: {len(records)}")

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:

        for record in records:

            annotation = {
                "problem_id": record["problem_id"],
                "capabilities_manual": [],
                "difficulty_manual": "",
                "notes": "",
                "annotator_id": "A1",
                "schema_version": "v1"
            }

            f.write(
                json.dumps(
                    annotation,
                    ensure_ascii=False
                )
                + "\n"
            )

    print(f"Created: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()