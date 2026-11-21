from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path


REPO = Path(r"C:\KLTN-SLM-Reasoning")

PATHS = {
    "batch": REPO / "data/gold_vfinal/batch_100_annotations_vfinal.jsonl",
    "supplement": REPO / "data/gold_vfinal/supplement_annotations_vfinal.jsonl",
    "gold_manifest": REPO / "data/gold_vfinal/gold_vfinal_manifest.json",
    "raw_train": REPO / "data/raw/gsm8k_train.jsonl",
    "supplement_raw": REPO / "data/raw/supplement_selected.jsonl",
    "worklist": (
        REPO / "experiments/week2September/manual/data/gold"
        / "review_2026-11-15/adjudication_worklist_63_pending.csv"
    ),
    "queue": (
        REPO / "experiments/week2September/manual/reports/capability"
        / "p1_gold_audit_2026-11-14/gold_review_queue.csv"
    ),
    "human_confirmed": (
        REPO / "experiments/week2September/manual/reports/capability"
        / "d3_audit/adjudication_human_confirmed.csv"
    ),
    "schema_inspection": (
        REPO / "experiments/week2September/manual/reports/gold"
        / "review_2026-11-15/gold_source_schema_inspection.json"
    ),
}

REPORT_DIR = (
    REPO / "experiments/week2September/manual/reports/gold"
    / "review_2026-11-16"
)

CANDIDATE_DIR = REPO / "data/gold_vnext_candidate_2026-11-16"

EXPECTED_FIELDS = {
    "problem_id",
    "capabilities_manual",
    "difficulty_manual",
    "notes",
    "annotator_id",
    "schema_version",
}

ALLOWED_CAPABILITIES = {
    "addition",
    "subtraction",
    "multiplication",
    "division",
    "fraction",
    "percentage",
    "ratio",
}

ALLOWED_DIFFICULTIES = {"easy", "medium", "hard"}


def read_jsonl(path):
    if not path.is_file():
        raise FileNotFoundError(path)

    rows = []
    with path.open("r", encoding="utf-8-sig") as f:
        for line_number, line in enumerate(f, start=1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSONL at {path}:{line_number}: {exc}"
                )
    return rows


def read_csv(path):
    if not path.is_file():
        raise FileNotFoundError(path)

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def read_json(path):
    if not path.is_file():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def unique_ids(rows, name):
    ids = [row["problem_id"] for row in rows]

    if len(ids) != len(set(ids)):
        raise ValueError(f"{name}: duplicate problem_id detected.")

    return set(ids)


def check(condition, name, detail, results):
    results.append({
        "name": name,
        "passed": bool(condition),
        "detail": str(detail),
    })


def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    missing = [str(p) for p in PATHS.values() if not p.is_file()]
    if missing:
        raise FileNotFoundError(
            "Missing required source files:\n" + "\n".join(missing)
        )

    batch = read_jsonl(PATHS["batch"])
    supplement = read_jsonl(PATHS["supplement"])
    raw_train = read_jsonl(PATHS["raw_train"])
    supplement_raw = read_jsonl(PATHS["supplement_raw"])

    worklist = read_csv(PATHS["worklist"])
    queue = read_csv(PATHS["queue"])
    human = read_csv(PATHS["human_confirmed"])

    manifest = read_json(PATHS["gold_manifest"])
    schema = read_json(PATHS["schema_inspection"])

    batch_ids = unique_ids(batch, "batch")
    supplement_ids = unique_ids(supplement, "supplement")
    raw_ids = unique_ids(raw_train, "raw_train")
    supplement_raw_ids = unique_ids(supplement_raw, "supplement_raw")
    worklist_ids = unique_ids(worklist, "worklist")
    human_ids = unique_ids(human, "human_confirmed")

    queue_ids = unique_ids(queue, "gold_review_queue")

    checks = []

    check(len(batch) == 100, "batch_count", len(batch), checks)
    check(len(supplement) == 85, "supplement_count", len(supplement), checks)
    check(
        len(batch_ids | supplement_ids) == 185,
        "gold_unique_ids",
        len(batch_ids | supplement_ids),
        checks,
    )
    check(
        not (batch_ids & supplement_ids),
        "batch_supplement_disjoint",
        f"overlap={len(batch_ids & supplement_ids)}",
        checks,
    )
    check(
        len(worklist) == 63 and len(worklist_ids) == 63,
        "pending_worklist",
        f"rows={len(worklist)}, unique={len(worklist_ids)}",
        checks,
    )
    check(
        worklist_ids <= supplement_ids,
        "worklist_in_supplement_gold",
        f"missing={sorted(worklist_ids - supplement_ids)}",
        checks,
    )
    check(
        len(human) == 22 and len(human_ids) == 22,
        "human_confirmed_count",
        f"rows={len(human)}, unique={len(human_ids)}",
        checks,
    )
    check(
        human_ids <= supplement_ids,
        "human_confirmed_in_supplement",
        f"missing={sorted(human_ids - supplement_ids)}",
        checks,
    )
    check(
        not (human_ids & worklist_ids),
        "human_confirmed_pending_disjoint",
        f"overlap={len(human_ids & worklist_ids)}",
        checks,
    )
    check(
        len(queue) == 185 and len(queue_ids) == 185,
        "queue_count",
        f"rows={len(queue)}, unique={len(queue_ids)}",
        checks,
    )

    status_counts = Counter(row["queue_status"] for row in queue)
    split_counts = Counter(row["split"] for row in queue)

    check(
        status_counts == {
            "excluded": 100,
            "pending": 63,
            "confirmed": 22,
        },
        "queue_status_counts",
        dict(status_counts),
        checks,
    )
    check(
        split_counts == {"D_pool": 100, "D_dev": 85},
        "split_counts",
        dict(split_counts),
        checks,
    )

    raw_by_id = {row["problem_id"]: row for row in raw_train}
    supplement_raw_by_id = {
        row["problem_id"]: row for row in supplement_raw
    }

    question_mismatches = []
    answer_mismatches = []
    missing_raw = []

    for pid in worklist_ids:
        raw = raw_by_id.get(pid)
        sup = supplement_raw_by_id.get(pid)

        if raw is None or sup is None:
            missing_raw.append(pid)
            continue

        if raw["question"] != sup["question"]:
            question_mismatches.append(pid)

        if str(raw["ground_truth"]) != str(sup["ground_truth"]):
            answer_mismatches.append(pid)

    check(
        not missing_raw,
        "pending_ids_in_raw_sources",
        f"missing={missing_raw}",
        checks,
    )
    check(
        not question_mismatches,
        "pending_question_consistency",
        f"mismatches={question_mismatches}",
        checks,
    )
    check(
        not answer_mismatches,
        "pending_answer_consistency",
        f"mismatches={answer_mismatches}",
        checks,
    )

    schema_errors = []
    for name, rows in [("batch", batch), ("supplement", supplement)]:
        for row in rows:
            if set(row.keys()) != EXPECTED_FIELDS:
                schema_errors.append(
                    f"{name}:{row.get('problem_id')} fields={sorted(row.keys())}"
                )
                continue

            if row["schema_version"] != "v1":
                schema_errors.append(
                    f"{name}:{row['problem_id']} schema_version"
                )

            if not set(row["capabilities_manual"]) <= ALLOWED_CAPABILITIES:
                schema_errors.append(
                    f"{name}:{row['problem_id']} invalid capabilities"
                )

            if row["difficulty_manual"] not in ALLOWED_DIFFICULTIES:
                schema_errors.append(
                    f"{name}:{row['problem_id']} invalid difficulty"
                )

    check(
        not schema_errors,
        "gold_v1_schema",
        f"errors={schema_errors[:10]}",
        checks,
    )

    # Compare the source files against the previously recorded inspection.
    source_hash_results = {}
    source_hash_map = {
        "batch": "gold_batch",
        "supplement": "gold_supplement",
        "gold_manifest": "gold_manifest",
    }

    for key, schema_key in source_hash_map.items():
        expected = (
            schema.get("source_hashes", {})
            .get(schema_key, {})
            .get("actual_sha256")
        )
        actual = sha256(PATHS[key])
        source_hash_results[key] = {
            "expected": expected,
            "actual": actual,
            "matches": expected == actual if expected else None,
        }

    hash_mismatches = [
        key for key, value in source_hash_results.items()
        if value["matches"] is False
    ]

    check(
        not hash_mismatches,
        "source_hashes",
        source_hash_results,
        checks,
    )

    candidate_available = not CANDIDATE_DIR.exists()
    check(
        candidate_available,
        "dated_candidate_directory_available",
        str(CANDIDATE_DIR),
        checks,
    )

    passed = all(item["passed"] for item in checks)

    report = {
        "review_date": "2026-11-16",
        "preflight_passed": passed,
        "source_manifest": manifest,
        "counts": {
            "batch": len(batch),
            "supplement": len(supplement),
            "gold_total": len(batch_ids | supplement_ids),
            "pending_worklist": len(worklist),
            "human_confirmed": len(human),
            "queue": len(queue),
            "raw_train": len(raw_train),
            "supplement_raw": len(supplement_raw),
        },
        "queue_status_counts": dict(status_counts),
        "split_counts": dict(split_counts),
        "source_hashes": source_hash_results,
        "candidate_directory": str(CANDIDATE_DIR),
        "checks": checks,
    }

    json_path = REPORT_DIR / "gold_vnext_preflight_2026-11-16.json"
    md_path = REPORT_DIR / "gold_vnext_preflight_2026-11-16.md"

    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = [
        "# Gold vNext Preflight — 2026-11-16",
        "",
        f"- Overall: **{'PASS' if passed else 'FAIL'}**",
        f"- Gold records: **{len(batch_ids | supplement_ids)}**",
        f"- Pending D_dev: **{len(worklist)}**",
        f"- Human-confirmed: **{len(human)}**",
        f"- Candidate directory: `{CANDIDATE_DIR}`",
        "",
        "## Checks",
        "",
    ]

    for item in checks:
        status = "PASS" if item["passed"] else "FAIL"
        lines.append(f"- **{status}** `{item['name']}`: {item['detail']}")

    lines += [
        "",
        "## Safety",
        "",
        "- Gold vFinal source files were read only.",
        "- No Gold vNext candidate was written.",
        "- No original worklist was modified.",
        "",
    ]

    md_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"Preflight: {'PASS' if passed else 'FAIL'}")
    print(f"Gold batch: {len(batch)}")
    print(f"Gold supplement: {len(supplement)}")
    print(f"Gold total: {len(batch_ids | supplement_ids)}")
    print(f"Pending worklist: {len(worklist)}")
    print(f"Human confirmed: {len(human)}")
    print(f"Candidate directory available: {candidate_available}")
    print(f"JSON report: {json_path}")
    print(f"Markdown report: {md_path}")
    print("Gold vFinal: unchanged")

    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
