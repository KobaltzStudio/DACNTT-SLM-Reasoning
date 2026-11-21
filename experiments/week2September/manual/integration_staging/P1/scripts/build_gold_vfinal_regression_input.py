import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]

GOLD_FILES = [
    BASE / "data" / "gold_vfinal" / "batch_100_annotations_vfinal.jsonl",
    BASE / "data" / "gold_vfinal" / "supplement_annotations_vfinal.jsonl",
]

SOURCE_FILE = BASE / "data" / "raw" / "gsm8k_train.jsonl"

OUTPUT_FILE = (
    BASE / "reports" / "capability" / "d3_final_regression"
    / "gold_evaluation_input.jsonl"
)

CAPABILITIES = {
    "addition", "subtraction", "multiplication",
    "division", "percentage", "fraction", "ratio",
}


def read_jsonl(path):
    if not path.exists():
        raise FileNotFoundError(path)

    rows = []
    with path.open("r", encoding="utf-8-sig") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON at {path}:{line_no}"
                ) from exc
    return rows


def main():
    source_records = read_jsonl(SOURCE_FILE)
    source_by_id = {}

    for row in source_records:
        problem_id = row["problem_id"]
        if problem_id in source_by_id:
            raise ValueError(f"Duplicate raw source ID: {problem_id}")
        source_by_id[problem_id] = row

    gold_records = []
    for path in GOLD_FILES:
        gold_records.extend(read_jsonl(path))

    gold_ids = [row["problem_id"] for row in gold_records]

    if len(gold_ids) != len(set(gold_ids)):
        raise ValueError("Duplicate IDs across Gold vFinal files")

    if len(gold_records) != 185:
        raise ValueError(
            f"Expected 185 Gold records, got {len(gold_records)}"
        )

    output = []
    missing_source = []

    for gold in gold_records:
        problem_id = gold["problem_id"]
        source = source_by_id.get(problem_id)

        if source is None:
            missing_source.append(problem_id)
            continue

        question = source.get("question")
        if not isinstance(question, str) or not question.strip():
            raise ValueError(f"Missing question for {problem_id}")

        labels = gold.get("capabilities_manual")
        if not isinstance(labels, list):
            raise ValueError(
                f"capabilities_manual must be a list: {problem_id}"
            )

        labels = set(labels)
        unknown = labels - CAPABILITIES

        if unknown:
            raise ValueError(
                f"Unknown labels for {problem_id}: {sorted(unknown)}"
            )

        output.append({
            "problem_id": problem_id,
            "question": question,
            "gold_capabilities": sorted(labels),
        })

    if missing_source:
        raise ValueError(
            f"Missing raw source records: {missing_source[:10]}"
        )

    output_ids = [row["problem_id"] for row in output]

    if len(output) != 185:
        raise ValueError(f"Expected 185 output records, got {len(output)}")

    if len(output_ids) != len(set(output_ids)):
        raise ValueError("Duplicate IDs in evaluation input")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        for row in output:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print("D3 FINAL GOLD EVALUATION INPUT")
    print(f"Gold records: {len(gold_records)}")
    print(f"Output records: {len(output)}")
    print(f"Unique IDs: {len(set(output_ids))}")
    print(f"Missing source records: {len(missing_source)}")
    print(f"Output: {OUTPUT_FILE}")
    print("[PASS]")


if __name__ == "__main__":
    main()
