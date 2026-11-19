import csv
import json
from pathlib import Path

ROOT = Path(".")
QUEUE_PATH = ROOT / "reports/capability/d3_audit/adjudication_working.csv"
RAW_PATH = ROOT / "data/raw/gsm8k_train.jsonl"
OUTPUT_PATH = ROOT / "reports/capability/d3_audit/adjudication_evidence.csv"

def read_jsonl(path):
    records = {}

    with path.open("r", encoding="utf-8-sig") as f:
        for line_number, line in enumerate(f, start=1):
            if not line.strip():
                continue

            record = json.loads(line)
            problem_id = record.get("problem_id")

            if not problem_id:
                raise ValueError(
                    f"Missing problem_id at {path}:{line_number}"
                )

            if problem_id in records:
                raise ValueError(
                    f"Duplicate raw problem_id: {problem_id}"
                )

            records[problem_id] = record

    return records


def main():
    if not QUEUE_PATH.exists():
        raise FileNotFoundError(QUEUE_PATH)

    if not RAW_PATH.exists():
        raise FileNotFoundError(RAW_PATH)

    with QUEUE_PATH.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:
        queue = list(csv.DictReader(f))

    if len(queue) != 22:
        raise ValueError(
            f"Expected 22 adjudication records, got {len(queue)}"
        )

    raw_records = read_jsonl(RAW_PATH)

    output_rows = []
    missing_ids = []
    question_mismatches = []

    for row in queue:
        problem_id = row["problem_id"]

        raw = raw_records.get(problem_id)

        if raw is None:
            missing_ids.append(problem_id)
            continue

        queue_question = row.get("question", "").strip()
        raw_question = raw.get("question", "").strip()

        if queue_question != raw_question:
            question_mismatches.append(problem_id)

        output = dict(row)

        output["raw_question"] = raw_question
        output["raw_ground_truth"] = raw.get("ground_truth", "")
        output["source_index"] = raw.get("source_index", "")
        output["question_matches_raw"] = (
            str(queue_question == raw_question).lower()
        )

        output_rows.append(output)

    if missing_ids:
        raise ValueError(
            "Missing raw records: " + ", ".join(missing_ids)
        )

    if question_mismatches:
        raise ValueError(
            "Question mismatch: " + ", ".join(question_mismatches)
        )

    if len(output_rows) != 22:
        raise ValueError(
            f"Expected 22 evidence rows, got {len(output_rows)}"
        )

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    columns = list(output_rows[0].keys())

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=columns
        )
        writer.writeheader()
        writer.writerows(output_rows)

    print("D3 ADJUDICATION EVIDENCE: PASS")
    print("Queue records:", len(queue))
    print("Matched raw records:", len(output_rows))
    print("Missing IDs:", len(missing_ids))
    print("Question mismatches:", len(question_mismatches))
    print("Output:", OUTPUT_PATH)


if __name__ == "__main__":
    main()
