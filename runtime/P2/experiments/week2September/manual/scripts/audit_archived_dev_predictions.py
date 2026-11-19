from pathlib import Path
from zipfile import ZipFile, BadZipFile
from io import BytesIO
from datetime import datetime
import csv
import hashlib
import json
import re
import sys

MANUAL = Path(
    r"C:\Users\PC - NGHI\Desktop\Pipeline\P2"
    r"\experiments\week2September\manual"
)
P2_ROOT = MANUAL.parents[2]

DEV_IDS_PATH = MANUAL / "splits" / "d_dev_ids.txt"

ROOT_ARCHIVES = [
    MANUAL / "manual_P2_1.zip",
    MANUAL / "manual_P2_2.zip",
    MANUAL / "runs" / "main" / "main.zip",
    P2_ROOT / "integration_staging.zip",
    MANUAL / "integration_staging" / "P1" / "reports" /
        "task7" / "B4" / "seed_13" / "seed_13.zip",
]

MAX_NESTED_DEPTH = 3

def sha256(data):
    return hashlib.sha256(data).hexdigest()

def load_dev_ids(path):
    if not path.exists():
        raise FileNotFoundError(f"D_DEV_IDS_NOT_FOUND: {path}")

    ids = set()
    with path.open("r", encoding="utf-8-sig") as f:
        for line in f:
            value = line.strip()
            if value:
                ids.add(value)

    if len(ids) != 500:
        raise ValueError(
            f"D_DEV_EXPECTED_500_UNIQUE_IDS_GOT_{len(ids)}"
        )
    return ids

def is_prediction_member(name):
    normalized = name.replace("\\", "/")
    base = normalized.rsplit("/", 1)[-1].lower()

    return (
        base.endswith(".jsonl")
        and base.startswith("eval_student")
        and "dev" in base
    )

def parse_prediction(raw, expected_ids):
    text = raw.decode("utf-8-sig")
    rows = []
    json_errors = []

    for line_no, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
            if not isinstance(obj, dict):
                raise ValueError("JSONL row is not an object")
            rows.append(obj)
        except Exception as exc:
            json_errors.append(f"line {line_no}: {exc}")

    ids = []
    missing_id_rows = 0

    for row in rows:
        pid = row.get("problem_id")
        if pid is None or str(pid).strip() == "":
            missing_id_rows += 1
        else:
            ids.append(str(pid).strip())

    unique_ids = set(ids)
    duplicate_count = len(ids) - len(unique_ids)
    missing_from_file = expected_ids - unique_ids
    outside_dev = unique_ids - expected_ids

    strict_valid = 0
    strict_invalid = 0
    missing_strict_status = 0

    for row in rows:
        status = row.get("status")
        verification = row.get("verification_status")
        correct = row.get("correct")

        if status == "valid" or verification == "valid":
            strict_valid += 1
        elif status is not None or verification is not None:
            strict_invalid += 1
        elif isinstance(correct, bool):
            if correct:
                strict_valid += 1
            else:
                strict_invalid += 1
        else:
            missing_strict_status += 1

    coverage_ok = (
        len(rows) == 500
        and len(unique_ids) == 500
        and duplicate_count == 0
        and missing_id_rows == 0
        and not missing_from_file
        and not outside_dev
        and not json_errors
    )

    return {
        "rows": len(rows),
        "unique_ids": len(unique_ids),
        "duplicate_ids": duplicate_count,
        "missing_id_rows": missing_id_rows,
        "missing_from_d_dev": len(missing_from_file),
        "outside_d_dev": len(outside_dev),
        "json_errors": len(json_errors),
        "strict_valid": strict_valid,
        "strict_invalid": strict_invalid,
        "missing_strict_status": missing_strict_status,
        "coverage_status": "500_UNIQUE_IDS" if coverage_ok else "INVALID",
        "missing_ids_sample": ";".join(sorted(missing_from_file)[:10]),
        "outside_ids_sample": ";".join(sorted(outside_dev)[:10]),
        "json_error_sample": " | ".join(json_errors[:3]),
    }

def inspect_zip_bytes(
    raw_zip,
    archive_label,
    depth,
    expected_ids,
    prediction_rows,
    archive_rows,
):
    try:
        zf = ZipFile(BytesIO(raw_zip), "r")
    except BadZipFile as exc:
        archive_rows.append({
            "archive_chain": archive_label,
            "depth": depth,
            "status": f"BAD_ZIP: {exc}",
            "member_count": 0,
            "nested_zip_count": 0,
        })
        return

    with zf:
        bad_member = zf.testzip()
        infos = zf.infolist()
        nested_count = 0

        archive_rows.append({
            "archive_chain": archive_label,
            "depth": depth,
            "status": "OK" if bad_member is None else f"BAD_MEMBER: {bad_member}",
            "member_count": len(infos),
            "nested_zip_count": 0,
        })

        for info in infos:
            if info.is_dir():
                continue

            name = info.filename
            try:
                member_bytes = zf.read(info)
            except Exception as exc:
                if is_prediction_member(name):
                    prediction_rows.append({
                        "archive_chain": archive_label,
                        "member_path": name,
                        "member_size": info.file_size,
                        "member_sha256": "",
                        "read_status": f"READ_ERROR: {exc}",
                        "rows": 0,
                        "unique_ids": 0,
                        "duplicate_ids": 0,
                        "missing_id_rows": 0,
                        "missing_from_d_dev": 0,
                        "outside_d_dev": 0,
                        "json_errors": 0,
                        "strict_valid": 0,
                        "strict_invalid": 0,
                        "missing_strict_status": 0,
                        "coverage_status": "READ_ERROR",
                        "missing_ids_sample": "",
                        "outside_ids_sample": "",
                        "json_error_sample": "",
                    })
                continue

            if is_prediction_member(name):
                result = parse_prediction(member_bytes, expected_ids)
                prediction_rows.append({
                    "archive_chain": archive_label,
                    "member_path": name,
                    "member_size": info.file_size,
                    "member_sha256": sha256(member_bytes),
                    "read_status": "OK",
                    **result,
                })

            if (
                depth < MAX_NESTED_DEPTH
                and name.lower().endswith(".zip")
            ):
                nested_count += 1
                inspect_zip_bytes(
                    member_bytes,
                    archive_label + " -> " + name,
                    depth + 1,
                    expected_ids,
                    prediction_rows,
                    archive_rows,
                )

        archive_rows[-1]["nested_zip_count"] = nested_count

def save_csv(path, rows):
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    fields = list(rows[0].keys())
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fields,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)

def main():
    expected_ids = load_dev_ids(DEV_IDS_PATH)

    run_id = datetime.now().strftime("run_%Y%m%d_%H%M%S")
    out_dir = (
        MANUAL / "reports" / "p1p2_integration" /
        "checkpoint_inventory_audit" /
        "archive_prediction_validation" / run_id
    )
    out_dir.mkdir(parents=True, exist_ok=False)

    prediction_rows = []
    archive_rows = []

    for archive_path in ROOT_ARCHIVES:
        if not archive_path.exists():
            archive_rows.append({
                "archive_chain": str(archive_path),
                "depth": 0,
                "status": "ROOT_ARCHIVE_NOT_FOUND",
                "member_count": 0,
                "nested_zip_count": 0,
            })
            continue

        try:
            raw = archive_path.read_bytes()
            inspect_zip_bytes(
                raw,
                str(archive_path),
                0,
                expected_ids,
                prediction_rows,
                archive_rows,
            )
        except Exception as exc:
            archive_rows.append({
                "archive_chain": str(archive_path),
                "depth": 0,
                "status": f"ROOT_READ_ERROR: {exc}",
                "member_count": 0,
                "nested_zip_count": 0,
            })

    save_csv(out_dir / "prediction_validation.csv", prediction_rows)
    save_csv(out_dir / "archive_scan_summary.csv", archive_rows)

    valid = sum(
        row["coverage_status"] == "500_UNIQUE_IDS"
        for row in prediction_rows
    )
    invalid = len(prediction_rows) - valid

    print("ARCHIVE_PREDICTION_AUDIT=COMPLETED")
    print(f"D_DEV_UNIQUE_IDS={len(expected_ids)}")
    print(f"ARCHIVES_SCANNED={len(archive_rows)}")
    print(f"PREDICTION_MEMBERS_FOUND={len(prediction_rows)}")
    print(f"PREDICTION_MEMBERS_VALID={valid}")
    print(f"PREDICTION_MEMBERS_INVALID={invalid}")
    print(f"OUTPUT_DIR={out_dir}")

    if not prediction_rows:
        print("WARNING=NO_EVAL_STUDENT_DEV_JSONL_FOUND")

if __name__ == "__main__":
    main()

