import hashlib
import json
from pathlib import Path
from collections import Counter

ROOT = Path(".").resolve()

EXPECTED_CONFIG_SHA256 = (
    "17cf4b837dc42ac5145aea762847ca5dfba4bae58d253560"
    "b3b0dd6a254b73c5"
)

EXPECTED_TRAIN_SET_HASHES = {
    "round_000": "614816f15b980f9958dd1747a3c0773171d8112ad167e116b7a7651d9623a006",
    "round_001": "cb82cb58ed58a92a8fd0dd33b09322e99191ecd048daf63a36b5ea4182898e1a",
    "round_002": "f16cb78cbdaf4ce5280d79c552adab5ec57f56ca26a3796b02995f0de2441e0e",
}

BASE = ROOT / "integration_staging/P1/reports/task7/B4/seed_13"
RUNS = ROOT / "runs/main/B4_seed13"

TRAIN_LOG_ROOT = ROOT / "integration_staging/P1/models/task7/B4/seed_13"

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load_json(path):
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)

def load_jsonl(path):
    records = []
    errors = []

    with path.open("r", encoding="utf-8-sig") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                errors.append((line_no, str(exc)))

    return records, errors

def collect_values(obj, target_key):
    values = []

    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == target_key:
                values.append(value)
            values.extend(collect_values(value, target_key))

    elif isinstance(obj, list):
        for item in obj:
            values.extend(collect_values(item, target_key))

    return values

def print_hash_distribution(label, records, field):
    values = [
        str(row.get(field))
        for row in records
        if row.get(field) is not None
    ]

    print(f"{label}_{field.upper()}_COUNT:", len(values))

    for value, count in Counter(values).items():
        print(f"{label}_{field.upper()}:", value, "COUNT:", count)

def audit_jsonl(path, label):
    print(f"\n=== {label} ===")
    print("PATH:", path)
    print("EXISTS:", path.is_file())

    if not path.is_file():
        return []

    print("SHA256:", sha256(path))
    records, errors = load_jsonl(path)

    print("RECORD_COUNT:", len(records))
    print("PARSE_ERRORS:", len(errors))

    for error in errors[:5]:
        print("PARSE_ERROR:", error)

    if records:
        print("FIRST_RECORD_KEYS:", sorted(records[0].keys()))

    print_hash_distribution(label, records, "config_hash")

    if any("config_sha256" in row for row in records):
        print_hash_distribution(label, records, "config_sha256")

    if any("round" in row for row in records):
        print("ROUND_COUNTS:", dict(Counter(str(r.get("round")) for r in records)))

    if any("checkpoint" in row for row in records):
        for row in records:
            print(
                "CHECKPOINT_RECORD:",
                "checkpoint=", row.get("checkpoint"),
                "round=", row.get("round"),
                "parent=", row.get("parent_checkpoint"),
                "method=", row.get("method"),
                "seed=", row.get("training_seed"),
                "config_hash=", row.get("config_hash"),
            )

    return records

print("=== CONFIG FILE ===")

config_path = ROOT / "integration_staging/P1/config/experiment_config.json"
print("PATH:", config_path)
print("EXISTS:", config_path.is_file())

if config_path.is_file():
    actual = sha256(config_path)
    print("ACTUAL_SHA256:", actual)
    print("EXPECTED_SHA256:", EXPECTED_CONFIG_SHA256)
    print("MATCH:", actual == EXPECTED_CONFIG_SHA256)

print("\n=== TRAIN LOGS ===")

if TRAIN_LOG_ROOT.exists():
    for path in sorted(TRAIN_LOG_ROOT.rglob("train_log.json")):
        try:
            data = load_json(path)
            print("\nTRAIN_LOG:", path)
            print("SHA256:", sha256(path))
            print("config_sha256:", data.get("config_sha256"))
            print("round:", data.get("round"))
            print("seed:", data.get("seed"))
            print("data_order_seed:", data.get("data_order_seed"))
            print("train_set_sha256:", data.get("train_set_sha256"))
            print("train_set:", data.get("train_set"))
        except Exception as exc:
            print("TRAIN_LOG_READ_ERROR:", path, repr(exc))
else:
    print("TRAIN_LOG_ROOT_NOT_FOUND:", TRAIN_LOG_ROOT)

print("\n=== STAGING SELECTION LOG ===")

staging_selection = audit_jsonl(
    BASE / "selection_log.jsonl",
    "STAGING_SELECTION"
)

print("\n=== CHECKPOINT LOG ===")

checkpoint_records = audit_jsonl(
    RUNS / "checkpoint_log.jsonl",
    "CHECKPOINT_LOG"
)

print("\n=== PER-ROUND SELECTION LOGS ===")

round_records = {}

for round_name in ("round_000", "round_001", "round_002"):
    path = RUNS / round_name / "selection_log.jsonl"
    records = audit_jsonl(path, round_name.upper())
    round_records[round_name] = records

print("\n=== TRAIN SET CONTENT / HASH CROSS-CHECK ===")

for round_name, expected_hash in EXPECTED_TRAIN_SET_HASHES.items():
    path = BASE / round_name / "train_set.json"

    print(f"\n{round_name}:")
    print("PATH:", path)
    print("EXISTS:", path.is_file())

    if not path.is_file():
        continue

    actual_hash = sha256(path)
    print("EXPECTED_SHA256:", expected_hash)
    print("ACTUAL_SHA256:", actual_hash)
    print("HASH_MATCH:", actual_hash == expected_hash)

    try:
        data = load_json(path)
        print("ROOT_TYPE:", type(data).__name__)

        if isinstance(data, dict):
            print("ROOT_KEYS:", sorted(data.keys()))

        trajectory_ids = collect_values(data, "trajectory_id")
        unique_ids = set(str(x) for x in trajectory_ids if x is not None)

        print("TRAJECTORY_ID_OCCURRENCES:", len(trajectory_ids))
        print("UNIQUE_TRAJECTORY_IDS:", len(unique_ids))
        print("FIRST_10_TRAJECTORY_IDS:", sorted(unique_ids)[:10])

    except Exception as exc:
        print("TRAIN_SET_PARSE_ERROR:", repr(exc))

print("\n=== CHECKPOINT SELECTED IDS SUMMARY ===")

for row in checkpoint_records:
    checkpoint = row.get("checkpoint")
    selected = row.get("selected_trajectory_ids")

    if isinstance(selected, list):
        print(
            "CHECKPOINT:",
            checkpoint,
            "ROUND:",
            row.get("round"),
            "SELECTED_COUNT:",
            len(selected),
            "UNIQUE_SELECTED:",
            len(set(str(x) for x in selected)),
            "CONFIG_HASH:",
            row.get("config_hash"),
        )

print("\n=== AUDIT STATUS ===")
print("CONFIG_HASH_LINEAGE_AUDIT: COMPLETED")
print("NOTE: COMPLETED DOES NOT MEAN PASS; inspect the hash differences above.")
