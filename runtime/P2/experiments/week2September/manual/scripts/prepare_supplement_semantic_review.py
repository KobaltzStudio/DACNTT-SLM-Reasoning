
from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

ANNOTATION_FILE = (
    ROOT / "data/supplement/supplement_annotations_v2.jsonl"
)

RAW_FILE = (
    ROOT / "data/raw/supplement_annotations.jsonl"
)

OUTPUT_FILE = (
    ROOT / "reports/capability/d3_audit/semantic_review_85.csv"
)


def load_jsonl(path: Path) -> dict[str, dict]:
    records = {}

    with path.open("r", encoding="utf-8-sig") as f:
        for line_no, line in enumerate(f, start=1):
            if not line.strip():
                continue

            record = json.loads(line)
            problem_id = str(record["problem_id"]).strip()

            if problem_id in records:
                raise ValueError(
                    f"Duplicate problem_id {problem_id} in {path}"
                )

            records[problem_id] = record

    return records


def main() -> None:
    annotations = load_jsonl(ANNOTATION_FILE)
    raw_records = load_jsonl(RAW_FILE)

    missing_ids = set(annotations) - set(raw_records)

    if missing_ids:
        raise ValueError(
            f"Missing raw problem records: {sorted(missing_ids)}"
        )

    rows = []

    for problem_id, annotation in sorted(annotations.items()):
        raw = raw_records[problem_id]

        rows.append({
            "problem_id": problem_id,
            "question": raw.get("question", ""),
            "ground_truth": raw.get("ground_truth", ""),
            "original_labels": json.dumps(
                annotation.get("capabilities_manual", []),
                ensure_ascii=False,
            ),
            "original_difficulty": annotation.get(
                "difficulty_manual", ""
            ),
            "original_notes": annotation.get("notes", ""),
            "annotator_id": annotation.get("annotator_id", ""),
            "semantic_status": "pending",
            "reviewed_labels": "",
            "issue_type": "",
            "review_rationale": "",
            "reviewer": "",
        })

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        fieldnames = list(rows[0].keys())

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(rows)

    print("SEMANTIC REVIEW WORKSHEET")
    print("-" * 60)
    print("Annotation records:", len(annotations))
    print("Matched raw records:", len(raw_records))
    print("Worksheet rows:", len(rows))
    print("Initial status: pending")
    print("Output:", OUTPUT_FILE)


if __name__ == "__main__":
    main()
