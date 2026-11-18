import csv
import hashlib
import json
from pathlib import Path

P2 = Path(r"C:\Users\PC - NGHI\Desktop\Pipeline\P2")
MANUAL = P2 / "experiments" / "week2September" / "manual"
AUDIT = P2 / "integration_staging" / "G4_CHECKPOINT_AUDIT"

OUT = MANUAL / "reports" / "capability_g4_validation"
LOG_DIR = AUDIT / "execution_logs"

RUNS = {
    "S1": "B4_seed13_S1",
    "S2": "B4_seed13_S2",
    "S3": "B4_seed13_S3",
}

EXPECTED_CAPABILITIES = {
    "addition",
    "subtraction",
    "multiplication",
    "division",
    "percentage",
    "fraction",
    "ratio",
}

REQUIRED_OUTPUTS = [
    "capability_metrics.csv",
    "capability_metrics.jsonl",
    "checkpoint_lineage.json",
]

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def load_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))

def print_json(title, obj):
    print(f"\n--- {title} ---")
    print(json.dumps(obj, indent=2, ensure_ascii=False))

print("========== G5.7 CAPABILITY RESULT AUDIT ==========")
print(f"OUTPUT_ROOT={OUT}")
print(f"LOG_DIR={LOG_DIR}")

if not OUT.is_dir():
    raise SystemExit(f"OUTPUT_ROOT_MISSING={OUT}")

all_pass = True

# 1. Inspect stage status records.
for stage, run_id in RUNS.items():
    print(f"\n========== {stage} STATUS ==========")

    status_files = sorted(
        LOG_DIR.glob(f"{run_id}_*.status.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    if not status_files:
        print("STATUS_FILE=FAIL")
        all_pass = False
        continue

    status_path = status_files[0]
    status = load_json(status_path)

    print(f"STATUS_FILE={status_path}")
    print_json("STAGE STATUS", status)

    if status.get("status") != "PASS" or status.get("exit_code") != 0:
        print("STAGE_STATUS_CHECK=FAIL")
        all_pass = False
    else:
        print("STAGE_STATUS_CHECK=PASS")

# 2. Inspect each sidecar.
for stage, run_id in RUNS.items():
    run_dir = OUT / run_id
    print(f"\n========== {run_id} OUTPUTS ==========")

    if not run_dir.is_dir():
        print(f"RUN_DIRECTORY=FAIL | {run_dir}")
        all_pass = False
        continue

    print(f"RUN_DIRECTORY=PASS | {run_dir}")

    for filename in REQUIRED_OUTPUTS:
        path = run_dir / filename
        if not path.is_file():
            print(f"{filename}=FAIL")
            all_pass = False
        else:
            print(
                f"{filename}=PASS | "
                f"bytes={path.stat().st_size} | "
                f"sha256={sha256(path)}"
            )

    # CSV metrics
    csv_path = run_dir / "capability_metrics.csv"
    if csv_path.is_file():
        try:
            with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                columns = reader.fieldnames or []

            print(f"CSV_COLUMNS={columns}")
            print(f"CSV_DATA_ROWS={len(rows)}")

            for index, row in enumerate(rows, start=1):
                print(f"CSV_ROW_{index}={json.dumps(row, ensure_ascii=False)}")

            if len(rows) != 7:
                print("CSV_CAPABILITY_ROW_COUNT=FAIL")
                all_pass = False
            else:
                print("CSV_CAPABILITY_ROW_COUNT=PASS")

        except Exception as exc:
            print(f"CSV_PARSE=FAIL | {exc}")
            all_pass = False

    # JSONL metrics
    jsonl_path = run_dir / "capability_metrics.jsonl"
    if jsonl_path.is_file():
        try:
            rows = []
            with jsonl_path.open("r", encoding="utf-8-sig") as f:
                for line_number, line in enumerate(f, start=1):
                    if line.strip():
                        rows.append(json.loads(line))

            print(f"JSONL_DATA_ROWS={len(rows)}")
            for index, row in enumerate(rows, start=1):
                print(
                    f"JSONL_ROW_{index}="
                    f"{json.dumps(row, ensure_ascii=False)}"
                )

            if len(rows) != 7:
                print("JSONL_CAPABILITY_ROW_COUNT=FAIL")
                all_pass = False
            else:
                print("JSONL_CAPABILITY_ROW_COUNT=PASS")

        except Exception as exc:
            print(f"JSONL_PARSE=FAIL | {exc}")
            all_pass = False

    # Checkpoint lineage
    lineage_path = run_dir / "checkpoint_lineage.json"
    if lineage_path.is_file():
        try:
            lineage = load_json(lineage_path)
            print_json("CHECKPOINT LINEAGE", lineage)
            print("LINEAGE_JSON_PARSE=PASS")
        except Exception as exc:
            print(f"LINEAGE_JSON_PARSE=FAIL | {exc}")
            all_pass = False

    print("FILES_IN_RUN_DIRECTORY:")
    for path in sorted(run_dir.iterdir()):
        if path.is_file():
            print(f"  {path.name} | {path.stat().st_size} bytes")

print("\n========== AUDIT SUMMARY ==========")
print(f"G5_OUTPUT_CONTENT_AUDIT={'PASS' if all_pass else 'FAIL'}")

if not all_pass:
    raise SystemExit(1)
