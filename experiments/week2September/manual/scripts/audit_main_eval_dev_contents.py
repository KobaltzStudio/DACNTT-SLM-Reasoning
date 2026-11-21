import argparse
import csv
import hashlib
import json
import re
import sys
import zipfile
from collections import Counter
from datetime import datetime
from pathlib import Path, PurePosixPath


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def read_jsonl(data):
    rows = []
    errors = []

    text = data.decode("utf-8-sig")
    for line_no, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
            if not isinstance(value, dict):
                errors.append(f"line_{line_no}:JSON_VALUE_NOT_OBJECT")
            else:
                rows.append(value)
        except Exception as exc:
            errors.append(f"line_{line_no}:{type(exc).__name__}:{exc}")

    return rows, errors


def write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def compact_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def context_from_path(member):
    parts = PurePosixPath(member).parts
    if len(parts) >= 2 and re.fullmatch(r"(B2|B3|B4|B5)_seed\d+", parts[0]):
        return parts[0], parts[1]
    return "", ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", required=True)
    parser.add_argument("--dev-ids", required=True)
    parser.add_argument("--output-root", required=True)
    args = parser.parse_args()

    archive_path = Path(args.archive).resolve()
    dev_ids_path = Path(args.dev_ids).resolve()
    output_root = Path(args.output_root).resolve()

    if not archive_path.is_file():
        raise FileNotFoundError(f"ARCHIVE_NOT_FOUND: {archive_path}")
    if not dev_ids_path.is_file():
        raise FileNotFoundError(f"D_DEV_IDS_NOT_FOUND: {dev_ids_path}")

    expected_ids = {
        line.strip()
        for line in dev_ids_path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    }
    if len(expected_ids) != 500:
        raise RuntimeError(f"EXPECTED_D_DEV_IDS_500_BUT_FOUND_{len(expected_ids)}")

    run_id = datetime.now().strftime("run_%Y%m%d_%H%M%S")
    out_dir = output_root / run_id
    out_dir.mkdir(parents=True, exist_ok=False)

    prediction_rows = []
    training_rows = []
    marker_rows = []
    checkpoint_log_rows = []
    archive_errors = []

    with zipfile.ZipFile(archive_path, "r") as zf:
        bad_member = zf.testzip()
        if bad_member is not None:
            raise RuntimeError(f"ZIP_INTEGRITY_ERROR: {bad_member}")

        names = zf.namelist()

        eval_members = sorted(
            name for name in names
            if PurePosixPath(name).name.lower() == "eval_dev.jsonl"
            and re.fullmatch(
                r"(B2|B3|B4|B5)_seed\d+/S[123]/eval_dev\.jsonl",
                name,
                flags=re.IGNORECASE,
            )
        )

        train_members = sorted(
            name for name in names
            if PurePosixPath(name).name.lower() == "train_log.json"
            and re.fullmatch(
                r"(B2|B3|B4|B5)_seed\d+/S[123]/adapter/train_log\.json",
                name,
                flags=re.IGNORECASE,
            )
        )

        marker_members = sorted(
            name for name in names
            if "/.done/" in name.lower()
            and name.lower().endswith(".json")
        )

        checkpoint_members = sorted(
            name for name in names
            if re.fullmatch(
                r"(B2|B3|B4|B5)_seed\d+/checkpoint_log\.jsonl",
                name,
                flags=re.IGNORECASE,
            )
        )

        for member in eval_members:
            raw = zf.read(member)
            rows, errors = read_jsonl(raw)

            ids = []
            missing_id_rows = 0
            for row in rows:
                value = row.get("problem_id")
                if value is None:
                    value = row.get("id")
                if value is None or not str(value).strip():
                    missing_id_rows += 1
                else:
                    ids.append(str(value).strip())

            counts = Counter(ids)
            unique_ids = set(ids)
            duplicates = sorted(k for k, v in counts.items() if v > 1)
            missing = sorted(expected_ids - unique_ids)
            outside = sorted(unique_ids - expected_ids)

            status_counts = Counter()
            verification_counts = Counter()
            correct_counts = Counter()

            for row in rows:
                if row.get("status") is not None:
                    status_counts[str(row["status"])] += 1
                if row.get("verification_status") is not None:
                    verification_counts[str(row["verification_status"])] += 1
                if row.get("correct") is not None:
                    correct_counts[str(row["correct"])] += 1

            method, round_name = context_from_path(member)
            seed_match = re.search(r"_seed(\d+)", member)
            seed = seed_match.group(1) if seed_match else ""

            coverage_ok = (
                len(rows) == 500
                and len(ids) == 500
                and len(unique_ids) == 500
                and not missing
                and not outside
                and missing_id_rows == 0
                and not errors
            )

            prediction_rows.append({
                "method": method,
                "seed": seed,
                "round": round_name,
                "member_path": member,
                "sha256": sha256_bytes(raw),
                "bytes": len(raw),
                "rows": len(rows),
                "ids_found": len(ids),
                "unique_ids": len(unique_ids),
                "duplicate_id_count": len(duplicates),
                "duplicate_ids": ";".join(duplicates),
                "missing_from_d_dev_count": len(missing),
                "missing_from_d_dev": ";".join(missing),
                "outside_d_dev_count": len(outside),
                "outside_d_dev": ";".join(outside),
                "missing_id_rows": missing_id_rows,
                "json_error_count": len(errors),
                "json_errors": " | ".join(errors),
                "status_counts": compact_json(dict(status_counts)),
                "verification_status_counts": compact_json(dict(verification_counts)),
                "correct_counts": compact_json(dict(correct_counts)),
                "sample_keys": compact_json(sorted(rows[0].keys()) if rows else []),
                "coverage_status": "500_UNIQUE_IDS" if coverage_ok else "INVALID_COVERAGE",
            })

        for member in train_members:
            raw = zf.read(member)
            try:
                obj = json.loads(raw.decode("utf-8-sig"))
                parse_status = "JSON_OK"
                keys = sorted(obj.keys()) if isinstance(obj, dict) else []
                payload = compact_json(obj)
            except Exception as exc:
                parse_status = f"JSON_ERROR:{type(exc).__name__}:{exc}"
                keys = []
                payload = ""

            method, round_name = context_from_path(member)
            seed_match = re.search(r"_seed(\d+)", member)
            training_rows.append({
                "method": method,
                "seed": seed_match.group(1) if seed_match else "",
                "round": round_name,
                "member_path": member,
                "sha256": sha256_bytes(raw),
                "bytes": len(raw),
                "parse_status": parse_status,
                "top_level_keys": compact_json(keys),
                "json_content": payload,
            })

        for member in marker_members:
            raw = zf.read(member)
            try:
                obj = json.loads(raw.decode("utf-8-sig"))
                parse_status = "JSON_OK"
                payload = compact_json(obj)
            except Exception as exc:
                parse_status = f"JSON_ERROR:{type(exc).__name__}:{exc}"
                payload = ""

            marker_rows.append({
                "member_path": member,
                "marker_name": PurePosixPath(member).name,
                "context": PurePosixPath(member).parts[0],
                "sha256": sha256_bytes(raw),
                "parse_status": parse_status,
                "json_content": payload,
            })

        for member in checkpoint_members:
            raw = zf.read(member)
            rows, errors = read_jsonl(raw)
            for index, row in enumerate(rows):
                checkpoint_log_rows.append({
                    "member_path": member,
                    "row_index": index,
                    "json_error_count": len(errors),
                    "record": compact_json(row),
                })

    write_csv(
        out_dir / "eval_dev_validation.csv",
        prediction_rows,
        [
            "method", "seed", "round", "member_path", "sha256", "bytes",
            "rows", "ids_found", "unique_ids", "duplicate_id_count",
            "duplicate_ids", "missing_from_d_dev_count", "missing_from_d_dev",
            "outside_d_dev_count", "outside_d_dev", "missing_id_rows",
            "json_error_count", "json_errors", "status_counts",
            "verification_status_counts", "correct_counts", "sample_keys",
            "coverage_status",
        ],
    )

    write_csv(
        out_dir / "train_log_audit.csv",
        training_rows,
        [
            "method", "seed", "round", "member_path", "sha256", "bytes",
            "parse_status", "top_level_keys", "json_content",
        ],
    )

    write_csv(
        out_dir / "done_marker_audit.csv",
        marker_rows,
        [
            "member_path", "marker_name", "context", "sha256",
            "parse_status", "json_content",
        ],
    )

    write_csv(
        out_dir / "checkpoint_log_audit.csv",
        checkpoint_log_rows,
        ["member_path", "row_index", "json_error_count", "record"],
    )

    coverage_counts = Counter(
        row["coverage_status"] for row in prediction_rows
    )
    method_counts = Counter(row["method"] for row in prediction_rows)

    summary = {
        "archive": str(archive_path),
        "archive_sha256": sha256_bytes(archive_path.read_bytes()),
        "d_dev_unique_ids": len(expected_ids),
        "eval_dev_file_count": len(eval_members),
        "train_log_file_count": len(train_members),
        "done_marker_count": len(marker_members),
        "checkpoint_log_file_count": len(checkpoint_members),
        "prediction_coverage_counts": dict(coverage_counts),
        "prediction_method_counts": dict(method_counts),
        "all_eval_dev_coverage_valid": (
            len(eval_members) == 36
            and len(prediction_rows) == 36
            and all(r["coverage_status"] == "500_UNIQUE_IDS" for r in prediction_rows)
        ),
        "train_logs_all_parseable": all(
            r["parse_status"] == "JSON_OK" for r in training_rows
        ),
        "markers_all_parseable": all(
            r["parse_status"] == "JSON_OK" for r in marker_rows
        ),
    }

    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("MAIN_EVAL_DEV_AUDIT=COMPLETED")
    print(f"D_DEV_UNIQUE_IDS={len(expected_ids)}")
    print(f"EVAL_DEV_FILES={len(eval_members)}")
    print(f"TRAIN_LOG_FILES={len(train_members)}")
    print(f"DONE_MARKERS={len(marker_members)}")
    print(f"CHECKPOINT_LOG_FILES={len(checkpoint_members)}")
    print(f"COVERAGE_COUNTS={compact_json(dict(coverage_counts))}")
    print(f"ALL_EVAL_DEV_COVERAGE_VALID={summary['all_eval_dev_coverage_valid']}")
    print(f"TRAIN_LOGS_ALL_PARSEABLE={summary['train_logs_all_parseable']}")
    print(f"MARKERS_ALL_PARSEABLE={summary['markers_all_parseable']}")
    print(f"OUTPUT_DIR={out_dir}")


if __name__ == "__main__":
    main()
