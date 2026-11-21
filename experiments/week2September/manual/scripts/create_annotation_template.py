import json
from pathlib import Path


BASE = Path(__file__).resolve().parents[2]

INPUT_FILE = (
    BASE
    / "manual"
    / "data"
    / "pilot"
    / "pilot_30.jsonl"
)

OUTPUT_FILE = (
    BASE
    / "manual"
    / "data"
    / "pilot"
    / "pilot_30_annotations.jsonl"
)


def load_jsonl(path):
    with path.open("r", encoding="utf-8") as f:
        return [
            json.loads(line)
            for line in f
            if line.strip()
        ]


def main():

    records = load_jsonl(INPUT_FILE)

    print(f"Pilot records: {len(records)}")

    if len(records) != 30:
        raise RuntimeError(
            f"Expected exactly 30 pilot records, "
            f"got {len(records)}."
        )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8"
    ) as f:

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
    print(f"Annotations: {len(records)}")


if __name__ == "__main__":
    main()