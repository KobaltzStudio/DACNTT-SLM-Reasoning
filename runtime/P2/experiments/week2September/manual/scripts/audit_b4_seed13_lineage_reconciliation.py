import hashlib
import json
from pathlib import Path

MANUAL = Path(__file__).resolve().parent.parent
REPO = MANUAL.parent.parent

RUN_DIR = MANUAL / "runs" / "main" / "B4_seed13"
STAGING_REPORTS = (
    MANUAL / "integration_staging" / "P1" / "reports"
    / "task7" / "B4" / "seed_13"
)
CHECKPOINT_ROOT = (
    REPO / "integration_staging" / "P1" / "models"
    / "task7" / "B4" / "seed_13"
)

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

def show_set_comparison(label, expected, actual):
    expected = set(expected)
    actual = set(actual)
    print(f"{label}_EXPECTED_COUNT:", len(expected))
    print(f"{label}_ACTUAL_COUNT:", len(actual))
    print(f"{label}_INTERSECTION:", len(expected & actual))
    print(f"{label}_EXPECTED_ONLY:", len(expected - actual))
    print(f"{label}_ACTUAL_ONLY:", len(actual - expected))
    print(f"{label}_EXACT_MATCH:", expected == actual)

    if expected - actual:
        print(f"{label}_EXPECTED_ONLY_SAMPLE:", sorted(expected - actual)[:8])
    if actual - expected:
        print(f"{label}_ACTUAL_ONLY_SAMPLE:", sorted(actual - expected)[:8])

print("=== ROOT VALIDATION ===")
for path in (RUN_DIR, STAGING_REPORTS, CHECKPOINT_ROOT):
    print(path, "EXISTS:", path.exists())

checkpoint_log_path = RUN_DIR / "checkpoint_log.jsonl"
checkpoint_rows, checkpoint_errors = read_jsonl(checkpoint_log_path)

print("\n=== CHECKPOINT LOG ===")
print("PATH:", checkpoint_log_path)
print("SHA256:", sha256(checkpoint_log_path))
print("ROWS:", len(checkpoint_rows))
print("PARSE_ERRORS:", checkpoint_errors)

checkpoint_by_round = {}
for row in checkpoint_rows:
    if row.get("record_type") != "checkpoint":
        continue
    checkpoint_by_round[row.get("round")] = row
    print(
        "CHECKPOINT_RECORD:",
        row.get("round"),
        row.get("checkpoint"),
        "config_hash=", row.get("config_hash"),
        "selected_count=", len(row.get("selected_trajectory_ids", [])),
    )

for round_no in range(3):
    name = f"round_{round_no:03d}"
    run_set_path = RUN_DIR / name / "train_set.json"
    staged_set_path = STAGING_REPORTS / name / "train_set.json"
    selection_path = RUN_DIR / name / "selection_log.jsonl"

    ckpt_round = round_no + 1
    ckpt_name = f"student_ckpt_{ckpt_round:03d}"
    checkpoint_dir = CHECKPOINT_ROOT / ckpt_name
    train_log_path = checkpoint_dir / "train_log.json"

    print(f"\n{'=' * 20} {name} {'=' * 20}")

    for path in (
        run_set_path, staged_set_path, selection_path, train_log_path
    ):
        print("FILE:", path, "EXISTS:", path.exists())

    if not all(p.exists() for p in (run_set_path, staged_set_path, selection_path, train_log_path)):
        print("ROUND_AUDIT: INCOMPLETE_INPUTS")
        continue

    run_set = read_json(run_set_path)
    staged_set = read_json(staged_set_path)
    train_log = read_json(train_log_path)
    selection_rows, selection_errors = read_jsonl(selection_path)

    run_ids_list = run_set.get("trajectory_ids", [])
    staged_ids_list = staged_set.get("trajectory_ids", [])
    run_ids = set(run_ids_list)
    staged_ids = set(staged_ids_list)

    print("\n--- RUN TRAIN SET ---")
    print("SHA256:", sha256(run_set_path))
    print("COUNT:", len(run_ids_list))
    print("UNIQUE:", len(run_ids))
    print("CONFIG_SHA256:", run_set.get("config_sha256"))
    print("SOURCE_CHECKPOINT:", run_set.get("source_checkpoint"))

    print("\n--- STAGED TRAIN SET ---")
    print("SHA256:", sha256(staged_set_path))
    print("COUNT:", len(staged_ids_list))
    print("UNIQUE:", len(staged_ids))
    print("CONFIG_SHA256:", staged_set.get("config_sha256"))
    print("SOURCE_CHECKPOINT:", staged_set.get("source_checkpoint"))

    print("\n--- TRAIN LOG ---")
    print("SHA256:", sha256(train_log_path))
    print("TRAIN_SET_PATH:", train_log.get("train_set"))
    print("TRAIN_SET_SHA256:", train_log.get("train_set_sha256"))
    print("TRAIN_SET_HASH_MATCH_STAGED:", train_log.get("train_set_sha256") == sha256(staged_set_path))
    print("TRAIN_SET_HASH_MATCH_RUN:", train_log.get("train_set_sha256") == sha256(run_set_path))
    print("N_EXAMPLES:", train_log.get("n_examples"))
    print("CONFIG_SHA256:", train_log.get("config_sha256"))
    print("CHECKPOINT_PARENT:", train_log.get("checkpoint_parent"))
    print("SEED:", train_log.get("seed"))
    print("DATA_ORDER_SEED:", train_log.get("data_order_seed"))

    print("\n--- RUN TRAIN SET VS STAGED TRAIN SET ---")
    show_set_comparison("RUN_VS_STAGED", run_ids, staged_ids)

    print("\n--- SELECTION LOG ---")
    print("ROWS:", len(selection_rows))
    print("PARSE_ERRORS:", selection_errors[:5])
    print("CONFIG_HASHES:", sorted({
        str(row.get("config_hash")) for row in selection_rows
    }))
    print("ROUND_VALUES:", sorted({
        str(row.get("round")) for row in selection_rows
    }))
    print("SOURCE_CHECKPOINTS:", sorted({
        str(row.get("source_checkpoint")) for row in selection_rows
    }))

    selected_rows = [
        row for row in selection_rows if row.get("selected") is True
    ]
    selected_ids = [
        row.get("trajectory_id") for row in selected_rows
        if row.get("trajectory_id") is not None
    ]

    print("SELECTED_ROWS:", len(selected_rows))
    print("SELECTED_ID_COUNT:", len(selected_ids))
    print("SELECTED_ID_UNIQUE:", len(set(selected_ids)))

    show_set_comparison(
        "SELECTION_VS_RUN_TRAIN_SET", selected_ids, run_ids
    )
    show_set_comparison(
        "SELECTION_VS_STAGED_TRAIN_SET", selected_ids, staged_ids
    )

    print("\n--- CHECKPOINT LOG VS TRAIN SETS ---")
    record = checkpoint_by_round.get(ckpt_round)
    if record is None:
        print("CHECKPOINT_RECORD_MISSING:", ckpt_round)
    else:
        ckpt_ids = record.get("selected_trajectory_ids", [])
        print("CHECKPOINT_CONFIG_HASH:", record.get("config_hash"))
        show_set_comparison(
            "CHECKPOINT_VS_RUN_TRAIN_SET", ckpt_ids, run_ids
        )
        show_set_comparison(
            "CHECKPOINT_VS_STAGED_TRAIN_SET", ckpt_ids, staged_ids
        )
        show_set_comparison(
            "CHECKPOINT_VS_SELECTION_LOG", ckpt_ids, selected_ids
        )

print("\n=== FINAL NOTE ===")
print("This audit is read-only. It does not modify checkpoints, train sets, logs, or config.")
print("LINEAGE_RECONCILIATION_AUDIT: COMPLETE")
