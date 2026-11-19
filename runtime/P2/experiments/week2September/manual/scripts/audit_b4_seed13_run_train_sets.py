import hashlib
import json
from pathlib import Path

MANUAL = Path(__file__).resolve().parent.parent
REPO = MANUAL.parent.parent
STAGING = MANUAL / "integration_staging" / "P1" / "reports" / "task7" / "B4" / "seed_13"
RUNS = MANUAL / "runs" / "main" / "B4_seed13"

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))

def read_jsonl(path):
    rows = []
    errors = []
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except Exception as exc:
                errors.append((line_no, str(exc)))
    return rows, errors

print("=== ROOTS ===")
print("MANUAL:", MANUAL)
print("STAGING:", STAGING)
print("RUNS:", RUNS)
print("STAGING_EXISTS:", STAGING.exists())
print("RUNS_EXISTS:", RUNS.exists())

for round_no in range(3):
    name = f"round_{round_no:03d}"
    staged = STAGING / name / "train_set.json"
    run_train_set = RUNS / name / "train_set.json"
    selection_log = RUNS / name / "selection_log.jsonl"

    print(f"\n=== {name} ===")
    print("STAGED_TRAIN_SET_EXISTS:", staged.exists())
    print("RUN_TRAIN_SET_EXISTS:", run_train_set.exists())
    print("RUN_SELECTION_LOG_EXISTS:", selection_log.exists())

    staged_ids = set()
    if staged.exists():
        obj = read_json(staged)
        staged_ids = set(obj.get("trajectory_ids", []))
        print("STAGED_SHA256:", sha256(staged))
        print("STAGED_ID_COUNT:", len(obj.get("trajectory_ids", [])))
        print("STAGED_ID_UNIQUE:", len(staged_ids))
        print("STAGED_CONFIG_SHA256:", obj.get("config_sha256"))
        print("STAGED_SOURCE_CHECKPOINT:", obj.get("source_checkpoint"))

    if run_train_set.exists():
        obj = read_json(run_train_set)
        run_ids = set(obj.get("trajectory_ids", []))
        print("RUN_TRAIN_SET_SHA256:", sha256(run_train_set))
        print("RUN_ID_COUNT:", len(obj.get("trajectory_ids", [])))
        print("RUN_ID_UNIQUE:", len(run_ids))
        print("RUN_CONFIG_SHA256:", obj.get("config_sha256"))
        print("RUN_SOURCE_CHECKPOINT:", obj.get("source_checkpoint"))
        print("STAGING_RUN_HASH_MATCH:", sha256(staged) == sha256(run_train_set) if staged.exists() else False)
        print("STAGING_RUN_ID_SET_MATCH:", staged_ids == run_ids if staged.exists() else False)

    if selection_log.exists():
        rows, errors = read_jsonl(selection_log)
        print("SELECTION_LOG_ROWS:", len(rows))
        print("SELECTION_LOG_PARSE_ERRORS:", errors[:5])
        if rows:
            print("SELECTION_LOG_FIRST_ROW_KEYS:", sorted(rows[0].keys()))
            print("SELECTION_LOG_FIRST_ROW:", json.dumps(rows[0], ensure_ascii=False)[:1800])

            trajectory_ids = [
                row.get("trajectory_id")
                for row in rows
                if row.get("trajectory_id") is not None
            ]
            print("SELECTION_LOG_TRAJECTORY_ID_COUNT:", len(trajectory_ids))
            print("SELECTION_LOG_TRAJECTORY_ID_UNIQUE:", len(set(trajectory_ids)))
            print("SELECTION_LOG_ID_INTERSECTION_WITH_TRAIN_SET:",
                  len(set(trajectory_ids) & staged_ids) if staged.exists() else "N/A")

print("\nACTUAL_RUN_TRAIN_SET_AUDIT: COMPLETE")
