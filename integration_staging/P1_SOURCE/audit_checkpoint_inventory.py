from pathlib import Path
import csv
import hashlib
import json
import sys

MANUAL = Path(r"C:\KLTN-SLM-Reasoning\experiments\week2September\manual")
OUT = MANUAL / "reports" / "learning_curve" / "2026-11-17"
INVENTORY = OUT / "B4_seed13_checkpoint_inventory.csv"
CAP_ROOT = MANUAL / "reports" / "capability" / "student_eval_2026-11-17"

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))

def flatten_keys(obj, prefix=""):
    result = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            name = f"{prefix}.{key}" if prefix else key
            result.append(name)
            result.extend(flatten_keys(value, name))
    elif isinstance(obj, list) and obj:
        result.extend(flatten_keys(obj[0], prefix + "[0]"))
    return result

if not INVENTORY.exists():
    raise FileNotFoundError(INVENTORY)

with INVENTORY.open("r", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

if len(rows) != 3:
    raise RuntimeError(f"EXPECTED_3_CHECKPOINTS_FOUND_{len(rows)}")

expected = {
    "student_ckpt_001": {"round": "0", "micro_batch": "4", "grad_accum": "2"},
    "student_ckpt_002": {"round": "1", "micro_batch": "4", "grad_accum": "2"},
    "student_ckpt_003": {"round": "2", "micro_batch": "1", "grad_accum": "8"},
}

gold_hash_sets = []
evaluator_hashes = []
pool_hashes = []
all_ok = True

for row in rows:
    ckpt = row["checkpoint"]
    print(f"\n===== {ckpt} =====")

    for key, value in expected[ckpt].items():
        actual = str(row.get(key, ""))
        ok = actual == value
        print(f"{key}: actual={actual} expected={value} {'PASS' if ok else 'FAIL'}")
        all_ok &= ok

    train_hash_log = row.get("train_set_sha256_log", "")
    train_hash_actual = row.get("train_set_sha256_actual", "")
    hash_ok = bool(train_hash_log) and train_hash_log == train_hash_actual
    print("TRAIN_SET_HASH_MATCH:", hash_ok)
    all_ok &= hash_ok

    if row.get("prediction_records") != "500":
        print("PREDICTION_COUNT_FAIL:", row.get("prediction_records"))
        all_ok = False
    if row.get("prediction_unique_ids") != "500":
        print("PREDICTION_UNIQUE_COUNT_FAIL:", row.get("prediction_unique_ids"))
        all_ok = False
    if row.get("prediction_duplicate_ids") != "0":
        print("PREDICTION_DUPLICATES_FAIL:", row.get("prediction_duplicate_ids"))
        all_ok = False
    if row.get("prediction_missing_ids") != "0":
        print("PREDICTION_MISSING_IDS_FAIL:", row.get("prediction_missing_ids"))
        all_ok = False

    print("PREDICTIONS: 500 records / 500 unique IDs")
    print("BACKEND:", row.get("eval_backend"))
    print("DO_SAMPLE:", row.get("eval_do_sample"))
    print("PROMPT_VERSION:", row.get("eval_prompt_version"))

    cap_dir = CAP_ROOT / f"B4_seed13_ckpt{ckpt[-3:]}"
    manifest_path = cap_dir / "student_capability_evaluation_manifest.json"
    coverage_path = cap_dir / "prediction_coverage_report.json"

    manifest = read_json(manifest_path)
    coverage = read_json(coverage_path)

    print("MANIFEST_TOP_LEVEL_KEYS:", sorted(manifest.keys()))
    print("MANIFEST_NESTED_KEYS:", flatten_keys(manifest)[:100])
    print("COVERAGE_TOP_LEVEL_KEYS:", sorted(coverage.keys()))
    print("COVERAGE_NESTED_KEYS:", flatten_keys(coverage)[:100])

    gold_hash_sets.append((
        manifest.get("gold_batch_sha256"),
        manifest.get("gold_supplement_sha256"),
        manifest.get("adjudication_sha256"),
    ))

    evaluator_hashes.append(manifest.get("evaluator_sha256"))
    pool_hashes.append(row.get("pool_sha256"))

print("\n===== CROSS-CHECK =====")
print("GOLD_HASH_SETS_IDENTICAL:", len(set(map(str, gold_hash_sets))) == 1)
print("EVALUATOR_HASHES:", evaluator_hashes)
print("EVALUATOR_HASHES_IDENTICAL:", len(set(map(str, evaluator_hashes))) == 1)
print("POOL_HASHES:", pool_hashes)
print("POOL_HASHES_IDENTICAL:", len(set(pool_hashes)) == 1)

if len(set(map(str, gold_hash_sets))) != 1:
    all_ok = False
if len(set(map(str, evaluator_hashes))) != 1:
    all_ok = False
if len(set(pool_hashes)) != 1:
    all_ok = False

print("\nINVENTORY_AUDIT:", "PASS" if all_ok else "FAIL")
if not all_ok:
    sys.exit(1)