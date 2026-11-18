import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(".")
METHODS = ["B2", "B3", "B4", "B5"]
SEEDS = [13, 42, 2026]
CHECKPOINTS = ["S1", "S2", "S3"]
ALLOWED_STATUSES = {"valid", "invalid_answer", "invalid_format"}

DEV_IDS_PATH = ROOT / "splits" / "d_dev_ids.txt"
OUT_DIR = ROOT / "reports" / "p1p2_integration"
CSV_OUT = OUT_DIR / "dev_prediction_audit_v2.csv"
JSON_OUT = OUT_DIR / "dev_prediction_audit_v2.json"

def sha256_file(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def load_expected_ids(path):
    if not path.exists():
        raise FileNotFoundError(path)

    ids = [
        line.strip()
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]

    if len(ids) != len(set(ids)):
        raise ValueError("D_dev ID file contains duplicates")

    return set(ids)

def prediction_paths():
    paths = [("SHARED", 0, "S0", ROOT / "runs/main/S0/eval_dev.jsonl")]

    for method in METHODS:
        for seed in SEEDS:
            for checkpoint in CHECKPOINTS:
                path = (
                    ROOT / "runs" / "main"
                    / f"{method}_seed{seed}"
                    / checkpoint
                    / "eval_dev.jsonl"
                )
                paths.append((method, seed, checkpoint, path))

    return paths

def main():
    errors = []
    records = []
    expected_ids = load_expected_ids(DEV_IDS_PATH)

    for method, seed, checkpoint, path in prediction_paths():
        if not path.exists():
            errors.append(f"MISSING_FILE: {path}")
            continue

        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()

        rows = []
        parse_errors = []

        for line_no, line in enumerate(
            raw.decode("utf-8").splitlines(), start=1
        ):
            if not line.strip():
                continue

            try:
                row = json.loads(line)
            except Exception as exc:
                parse_errors.append(f"line {line_no}: {exc}")
                continue

            if not isinstance(row, dict):
                parse_errors.append(
                    f"line {line_no}: JSON value is not an object"
                )
                continue

            rows.append(row)

        if parse_errors:
            errors.append(
                f"JSON_PARSE_ERROR: {path}: {parse_errors[:5]}"
            )

        ids = [str(row.get("problem_id", "")).strip() for row in rows]
        id_set = set(ids)
        duplicates = len(ids) - len(id_set)
        empty_ids = sum(not value for value in ids)

        if len(rows) != len(expected_ids):
            errors.append(
                f"ROW_COUNT: {path}: {len(rows)} != {len(expected_ids)}"
            )

        if duplicates:
            errors.append(f"DUPLICATE_IDS: {path}: {duplicates}")

        if empty_ids:
            errors.append(f"EMPTY_IDS: {path}: {empty_ids}")

        missing = sorted(expected_ids - id_set)
        extra = sorted(id_set - expected_ids)

        if missing or extra:
            errors.append(
                f"ID_SET_MISMATCH: {path}: "
                f"missing={len(missing)}, extra={len(extra)}"
            )

        statuses = Counter(
            row.get("status", row.get("verification_status"))
            for row in rows
        )

        unknown_statuses = set(statuses) - ALLOWED_STATUSES
        if unknown_statuses:
            errors.append(
                f"UNKNOWN_STATUS: {path}: {sorted(map(str, unknown_statuses))}"
            )

        record = {
            "method": method,
            "seed": seed,
            "checkpoint": checkpoint,
            "path": path.as_posix(),
            "rows": len(rows),
            "unique_ids": len(id_set),
            "empty_ids": empty_ids,
            "duplicate_ids": duplicates,
            "missing_ids": len(missing),
            "extra_ids": len(extra),
            "status_valid": statuses.get("valid", 0),
            "status_invalid_answer": statuses.get("invalid_answer", 0),
            "status_invalid_format": statuses.get("invalid_format", 0),
            "unknown_status_count": sum(
                count for status, count in statuses.items()
                if status not in ALLOWED_STATUSES
            ),
            "prediction_sha256": digest,
            "audit_status": "PASS" if not (
                parse_errors or
                len(rows) != len(expected_ids) or
                duplicates or empty_ids or missing or extra or
                unknown_statuses
            ) else "FAIL",
        }
        records.append(record)

        print(
            f"{method} seed={seed} {checkpoint}: "
            f"rows={len(rows)}, unique={len(id_set)}, "
            f"valid={statuses.get('valid', 0)}, "
            f"invalid_answer={statuses.get('invalid_answer', 0)}, "
            f"invalid_format={statuses.get('invalid_format', 0)}, "
            f"sha256={digest}"
        )

    by_key = {
        (r["method"], r["seed"], r["checkpoint"]): r
        for r in records
    }

    aliases = []
    for seed in SEEDS:
        b4 = by_key.get(("B4", seed, "S1"))
        b5 = by_key.get(("B5", seed, "S1"))

        if not b4 or not b5:
            errors.append(f"ALIAS_CHECK_MISSING: seed={seed}")
            continue

        same = (
            b4["prediction_sha256"] == b5["prediction_sha256"]
        )

        aliases.append({
            "seed": seed,
            "left": "B4/S1",
            "right": "B5/S1",
            "same_prediction_sha256": same,
            "prediction_sha256": b4["prediction_sha256"] if same else None,
            "alias_group": f"S1_SHARED_SEED_{seed}" if same else None,
        })

        if same:
            print(f"ALIAS CONFIRMED: B4/B5 S1 seed={seed}")
        else:
            print(f"NOT AN ALIAS: B4/B5 S1 seed={seed}")

    if len(records) != 37:
        errors.append(f"CONTEXT_COUNT: {len(records)} != 37")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if CSV_OUT.exists() or JSON_OUT.exists():
        raise FileExistsError(
            "Refusing to overwrite existing v2 audit output. "
            "Inspect or archive it before rerunning."
        )

    with CSV_OUT.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=list(records[0].keys()) if records else [],
        )
        writer.writeheader()
        writer.writerows(records)

    report = {
        "expected_dev_id_count": len(expected_ids),
        "prediction_context_count": len(records),
        "allowed_statuses": sorted(ALLOWED_STATUSES),
        "correctness_policy": "status == valid",
        "records": records,
        "prediction_aliases": aliases,
        "errors": errors,
        "result": "PASS" if not errors else "FAIL",
    }

    JSON_OUT.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print("\n=== G3 V2 RESULT ===")
    print("Contexts:", len(records))
    print("Errors:", len(errors))
    print("Result:", report["result"])
    print("CSV:", CSV_OUT)
    print("JSON:", JSON_OUT)

    if errors:
        for error in errors:
            print("ERROR:", error)
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
