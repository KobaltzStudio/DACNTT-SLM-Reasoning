import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

SEMANTIC_REVIEW = (
    ROOT / "reports/capability/d3_audit/semantic_review_85.csv"
)
A1_FILE = ROOT / "data/annotation/a1_supplement_agreement_25.jsonl"
A2_FILE = ROOT / "data/annotation/a2_supplement_annotations.jsonl"
AGREEMENT_FILE = (
    ROOT / "reports/capability/d3_audit/agreement_supplement_25.json"
)

OUTPUT_FILE = (
    ROOT / "reports/capability/d3_audit/adjudication_queue.csv"
)


def read_jsonl(path):
    if not path.exists():
        raise FileNotFoundError(path)

    records = []
    with path.open("r", encoding="utf-8-sig") as f:
        for line_number, line in enumerate(f, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON at {path}:{line_number}: {exc}"
                ) from exc

            if not isinstance(record, dict):
                raise ValueError(
                    f"Expected JSON object at {path}:{line_number}"
                )
            records.append(record)

    return records


def parse_label_list(value, problem_id, field):
    try:
        labels = json.loads(value)
    except Exception as exc:
        raise ValueError(
            f"{problem_id}: invalid JSON in {field}: {value!r}"
        ) from exc

    if not isinstance(labels, list):
        raise ValueError(
            f"{problem_id}: {field} must be a JSON list"
        )

    return labels


def label_text(labels):
    if labels is None:
        return ""
    return json.dumps(
        sorted(labels),
        ensure_ascii=False,
    )


def main():
    required_files = [
        SEMANTIC_REVIEW,
        A1_FILE,
        A2_FILE,
        AGREEMENT_FILE,
    ]

    for path in required_files:
        if not path.exists():
            raise FileNotFoundError(
                f"Required input does not exist: {path}"
            )

    with SEMANTIC_REVIEW.open(
        "r", encoding="utf-8-sig", newline=""
    ) as f:
        reader = csv.DictReader(f)
        semantic_rows = list(reader)
        semantic_columns = reader.fieldnames or []

    required_columns = {
        "problem_id",
        "question",
        "original_labels",
        "original_difficulty",
        "semantic_status",
        "reviewed_labels",
        "issue_type",
        "review_rationale",
    }

    missing_columns = required_columns - set(semantic_columns)
    if missing_columns:
        raise ValueError(
            f"Semantic review missing columns: {sorted(missing_columns)}"
        )

    semantic_by_id = {}
    for row in semantic_rows:
        pid = row["problem_id"]
        if not pid:
            raise ValueError("Semantic review contains empty problem_id")
        if pid in semantic_by_id:
            raise ValueError(f"Duplicate semantic review ID: {pid}")
        semantic_by_id[pid] = row

    a1_records = read_jsonl(A1_FILE)
    a2_records = read_jsonl(A2_FILE)

    def index_records(records, name):
        result = {}
        for row in records:
            pid = row.get("problem_id")
            if not pid:
                raise ValueError(f"{name}: record without problem_id")
            if pid in result:
                raise ValueError(f"{name}: duplicate problem_id {pid}")
            result[pid] = row
        return result

    a1 = index_records(a1_records, "A1")
    a2 = index_records(a2_records, "A2")

    agreement = json.loads(
        AGREEMENT_FILE.read_text(encoding="utf-8-sig")
    )

    if agreement.get("n_records") != len(a1):
        raise ValueError(
            "Agreement report record count does not match A1 subset"
        )

    if set(a1) != set(a2):
        raise ValueError("A1/A2 IDs do not match")

    disagreement_by_id = {
        row["problem_id"]: row
        for row in agreement.get("disagreements", [])
    }

    queue = []

    for pid, semantic in semantic_by_id.items():
        issue_type = (semantic.get("issue_type") or "").strip()
        disagreement = disagreement_by_id.get(pid)

        reasons = []

        if issue_type:
            reasons.append("A1_SEMANTIC_REVIEW")

        if disagreement:
            if disagreement.get("capability_disagreements"):
                reasons.append("A1_A2_CAPABILITY_DISAGREEMENT")
            if (
                disagreement.get("difficulty_A1")
                != disagreement.get("difficulty_A2")
            ):
                reasons.append("A1_A2_DIFFICULTY_DISAGREEMENT")

        if not reasons:
            continue

        a1_record = a1.get(pid, {})
        a2_record = a2.get(pid, {})

        original_labels = parse_label_list(
            semantic["original_labels"], pid, "original_labels"
        )
        reviewed_labels = parse_label_list(
            semantic["reviewed_labels"], pid, "reviewed_labels"
        )

        a1_original = a1_record.get("capabilities_manual", [])
        a2_labels = a2_record.get("capabilities_manual", [])

        capability_disagreements = sorted(
            set(a1_original).symmetric_difference(set(a2_labels))
        )

        queue.append({
            "problem_id": pid,
            "question": semantic.get("question", ""),
            "queue_reasons": ";".join(reasons),
            "semantic_issue_type": issue_type,
            "A1_original_labels": label_text(original_labels),
            "A1_reviewed_labels": label_text(reviewed_labels),
            "A2_labels": label_text(a2_labels) if a2_record else "",
            "A1_difficulty": (
                a1_record.get("difficulty_manual")
                or semantic.get("original_difficulty", "")
            ),
            "A2_difficulty": a2_record.get("difficulty_manual", ""),
            "capability_disagreements": label_text(
                capability_disagreements
            ),
            "A1_review_rationale": semantic.get(
                "review_rationale", ""
            ),
            "adjudication_status": "pending",
            "final_labels": "",
            "final_difficulty": "",
            "adjudication_rationale": "",
            "reviewer": "",
        })

    queue.sort(key=lambda row: row["problem_id"])

    output_columns = [
        "problem_id",
        "question",
        "queue_reasons",
        "semantic_issue_type",
        "A1_original_labels",
        "A1_reviewed_labels",
        "A2_labels",
        "A1_difficulty",
        "A2_difficulty",
        "capability_disagreements",
        "A1_review_rationale",
        "adjudication_status",
        "final_labels",
        "final_difficulty",
        "adjudication_rationale",
        "reviewer",
    ]

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_FILE.open(
        "w", encoding="utf-8-sig", newline=""
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=output_columns,
        )
        writer.writeheader()
        writer.writerows(queue)

    semantic_issue_count = sum(
        bool((row.get("issue_type") or "").strip())
        for row in semantic_rows
    )

    print("D3 ADJUDICATION QUEUE: PASS")
    print(f"Semantic review records: {len(semantic_rows)}")
    print(f"A1/A2 agreement records: {len(a1_records)}")
    print(f"A1/A2 disagreement records: {len(disagreement_by_id)}")
    print(f"A1 semantic issue records: {semantic_issue_count}")
    print(f"Unique adjudication cases: {len(queue)}")
    print("All adjudication statuses: pending")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
