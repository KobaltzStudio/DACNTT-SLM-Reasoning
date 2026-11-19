from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path


MANUAL = Path(__file__).resolve().parents[1]
AUDIT_ROOT = (
    MANUAL
    / "reports"
    / "p1p2_integration"
    / "checkpoint_inventory_audit"
    / "archive_prediction_validation"
)

MATRIX_PATH = (
    MANUAL
    / "reports"
    / "p1p2_integration"
    / "checkpoint_inventory_audit"
    / "checkpoint_evidence_matrix.csv"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    if not AUDIT_ROOT.is_dir():
        raise SystemExit(f"AUDIT_ROOT_NOT_FOUND: {AUDIT_ROOT}")

    if not MATRIX_PATH.is_file():
        raise SystemExit(f"MATRIX_NOT_FOUND: {MATRIX_PATH}")

    runs = [
        path for path in AUDIT_ROOT.iterdir()
        if path.is_dir() and path.name.startswith("run_")
    ]
    if not runs:
        raise SystemExit("NO_ARCHIVE_AUDIT_RUN_FOUND")

    latest_run = max(runs, key=lambda path: path.stat().st_mtime)
    prediction_csv = latest_run / "prediction_validation.csv"

    if not prediction_csv.is_file():
        raise SystemExit(f"PREDICTION_REPORT_NOT_FOUND: {prediction_csv}")

    with prediction_csv.open(
        "r", encoding="utf-8-sig", newline=""
    ) as handle:
        predictions = list(csv.DictReader(handle))

    with MATRIX_PATH.open(
        "r", encoding="utf-8-sig", newline=""
    ) as handle:
        matrix = list(csv.DictReader(handle))

    groups = defaultdict(list)

    for row in predictions:
        digest = row.get("member_sha256", "").strip()
        if not digest:
            raise SystemExit("PREDICTION_ROW_WITHOUT_SHA256")
        groups[digest].append(row)

    output_dir = (
        MANUAL
        / "reports"
        / "p1p2_integration"
        / "checkpoint_inventory_audit"
        / "prediction_deduplication"
        / datetime.now().strftime("run_%Y%m%d_%H%M%S")
    )
    output_dir.mkdir(parents=True, exist_ok=False)

    dedup_rows = []

    for digest, copies in sorted(groups.items()):
        first = copies[0]
        dedup_rows.append({
            "member_sha256": digest,
            "independent_prediction_group": first.get("member_path", ""),
            "copy_count": len(copies),
            "rows": first.get("rows", ""),
            "unique_ids": first.get("unique_ids", ""),
            "coverage_status": first.get("coverage_status", ""),
            "archive_locations": json.dumps(
                [
                    {
                        "archive_chain": row.get("archive_chain", ""),
                        "member_path": row.get("member_path", ""),
                    }
                    for row in copies
                ],
                ensure_ascii=False,
            ),
        })

    dedup_path = output_dir / "prediction_deduplication.csv"
    with dedup_path.open(
        "w", encoding="utf-8-sig", newline=""
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "member_sha256",
                "independent_prediction_group",
                "copy_count",
                "rows",
                "unique_ids",
                "coverage_status",
                "archive_locations",
            ],
        )
        writer.writeheader()
        writer.writerows(dedup_rows)

    matrix_summary = defaultdict(int)
    for row in matrix:
        matrix_summary[row.get("evidence_status", "UNKNOWN")] += 1

    summary = {
        "source_audit_run": str(latest_run),
        "source_prediction_rows": len(predictions),
        "unique_prediction_sha256_groups": len(groups),
        "duplicate_copy_count": len(predictions) - len(groups),
        "matrix_context_count": len(matrix),
        "matrix_evidence_status": dict(matrix_summary),
        "deduplication_policy": (
            "Files with identical SHA256 are copies of the same "
            "prediction artifact and count as one independent result."
        ),
        "prediction_groups": dedup_rows,
    }

    summary_path = output_dir / "prediction_deduplication_summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("PREDICTION_DEDUP_REPORT=CREATED")
    print(f"SOURCE_AUDIT_RUN={latest_run}")
    print(f"PREDICTION_FILE_COPIES={len(predictions)}")
    print(f"INDEPENDENT_PREDICTION_GROUPS={len(groups)}")
    print(f"DUPLICATE_COPIES={len(predictions) - len(groups)}")
    print(f"MATRIX_CONTEXTS={len(matrix)}")
    print(f"OUTPUT_DIR={output_dir}")


if __name__ == "__main__":
    main()
