from pathlib import Path
import csv
import hashlib
import json
import sys

MANUAL = Path(r"C:\KLTN-SLM-Reasoning\experiments\week2September\manual")
OUT = MANUAL / "reports" / "learning_curve" / "2026-11-17"
CAP_ROOT = MANUAL / "reports" / "capability" / "student_eval_2026-11-17"
INVENTORY = OUT / "B4_seed13_checkpoint_inventory.csv"

EXPECTED_GOLD = {
    "gold_batch_sha256": "5b655ab6705fa8d6178871d35f30712b90058354a29952b9e51e88e0108c8a9f",
    "gold_supplement_sha256": "8c41bc4e5c237a289dfcda92fcc691bf84b0ff5552ea8c8249c3947d3725ae26",
    "adjudication_csv_sha256": "f9a8d55f5079ec94ad31cb0c933a6a0d00409cce0815e47fbefd80c1354224ab",
}

EXPECTED = {
    "student_ckpt_001": {"round": 0, "micro_batch": 4, "grad_accum": 2},
    "student_ckpt_002": {"round": 1, "micro_batch": 4, "grad_accum": 2},
    "student_ckpt_003": {"round": 2, "micro_batch": 1, "grad_accum": 8},
}

def read_json(path):
    if not path.is_file():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))

def require(condition, message):
    if not condition:
        raise RuntimeError("FAIL: " + message)
    print("PASS:", message)

with INVENTORY.open("r", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

require(len(rows) == 3, f"inventory contains exactly 3 checkpoints; found={len(rows)}")

gold_sets = []
evaluator_hashes = []
pool_hashes = []
prediction_hashes = []

for row in rows:
    ckpt = row["checkpoint"]
    print(f"\n===== {ckpt} =====")

    require(ckpt in EXPECTED, f"{ckpt} is an expected checkpoint")
    exp = EXPECTED[ckpt]

    for field, expected in exp.items():
        actual = row.get(field, "")
        require(str(actual) == str(expected),
                f"{ckpt} {field}: actual={actual}, expected={expected}")

    require(row.get("train_set_sha256_log") == row.get("train_set_sha256_actual"),
            f"{ckpt} train-set SHA matches actual file")

    for field, expected in {
        "prediction_records": "500",
        "prediction_unique_ids": "500",
        "prediction_duplicate_ids": "0",
        "prediction_missing_ids": "0",
    }.items():
        require(str(row.get(field, "")) == expected,
                f"{ckpt} {field}={row.get(field)}")

    require(row.get("eval_backend") == "hf", f"{ckpt} evaluation backend is hf")
    require(str(row.get("eval_do_sample")).lower() == "false",
            f"{ckpt} uses greedy decoding")
    require(row.get("eval_prompt_version") == "v1",
            f"{ckpt} uses prompt version v1")

    cap_dir = CAP_ROOT / f"B4_seed13_ckpt{ckpt[-3:]}"
    manifest = read_json(cap_dir / "student_capability_evaluation_manifest.json")
    coverage = read_json(cap_dir / "prediction_coverage_report.json")

    # Gold hashes are nested under manifest.gold_source_hashes.
    manifest_gold = manifest.get("gold_source_hashes", {})
    for key, expected in EXPECTED_GOLD.items():
        actual = manifest_gold.get(key)
        require(actual == expected,
                f"{ckpt} manifest {key} matches frozen Gold SHA")

    # Coverage report stores the same source hashes under coverage.gold_source.
    coverage_gold = coverage.get("gold_source", {})
    for key, expected in EXPECTED_GOLD.items():
        actual = coverage_gold.get(key)
        require(actual == expected,
                f"{ckpt} coverage {key} matches frozen Gold SHA")

    require(coverage.get("status") == "PASS_WITH_COVERAGE_REPORTED",
            f"{ckpt} coverage status is PASS_WITH_COVERAGE_REPORTED")
    require(coverage.get("prediction_records") == 500,
            f"{ckpt} coverage records=500")
    require(coverage.get("prediction_unique_ids") == 500,
            f"{ckpt} coverage unique IDs=500")
    require(coverage.get("confirmed_gold_records") == 22,
            f"{ckpt} confirmed Gold D_dev records=22")
    require(coverage.get("matched_gold_prediction_ids") == 22,
            f"{ckpt} matched confirmed Gold prediction IDs=22")
    require(coverage.get("missing_prediction_count") == 0,
            f"{ckpt} missing prediction count=0")
    require(coverage.get("missing_prediction_ids") == [],
            f"{ckpt} missing prediction ID list is empty")
    require(coverage.get("prediction_ids_outside_d_dev") == [],
            f"{ckpt} has no prediction IDs outside D_dev")
    require(coverage.get("coverage_rate") == 1.0,
            f"{ckpt} coverage rate=1.0")

    manifest_pred_hash = manifest.get("prediction_sha256")
    coverage_pred_hash = coverage.get("prediction_sha256")
    require(bool(manifest_pred_hash), f"{ckpt} manifest prediction SHA exists")
    require(manifest_pred_hash == coverage_pred_hash,
            f"{ckpt} manifest and coverage prediction SHA match")

    evaluator_hash = manifest.get("evaluator_sha256")
    require(bool(evaluator_hash), f"{ckpt} evaluator SHA exists")

    gold_sets.append(tuple(manifest_gold.get(k) for k in EXPECTED_GOLD))
    evaluator_hashes.append(evaluator_hash)
    pool_hashes.append(row.get("pool_sha256"))
    prediction_hashes.append(manifest_pred_hash)

print("\n===== CROSS-CHECK =====")
require(len(set(gold_sets)) == 1, "Gold source SHA set identical across checkpoints")
require(len(set(evaluator_hashes)) == 1, "evaluator SHA identical across checkpoints")
require(len(set(pool_hashes)) == 1, "pool SHA identical across checkpoints")
require(len(set(prediction_hashes)) == 3, "each checkpoint has a distinct prediction SHA")

print("\nINVENTORY_AUDIT_V2: PASS")