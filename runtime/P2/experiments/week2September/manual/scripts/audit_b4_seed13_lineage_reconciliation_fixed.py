from pathlib import Path
import json
import hashlib
import sys

MANUAL = Path(r"C:\Users\PC - NGHI\Desktop\Pipeline\P2\experiments\week2September\manual")
RUN = MANUAL / "runs" / "main" / "B4_seed13"
STAGING = MANUAL / "integration_staging" / "P1" / "reports" / "task7" / "B4" / "seed_13"
CHECKPOINTS = Path(r"C:\Users\PC - NGHI\Desktop\Pipeline\P2\integration_staging\P1\models\task7\B4\seed_13")

OUT = MANUAL / "reports" / "p1p2_integration" / "b4_seed13_lineage_reconciliation_fixed.txt"
OUT.parent.mkdir(parents=True, exist_ok=True)

lines = []

def log(s=""):
    print(s)
    lines.append(str(s))

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def read_json(path):
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)

def read_jsonl(path):
    rows, errors = [], []
    with path.open("r", encoding="utf-8-sig") as f:
        for n, raw in enumerate(f, 1):
            if not raw.strip():
                continue
            try:
                rows.append(json.loads(raw))
            except Exception as e:
                errors.append(f"line {n}: {e}")
    return rows, errors

def get_ids(obj):
    ids = obj.get("trajectory_ids")
    if ids is None:
        ids = obj.get("selected_trajectory_ids")
    if ids is None:
        raise KeyError("Không tìm thấy trajectory_ids hoặc selected_trajectory_ids")
    return [str(x) for x in ids]

def compare(label, a, b):
    if a is None or b is None:
        log(f"{label}: NOT_COMPARABLE")
        return
    only_a = sorted(a - b)
    only_b = sorted(b - a)
    log(f"{label}: {'EXACT_MATCH' if a == b else 'MISMATCH'}")
    log(f"  A_COUNT={len(a)} B_COUNT={len(b)} INTERSECTION={len(a & b)}")
    log(f"  A_ONLY_COUNT={len(only_a)} B_ONLY_COUNT={len(only_b)}")
    if only_a:
        log(f"  A_ONLY_SAMPLE={only_a[:10]}")
    if only_b:
        log(f"  B_ONLY_SAMPLE={only_b[:10]}")

log("=== ROOT VALIDATION ===")
for label, path in [
    ("RUN", RUN),
    ("STAGING_TRAIN_SETS", STAGING),
    ("CHECKPOINT_TRAIN_LOGS", CHECKPOINTS),
]:
    log(f"{label}: {path} EXISTS={path.exists()}")

if not all(p.exists() for p in [RUN, STAGING, CHECKPOINTS]):
    log("FATAL: Một hoặc nhiều root không tồn tại. Dừng audit.")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    sys.exit(2)

checkpoint_log_path = RUN / "checkpoint_log.jsonl"
checkpoint_rows, checkpoint_errors = read_jsonl(checkpoint_log_path)
log("\n=== CHECKPOINT LOG ===")
log(f"PATH={checkpoint_log_path}")
log(f"SHA256={sha256(checkpoint_log_path)}")
log(f"ROWS={len(checkpoint_rows)} PARSE_ERRORS={checkpoint_errors}")

checkpoint_by_name = {}
for row in checkpoint_rows:
    if row.get("record_type") == "checkpoint":
        name = row.get("checkpoint")
        checkpoint_by_name[name] = row
        log(
            f"CHECKPOINT={name} ROUND={row.get('round')} "
            f"CONFIG_HASH={row.get('config_hash')} "
            f"SELECTED_COUNT={len(row.get('selected_trajectory_ids') or [])}"
        )

all_rounds_pass = True

for r in range(3):
    round_name = f"round_{r:03d}"
    log(f"\n=== {round_name} ===")

    run_train = RUN / round_name / "train_set.json"
    staging_train = STAGING / round_name / "train_set.json"
    selection_log = RUN / round_name / "selection_log.jsonl"

    ckpt_name = f"student_ckpt_{r+1:03d}"
    train_log = CHECKPOINTS / ckpt_name / "train_log.json"
    checkpoint_row = checkpoint_by_name.get(ckpt_name)

    required = [
        ("RUN_TRAIN_SET", run_train),
        ("STAGING_TRAIN_SET", staging_train),
        ("SELECTION_LOG", selection_log),
        ("CHECKPOINT_TRAIN_LOG", train_log),
    ]

    for label, path in required:
        log(f"{label}: {path} EXISTS={path.exists()}")

    if not all(path.exists() for _, path in required) or checkpoint_row is None:
        log("ROUND_RESULT=INCOMPLETE_INPUTS")
        all_rounds_pass = False
        continue

    run_obj = read_json(run_train)
    staging_obj = read_json(staging_train)
    train_obj = read_json(train_log)

    run_ids_list = get_ids(run_obj)
    staging_ids_list = get_ids(staging_obj)
    run_ids = set(run_ids_list)
    staging_ids = set(staging_ids_list)

    log(f"RUN_TRAIN_SHA256={sha256(run_train)}")
    log(f"STAGING_TRAIN_SHA256={sha256(staging_train)}")
    log(f"TRAIN_LOG_SHA256={sha256(train_log)}")
    log(f"RUN_TRAIN_COUNT={len(run_ids_list)} UNIQUE={len(run_ids)}")
    log(f"STAGING_TRAIN_COUNT={len(staging_ids_list)} UNIQUE={len(staging_ids)}")
    log(f"RUN_CONFIG_HASH={run_obj.get('config_sha256', run_obj.get('config_hash'))}")
    log(f"STAGING_CONFIG_HASH={staging_obj.get('config_sha256', staging_obj.get('config_hash'))}")
    log(f"TRAIN_LOG_CONFIG_HASH={train_obj.get('config_sha256', train_obj.get('config_hash'))}")
    log(f"TRAIN_LOG_TRAIN_SET_SHA256={train_obj.get('train_set_sha256')}")
    log(f"TRAIN_LOG_N_EXAMPLES={train_obj.get('n_examples')}")

    compare("RUN_VS_STAGING", run_ids, staging_ids)

    selection_rows, selection_errors = read_jsonl(selection_log)
    selected_rows = [x for x in selection_rows if x.get("selected") is True]
    selected_ids_list = [str(x["trajectory_id"]) for x in selected_rows if x.get("trajectory_id") is not None]
    selected_ids = set(selected_ids_list)

    log(f"SELECTION_ROWS={len(selection_rows)}")
    log(f"SELECTION_PARSE_ERRORS={selection_errors}")
    log(f"SELECTED_TRUE_ROWS={len(selected_ids_list)} UNIQUE={len(selected_ids)}")
    log(f"SELECTION_CONFIG_HASHES={sorted({str(x.get('config_hash')) for x in selection_rows})}")

    compare("RUN_TRAIN_VS_SELECTED_TRUE", run_ids, selected_ids)
    compare("STAGING_TRAIN_VS_SELECTED_TRUE", staging_ids, selected_ids)

    checkpoint_ids_list = [
        str(x) for x in (checkpoint_row.get("selected_trajectory_ids") or [])
    ]
    checkpoint_ids = set(checkpoint_ids_list)
    log(f"CHECKPOINT_LOG_SELECTED_COUNT={len(checkpoint_ids_list)} UNIQUE={len(checkpoint_ids)}")

    compare("RUN_TRAIN_VS_CHECKPOINT_LOG", run_ids, checkpoint_ids)
    compare("STAGING_TRAIN_VS_CHECKPOINT_LOG", staging_ids, checkpoint_ids)
    compare("SELECTED_TRUE_VS_CHECKPOINT_LOG", selected_ids, checkpoint_ids)

    train_set_hash_match_run = train_obj.get("train_set_sha256") == sha256(run_train)
    train_set_hash_match_staging = train_obj.get("train_set_sha256") == sha256(staging_train)
    log(f"TRAIN_LOG_HASH_MATCH_RUN_TRAIN_SET={train_set_hash_match_run}")
    log(f"TRAIN_LOG_HASH_MATCH_STAGING_TRAIN_SET={train_set_hash_match_staging}")

    n_examples_match_run = train_obj.get("n_examples") == len(run_ids_list)
    n_examples_match_staging = train_obj.get("n_examples") == len(staging_ids_list)
    log(f"TRAIN_LOG_N_EXAMPLES_MATCH_RUN={n_examples_match_run}")
    log(f"TRAIN_LOG_N_EXAMPLES_MATCH_STAGING={n_examples_match_staging}")

    config_values = {
        str(run_obj.get("config_sha256", run_obj.get("config_hash"))),
        str(staging_obj.get("config_sha256", staging_obj.get("config_hash"))),
        str(train_obj.get("config_sha256", train_obj.get("config_hash"))),
        str(checkpoint_row.get("config_hash")),
    }
    config_values.discard("None")
    log(f"CONFIG_HASH_VALUES={sorted(config_values)}")
    log(f"CONFIG_HASH_UNIFORM={len(config_values) == 1}")

    # Xác định train set được train_log ghi nhận bằng hash chính xác.
    if train_set_hash_match_run and not train_set_hash_match_staging:
        logged_source = "RUN_TRAIN_SET"
    elif train_set_hash_match_staging and not train_set_hash_match_run:
        logged_source = "STAGING_TRAIN_SET"
    elif train_set_hash_match_run and train_set_hash_match_staging:
        logged_source = "BOTH_IDENTICAL"
    else:
        logged_source = "NEITHER_OR_DIFFERENT_BYTES"

    log(f"TRAIN_LOG_RECORDED_TRAIN_SET_SOURCE={logged_source}")

    round_pass = (
        len(run_ids) == len(run_ids_list)
        and len(staging_ids) == len(staging_ids_list)
        and run_ids == selected_ids
        and run_ids == checkpoint_ids
        and train_obj.get("train_set_sha256") == sha256(run_train)
        and train_obj.get("n_examples") == len(run_ids_list)
        and len(config_values) == 1
        and not selection_errors
    )

    log(f"ROUND_RESULT={'PASS' if round_pass else 'FAIL_REQUIRES_INVESTIGATION'}")
    if not round_pass:
        all_rounds_pass = False

log("\n=== FINAL RESULT ===")
log(
    "LINEAGE_RECONCILIATION_FIXED: "
    + ("PASS" if all_rounds_pass else "NOT_PASS_DO_NOT_RUN_G5")
)
log("This audit is read-only. No source data or experiment artifacts were modified.")

OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"\nREPORT_SAVED={OUT}")
