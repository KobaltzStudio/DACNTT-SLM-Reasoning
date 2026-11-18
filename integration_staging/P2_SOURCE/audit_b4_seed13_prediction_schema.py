import hashlib
import json
from collections import Counter
from pathlib import Path

MANUAL = Path(
    r"C:\Users\PC - NGHI\Desktop\Pipeline\P2\experiments\week2September\manual"
)

PREDICTION_ROOT = (
    MANUAL / "integration_staging" / "P1"
    / "reports" / "task7" / "B4" / "seed_13"
)

CHECKPOINT_ROOT = (
    MANUAL / "integration_staging" / "P1"
    / "models" / "task7" / "B4" / "seed_13"
)

EXPECTED = [
    {
        "name": "student_ckpt_001",
        "round": 0,
        "prediction": PREDICTION_ROOT / "eval_student_ckpt_001_dev.jsonl",
        "checkpoint": CHECKPOINT_ROOT / "student_ckpt_001",
        "sha256": "9bb9aeb1c356b7563fc3d8b1b45fe9553bc7c2ca7907e7672833fae448f9a26d",
        "checkpoint_value": "B4_seed13_student_ckpt_001",
    },
    {
        "name": "student_ckpt_002",
        "round": 1,
        "prediction": PREDICTION_ROOT / "eval_student_ckpt_002_dev.jsonl",
        "checkpoint": CHECKPOINT_ROOT / "student_ckpt_002",
        "sha256": "bd1c5a1a952056beea92d982b0212eab484a9bf6ad034cbc76803d6214d7c50f",
        "checkpoint_value": "B4_seed13_student_ckpt_002",
    },
    {
        "name": "student_ckpt_003",
        "round": 2,
        "prediction": PREDICTION_ROOT / "eval_student_ckpt_003_dev.jsonl",
        "checkpoint": CHECKPOINT_ROOT / "student_ckpt_003",
        "sha256": "b27ecc6553c963cb8b173794b82f703aee4ebaf99461b0b051d45c06a55bf7cb",
        "checkpoint_value": "B4_seed13_student_ckpt_003",
    },
]

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def load_jsonl(path: Path):
    rows = []
    with path.open("r", encoding="utf-8-sig") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: {exc}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_no}: JSON row is not an object")
            rows.append(row)
    return rows

all_pass = True
report = []

for item in EXPECTED:
    path = item["prediction"]
    checkpoint = item["checkpoint"]

    print("\n" + "=" * 88)
    print("CHECKPOINT:", item["name"])
    print("ROUND:", item["round"])
    print("PREDICTION:", path)
    print("PREDICTION_EXISTS:", path.is_file())
    print("CHECKPOINT_DIR_EXISTS:", checkpoint.is_dir())

    if not path.is_file():
        all_pass = False
        print("RESULT: FAIL - prediction file missing")
        continue

    actual_hash = sha256(path)
    hash_ok = actual_hash == item["sha256"]
    rows = load_jsonl(path)

    keys = sorted(set().union(*(row.keys() for row in rows))) if rows else []
    id_values = [str(row.get("problem_id", "")).strip() for row in rows]
    missing_ids = sum(not x for x in id_values)
    duplicate_ids = len(id_values) - len(set(id_values))

    correct_types = Counter(type(row.get("correct")).__name__ for row in rows)
    status_values = Counter(str(row.get("status")) for row in rows)
    checkpoint_values = Counter(str(row.get("checkpoint", "")) for row in rows)

    correct_bool_count = sum(isinstance(row.get("correct"), bool) for row in rows)
    status_present_count = sum("status" in row for row in rows)
    checkpoint_present_count = sum("checkpoint" in row for row in rows)

    checkpoint_value_ok = (
        checkpoint_present_count == len(rows)
        and set(checkpoint_values) == {item["checkpoint_value"]}
    )

    record_ok = len(rows) == 500
    ids_ok = missing_ids == 0 and duplicate_ids == 0
    correct_ok = correct_bool_count == len(rows)
    status_ok = status_present_count == len(rows)

    print("SHA256:", actual_hash)
    print("EXPECTED_SHA256_MATCH:", hash_ok)
    print("RECORDS:", len(rows))
    print("UNIQUE_PROBLEM_IDS:", len(set(x for x in id_values if x)))
    print("MISSING_PROBLEM_IDS:", missing_ids)
    print("DUPLICATE_PROBLEM_IDS:", duplicate_ids)
    print("TOP_LEVEL_KEYS:", keys)
    print("CORRECT_TYPES:", dict(correct_types))
    print("CORRECT_BOOLEAN_ROWS:", correct_bool_count)
    print("STATUS_ROWS:", status_present_count)
    print("STATUS_VALUES:", dict(status_values))
    print("CHECKPOINT_ROWS:", checkpoint_present_count)
    print("CHECKPOINT_VALUES:", dict(checkpoint_values))
    print("EXPECTED_CHECKPOINT_VALUE_MATCH:", checkpoint_value_ok)

    print("P2_EVALUATOR_STATUS_CONTRACT:", "PASS" if status_ok else "FAIL")
    print("LEGACY_CORRECT_BOOL_CONTRACT:", "PASS" if correct_ok else "FAIL")

    row_pass = (
        hash_ok and record_ok and ids_ok
        and correct_ok and checkpoint_value_ok
        and checkpoint.is_dir()
    )
    all_pass = all_pass and row_pass

    report.append({
        "checkpoint": item["name"],
        "round": item["round"],
        "prediction_file": str(path),
        "checkpoint_dir": str(checkpoint),
        "sha256": actual_hash,
        "expected_sha256_match": hash_ok,
        "records": len(rows),
        "unique_problem_ids": len(set(x for x in id_values if x)),
        "missing_problem_ids": missing_ids,
        "duplicate_problem_ids": duplicate_ids,
        "keys": keys,
        "correct_types": dict(correct_types),
        "status_rows": status_present_count,
        "status_values": dict(status_values),
        "checkpoint_values": dict(checkpoint_values),
        "p2_status_contract_pass": status_ok,
        "legacy_correct_bool_contract_pass": correct_ok,
        "checkpoint_value_match": checkpoint_value_ok,
        "checkpoint_dir_exists": checkpoint.is_dir(),
        "row_audit_pass": row_pass,
    })

out = MANUAL / "reports" / "p1p2_integration" / "b4_seed13_prediction_schema_audit.json"
out.write_text(json.dumps({
    "method": "B4",
    "seed": 13,
    "checkpoint_count": len(report),
    "overall_pass": all_pass and len(report) == 3,
    "results": report,
}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

print("\n" + "=" * 88)
print("SCHEMA_AUDIT_REPORT:", out)
print("CHECKPOINTS_AUDITED:", len(report))
print("OVERALL:", "PASS" if all_pass and len(report) == 3 else "FAIL")
