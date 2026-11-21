from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


MANUAL = Path(__file__).resolve().parents[1]

AUDIT_DIR = (
    MANUAL
    / "reports"
    / "capability"
    / "p1_gold_audit_2026-11-14"
)

OUTPUT_DIR = (
    MANUAL
    / "data"
    / "gold"
    / "review_2026-11-15"
)

REPORT_DIR = (
    MANUAL
    / "reports"
    / "gold"
    / "review_2026-11-15"
)

INVENTORY_PATH = AUDIT_DIR / "gold_inventory.json"
QUEUE_PATH = AUDIT_DIR / "gold_review_queue.csv"

SOURCE_PATHS = {
    "gold_batch": (
        MANUAL / "data/gold_vfinal/batch_100_annotations_vfinal.jsonl"
    ),
    "gold_supplement": (
        MANUAL / "data/gold_vfinal/supplement_annotations_vfinal.jsonl"
    ),
    "gold_manifest": (
        MANUAL / "data/gold_vfinal/gold_vfinal_manifest.json"
    ),
    "vnext_manifest": (
        MANUAL / "data/gold_vnext/gold_vnext_manifest.json"
    ),
    "vnext_batch": (
        MANUAL / "data/gold_vnext/batch_100_annotations_vnext.jsonl"
    ),
    "vnext_supplement": (
        MANUAL / "data/gold_vnext/supplement_annotations_vnext.jsonl"
    ),
    "split_manifest": (
        MANUAL / "splits/split_manifest.json"
    ),
    "human_confirmed": (
        MANUAL / "reports/capability/d3_audit/"
        "adjudication_human_confirmed.csv"
    ),
    "priority_error_review": (
        MANUAL / "reports/capability/d3_final_regression/"
        "priority_error_review_annotated.csv"
    ),
    "raw_train": (
        MANUAL / "data/raw/gsm8k_train.jsonl"
    ),
    "supplement_selected": (
        MANUAL / "data/raw/supplement_selected.jsonl"
    ),
    "ambiguous_cases": (
        MANUAL / "data/issues/ambiguous_cases_audited.jsonl"
    ),
}

ID_KEYS = ("problem_id", "id", "question_id", "uid")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def read_jsonl(path: Path) -> tuple[list[dict], list[dict], list[str]]:
    records = []
    samples = []
    errors = []

    with path.open("r", encoding="utf-8-sig") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(
                    f"line {line_number}: {exc}"
                )
                continue

            if not isinstance(record, dict):
                errors.append(
                    f"line {line_number}: record is not a JSON object"
                )
                continue

            records.append(record)

            if len(samples) < 2:
                samples.append(record)

    return records, samples, errors


def read_csv(path: Path) -> tuple[list[dict], list[str]]:
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fields = reader.fieldnames or []

    return rows, fields


def detect_id_key(record: dict) -> str | None:
    for key in ID_KEYS:
        if key in record:
            return key

    return None


def extract_ids(
    records: list[dict],
    source_name: str
) -> tuple[set[str], str | None, list[str]]:
    if not records:
        return set(), None, [
            f"{source_name}: no records"
        ]

    id_key = detect_id_key(records[0])

    if id_key is None:
        return set(), None, [
            f"{source_name}: cannot detect ID field"
        ]

    ids = set()
    errors = []

    for index, record in enumerate(records):
        value = record.get(id_key)

        if value is None or str(value).strip() == "":
            errors.append(
                f"{source_name}: blank ID at record {index + 1}"
            )
            continue

        ids.add(str(value).strip())

    return ids, id_key, errors


def summarize_jsonl(path: Path) -> dict:
    records, samples, errors = read_jsonl(path)

    all_keys = sorted({
        key
        for record in samples
        for key in record.keys()
    })

    id_key = detect_id_key(records[0]) if records else None

    return {
        "path": str(path.relative_to(MANUAL)),
        "exists": True,
        "record_count": len(records),
        "sample_keys": all_keys,
        "detected_id_key": id_key,
        "sample_records": samples,
        "parse_errors": errors,
    }


def summarize_csv(path: Path) -> dict:
    rows, fields = read_csv(path)

    return {
        "path": str(path.relative_to(MANUAL)),
        "exists": True,
        "record_count": len(rows),
        "fields": fields,
        "sample_records": rows[:2],
    }


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    errors = []
    warnings = []

    print("=" * 72)
    print("GOLD REVIEW PREPARATION — 2026-11-15")
    print("=" * 72)

    required_paths = [
        INVENTORY_PATH,
        QUEUE_PATH,
        SOURCE_PATHS["gold_batch"],
        SOURCE_PATHS["gold_supplement"],
        SOURCE_PATHS["gold_manifest"],
        SOURCE_PATHS["human_confirmed"],
        SOURCE_PATHS["priority_error_review"],
    ]

    for path in required_paths:
        if not path.is_file():
            errors.append(f"Required file missing: {path}")

    if errors:
        for error in errors:
            print("[FAIL]", error)
        return 1

    inventory = read_json(INVENTORY_PATH)

    expected_hashes = inventory.get("source_files", {})

    hash_results = {}

    for name, path in SOURCE_PATHS.items():
        if not path.is_file():
            warnings.append(f"Optional source missing: {path}")
            continue

        actual_hash = sha256_file(path)

        inventory_key = {
            "human_confirmed": "human_confirmed_adjudication",
        }.get(name, name)

        if name == "split_manifest":
            expected_hash = inventory.get(
                "split_manifest", {}
            ).get("sha256")
        else:
            expected_hash = expected_hashes.get(
                inventory_key, {}
            ).get("sha256")

        result = {
            "path": str(path.relative_to(MANUAL)),
            "actual_sha256": actual_hash,
            "expected_sha256": expected_hash,
            "matches_inventory": (
                actual_hash == expected_hash
                if expected_hash
                else None
            ),
        }

        hash_results[name] = result

        if expected_hash and actual_hash != expected_hash:
            errors.append(
                f"SHA-256 mismatch: {path}"
            )

    if errors:
        for error in errors:
            print("[FAIL]", error)
        return 1

    batch, batch_samples, batch_parse_errors = read_jsonl(
        SOURCE_PATHS["gold_batch"]
    )

    supplement, supplement_samples, supplement_parse_errors = (
        read_jsonl(SOURCE_PATHS["gold_supplement"])
    )

    if batch_parse_errors:
        errors.extend(batch_parse_errors)

    if supplement_parse_errors:
        errors.extend(supplement_parse_errors)

    batch_ids, batch_id_key, batch_id_errors = extract_ids(
        batch, "gold_batch"
    )

    supplement_ids, supplement_id_key, supplement_id_errors = (
        extract_ids(supplement, "gold_supplement")
    )

    errors.extend(batch_id_errors)
    errors.extend(supplement_id_errors)

    overlap_batch_supplement = batch_ids & supplement_ids
    gold_ids = batch_ids | supplement_ids

    queue_rows, queue_fields = read_csv(QUEUE_PATH)

    human_rows, human_fields = read_csv(
        SOURCE_PATHS["human_confirmed"]
    )

    priority_rows, priority_fields = read_csv(
        SOURCE_PATHS["priority_error_review"]
    )

    queue_ids, queue_id_key, queue_id_errors = extract_ids(
        queue_rows, "gold_review_queue"
    )

    human_ids, human_id_key, human_id_errors = extract_ids(
        human_rows, "human_confirmed"
    )

    priority_ids, priority_id_key, priority_id_errors = (
        extract_ids(priority_rows, "priority_error_review")
    )

    errors.extend(queue_id_errors)
    errors.extend(human_id_errors)
    errors.extend(priority_id_errors)

    if len(batch) != 100:
        errors.append(
            f"Gold batch expected 100 records, found {len(batch)}"
        )

    if len(supplement) != 85:
        errors.append(
            f"Gold supplement expected 85 records, found {len(supplement)}"
        )

    if len(gold_ids) != 185:
        errors.append(
            f"Gold union expected 185 unique IDs, found {len(gold_ids)}"
        )

    if overlap_batch_supplement:
        errors.append(
            f"Gold batch/supplement overlap: "
            f"{sorted(overlap_batch_supplement)[:10]}"
        )

    if len(queue_rows) != 185 or len(queue_ids) != 185:
        errors.append(
            "Gold review queue must contain 185 unique records"
        )

    if queue_ids != gold_ids:
        errors.append(
            "Gold review queue IDs do not exactly match Gold vFinal IDs"
        )

    if len(human_rows) != 22 or len(human_ids) != 22:
        errors.append(
            "Human-confirmed adjudication must contain 22 unique records"
        )

    if not human_ids.issubset(gold_ids):
        errors.append(
            "Human-confirmed file contains IDs outside Gold vFinal"
        )

    if len(priority_rows) != 170 or len(priority_ids) != 170:
        errors.append(
            "Priority extractor-error queue must contain 170 unique records"
        )

    if not priority_ids.issubset(gold_ids):
        errors.append(
            "Priority queue contains IDs outside Gold vFinal"
        )

    queue_priority_ids = {
        row["problem_id"]
        for row in queue_rows
        if (row.get("extractor_error_review") or "").strip().lower()
        == "yes"
    }

    if queue_priority_ids != priority_ids:
        errors.append(
            "Priority IDs in Gold review queue do not match "
            "priority_error_review_annotated.csv"
        )

    if errors:
        for error in errors:
            print("[FAIL]", error)
        return 1

    queue_status_counts = Counter(
        (row.get("queue_status") or "").strip().lower()
        for row in queue_rows
    )

    split_counts = Counter(
        (row.get("split") or "").strip()
        for row in queue_rows
    )

    priority_split_counts = Counter(
        (row.get("split") or "").strip()
        for row in queue_rows
        if (row.get("extractor_error_review") or "").strip().lower()
        == "yes"
    )

    confirmed_queue_ids = {
        row["problem_id"]
        for row in queue_rows
        if (row.get("queue_status") or "").strip().lower()
        == "confirmed"
    }

    if confirmed_queue_ids != human_ids:
        errors.append(
            "Confirmed IDs in Gold review queue do not match "
            "human-confirmed adjudication IDs"
        )

    pending_ddev = [
        row.copy()
        for row in queue_rows
        if (row.get("split") or "").strip() == "D_dev"
        and (row.get("queue_status") or "").strip().lower()
        == "pending"
    ]

    excluded_pool = [
        row
        for row in queue_rows
        if (row.get("split") or "").strip() == "D_pool"
        and (row.get("queue_status") or "").strip().lower()
        == "excluded"
    ]

    priority_ddev_ids = {
        row["problem_id"]
        for row in queue_rows
        if (row.get("split") or "").strip() == "D_dev"
        and (row.get("extractor_error_review") or "").strip().lower()
        == "yes"
    }

    pending_ddev_ids = {
        row["problem_id"]
        for row in pending_ddev
    }

    pending_priority_overlap = (
        pending_ddev_ids & priority_ddev_ids
    )

    if queue_status_counts != Counter({
        "confirmed": 22,
        "pending": 63,
        "excluded": 100,
    }):
        errors.append(
            f"Unexpected queue status counts: {dict(queue_status_counts)}"
        )

    if split_counts != Counter({
        "D_pool": 100,
        "D_dev": 85,
    }):
        errors.append(
            f"Unexpected Gold split counts: {dict(split_counts)}"
        )

    if len(pending_ddev) != 63:
        errors.append(
            f"Expected 63 pending D_dev records, found {len(pending_ddev)}"
        )

    if len(excluded_pool) != 100:
        errors.append(
            f"Expected 100 excluded D_pool records, found {len(excluded_pool)}"
        )

    if errors:
        for error in errors:
            print("[FAIL]", error)
        return 1

    worklist_path = (
        OUTPUT_DIR / "adjudication_worklist_63_pending.csv"
    )

    if worklist_path.exists():
        errors.append(
            f"Worklist already exists; refusing to overwrite: {worklist_path}"
        )

        for error in errors:
            print("[FAIL]", error)

        return 1

    new_fields = [
        "review_status_2026_11_15",
        "proposed_capabilities",
        "final_capabilities",
        "difficulty_final",
        "ambiguity_final",
        "decision_reason",
        "evidence_reference",
        "reviewed_at",
    ]

    original_fields = list(queue_fields)

    output_fields = original_fields + [
        field for field in new_fields
        if field not in original_fields
    ]

    for row in pending_ddev:
        row["review_status_2026_11_15"] = "NOT_REVIEWED"
        row["proposed_capabilities"] = ""
        row["final_capabilities"] = ""
        row["difficulty_final"] = ""
        row["ambiguity_final"] = ""
        row["decision_reason"] = ""
        row["evidence_reference"] = ""
        row["reviewed_at"] = ""

    with worklist_path.open(
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=output_fields,
            extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(pending_ddev)

    schema_report = {
        "generated_from": "Gold vFinal source files and 2026-11-14 audit",
        "source_hashes": hash_results,
        "gold_batch": {
            "records": len(batch),
            "id_field": batch_id_key,
            "sample_records": batch_samples,
        },
        "gold_supplement": {
            "records": len(supplement),
            "id_field": supplement_id_key,
            "sample_records": supplement_samples,
        },
        "gold_review_queue": {
            "records": len(queue_rows),
            "fields": queue_fields,
            "id_field": queue_id_key,
            "sample_records": queue_rows[:2],
            "queue_status_counts": dict(queue_status_counts),
            "split_counts": dict(split_counts),
        },
        "human_confirmed_adjudication": {
            "records": len(human_rows),
            "fields": human_fields,
            "id_field": human_id_key,
            "sample_records": human_rows[:2],
        },
        "priority_error_review": {
            "records": len(priority_rows),
            "fields": priority_fields,
            "id_field": priority_id_key,
            "sample_records": priority_rows[:2],
        },
        "priority_ddev": {
            "records": len(priority_ddev_ids),
        },
        "pending_ddev": {
            "records": len(pending_ddev),
            "priority_queue_overlap": len(pending_priority_overlap),
            "not_in_priority_queue": len(
                pending_ddev_ids - priority_ddev_ids
            ),
            "problem_ids": sorted(pending_ddev_ids),
        },
        "source_schema_inspection": {},
        "warnings": warnings,
    }

    schema_sources = [
        ("gold_vnext_batch", SOURCE_PATHS["vnext_batch"]),
        ("gold_vnext_supplement", SOURCE_PATHS["vnext_supplement"]),
        ("raw_train", SOURCE_PATHS["raw_train"]),
        ("supplement_selected", SOURCE_PATHS["supplement_selected"]),
        ("ambiguous_cases", SOURCE_PATHS["ambiguous_cases"]),
    ]

    for name, path in schema_sources:
        if path.is_file():
            schema_report["source_schema_inspection"][name] = (
                summarize_jsonl(path)
            )

    for name in ("gold_manifest", "vnext_manifest", "split_manifest"):
        path = SOURCE_PATHS[name]

        if path.is_file():
            data = read_json(path)

            schema_report["source_schema_inspection"][name] = {
                "path": str(path.relative_to(MANUAL)),
                "top_level_keys": (
                    sorted(data.keys())
                    if isinstance(data, dict)
                    else None
                ),
                "content": data,
            }

    inspection_path = (
        REPORT_DIR / "gold_source_schema_inspection.json"
    )

    with inspection_path.open("w", encoding="utf-8") as f:
        json.dump(
            schema_report,
            f,
            ensure_ascii=False,
            indent=2
        )

    summary_path = (
        REPORT_DIR / "gold_review_preparation_summary.md"
    )

    summary = [
        "# Gold Review Preparation — 2026-11-15",
        "",
        "## Source integrity",
        "",
        f"- Gold batch records: {len(batch)}",
        f"- Gold supplement records: {len(supplement)}",
        f"- Gold unique IDs: {len(gold_ids)}",
        f"- Gold review queue records: {len(queue_rows)}",
        f"- Human-confirmed decisions: {len(human_ids)}",
        f"- Priority extractor-error records: {len(priority_ids)}",
        "",
        "## Gold review status",
        "",
        f"- Confirmed: {queue_status_counts['confirmed']}",
        f"- Pending: {queue_status_counts['pending']}",
        f"- Excluded: {queue_status_counts['excluded']}",
        "",
        "## Worklist",
        "",
        f"- Pending D_dev records: {len(pending_ddev)}",
        f"- Also in priority extractor queue: {len(pending_priority_overlap)}",
        f"- Not in priority extractor queue: "
        f"{len(pending_ddev_ids - priority_ddev_ids)}",
        f"- Worklist: `{worklist_path.relative_to(MANUAL)}`",
        "",
        "## Important scope restrictions",
        "",
        "- The 170-row priority queue is not a Gold adjudication queue.",
        "- Only the 63 pending D_dev records enter this worklist.",
        "- The 22 human-confirmed records are retained unchanged.",
        "- The 100 D_pool records remain excluded from primary mastery evaluation.",
        "- This script does not modify Gold vFinal, Gold vNext, split files, "
        "capability config, or extractor rules.",
        "- This worklist is not a frozen Gold release.",
        "",
        "## Source schema inspection",
        "",
        f"`{inspection_path.relative_to(MANUAL)}`",
        "",
        "The schema inspection contains source fields and sample records. "
        "Use it before writing a source-specific join or adjudication exporter.",
        "",
    ]

    summary_path.write_text(
        "\n".join(summary),
        encoding="utf-8"
    )

    print("\n" + "=" * 72)
    print("VALIDATION SUMMARY")
    print("=" * 72)

    print("[PASS] Gold batch: 100 records")
    print("[PASS] Gold supplement: 85 records")
    print("[PASS] Gold vFinal: 185 unique IDs")
    print("[PASS] Gold review queue: 185 unique IDs")
    print("[PASS] Human-confirmed adjudication: 22 unique IDs")
    print("[PASS] Priority extractor-error queue: 170 unique IDs")
    print("[PASS] Queue status: 22 confirmed / 63 pending / 100 excluded")
    print("[PASS] Pending D_dev worklist: 63 records")
    print(
        "[INFO] Pending D_dev also in priority queue: "
        f"{len(pending_priority_overlap)}"
    )

    print("\nCreated:")
    print(worklist_path)
    print(inspection_path)
    print(summary_path)

    print("\nRESULT: PASS — REVIEW WORKLIST PREPARED")
    print("Gold source files were not modified.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
