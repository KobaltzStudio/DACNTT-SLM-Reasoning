import json
from pathlib import Path


BASE = Path(__file__).resolve().parents[2]

PILOT_FILE = (
    BASE
    / "manual"
    / "data"
    / "pilot"
    / "pilot_30_annotations.jsonl"
)

PARTIAL_FILE = (
    BASE
    / "manual"
    / "data"
    / "batch_100"
    / "batch_100_annotations_partial.jsonl"
)

OUTPUT_FILE = (
    BASE
    / "manual"
    / "data"
    / "batch_100"
    / "batch_100_annotations.jsonl"
)


def load_jsonl(path):
    records = []

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    return records


def main():
    pilot = load_jsonl(PILOT_FILE)
    partial = load_jsonl(PARTIAL_FILE)

    print(f"Pilot annotations: {len(pilot)}")
    print(f"New annotations: {len(partial)}")

    records = pilot + partial

    ids = [record["problem_id"] for record in records]

    if len(ids) != len(set(ids)):
        duplicates = sorted(
            problem_id
            for problem_id, count in __import__("collections")
            .Counter(ids).items()
            if count > 1
        )

        raise RuntimeError(
            f"Duplicate problem_id detected: {duplicates}"
        )

    if len(records) != 100:
        raise RuntimeError(
            f"Expected 100 annotations, got {len(records)}."
        )

    expected_ids = {
        f"gsm8k_train_{i:05d}"
        for i in range(100)
    }

    actual_ids = set(ids)

    missing = expected_ids - actual_ids
    extra = actual_ids - expected_ids

    if missing:
        raise RuntimeError(
            f"Missing IDs: {sorted(missing)}"
        )

    if extra:
        raise RuntimeError(
            f"Unexpected IDs: {sorted(extra)}"
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
            f.write(
                json.dumps(
                    record,
                    ensure_ascii=False
                )
                + "\n"
            )

    print(f"Created: {OUTPUT_FILE}")
    print(f"Total annotations: {len(records)}")


if __name__ == "__main__":
    main()