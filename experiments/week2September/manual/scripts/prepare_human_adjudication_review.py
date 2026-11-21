import csv
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
AUDIT_DIR = BASE / "reports" / "capability" / "d3_audit"

AI_FILE = AUDIT_DIR / "adjudication_final_ai.csv"
EVIDENCE_FILE = AUDIT_DIR / "adjudication_evidence.csv"
OUTPUT_FILE = AUDIT_DIR / "adjudication_human_review.csv"

HUMAN_FIELDS = [
    "human_review_status",
    "human_confirmed_capabilities",
    "human_confirmed_difficulty",
    "human_reviewer",
    "human_review_notes",
]


def read_csv(path):
    if not path.exists():
        raise FileNotFoundError(path)

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f"CSV has no header: {path}")
        return reader.fieldnames, list(reader)


def main():
    ai_headers, ai_rows = read_csv(AI_FILE)
    evidence_headers, evidence_rows = read_csv(EVIDENCE_FILE)

    if "problem_id" not in ai_headers:
        raise ValueError("AI adjudication CSV has no problem_id column")

    if "problem_id" not in evidence_headers:
        raise ValueError("Evidence CSV has no problem_id column")

    if len(ai_rows) != 22:
        raise ValueError(
            f"Expected 22 AI decisions, found {len(ai_rows)}"
        )

    ai_ids = [row["problem_id"] for row in ai_rows]
    if len(ai_ids) != len(set(ai_ids)):
        raise ValueError("Duplicate problem_id in AI adjudication CSV")

    evidence_by_id = {}
    for row in evidence_rows:
        problem_id = row["problem_id"]
        if problem_id in evidence_by_id:
            raise ValueError(
                f"Duplicate evidence record: {problem_id}"
            )
        evidence_by_id[problem_id] = row

    missing = sorted(set(ai_ids) - set(evidence_by_id))
    if missing:
        raise ValueError(
            f"Missing evidence for adjudication IDs: {missing}"
        )

    evidence_extra_headers = [
        f"evidence_{name}"
        for name in evidence_headers
        if name != "problem_id" and name not in ai_headers
    ]

    output_headers = (
        ai_headers
        + evidence_extra_headers
        + [field for field in HUMAN_FIELDS if field not in ai_headers]
    )

    output_rows = []

    for ai_row in ai_rows:
        problem_id = ai_row["problem_id"]
        evidence = evidence_by_id[problem_id]

        row = dict(ai_row)

        for name in evidence_headers:
            if name == "problem_id" or name in ai_headers:
                continue
            row[f"evidence_{name}"] = evidence[name]

        row["human_review_status"] = "PENDING"
        row["human_confirmed_capabilities"] = ""
        row["human_confirmed_difficulty"] = ""
        row["human_reviewer"] = ""
        row["human_review_notes"] = ""

        output_rows.append(row)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_FILE.open(
        "w", encoding="utf-8-sig", newline=""
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=output_headers,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(output_rows)

    print("HUMAN ADJUDICATION REVIEW SHEET")
    print(f"AI decisions: {len(ai_rows)}")
    print(f"Evidence records: {len(evidence_rows)}")
    print(f"Review rows: {len(output_rows)}")
    print(f"Output: {OUTPUT_FILE}")
    print("[PASS]")


if __name__ == "__main__":
    main()
