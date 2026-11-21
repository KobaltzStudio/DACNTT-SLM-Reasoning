import hashlib
import json
from pathlib import Path
from collections import Counter

REPO = Path(
    r"C:\Users\PC - NGHI\Desktop\Pipeline\P2"
)

MANUAL = REPO / "experiments/week2September/manual"

CHECKPOINT_ROOT = (
    REPO / "integration_staging/P1/models/task7/B4/seed_13"
)

TRAIN_SET_ROOT = (
    MANUAL / "integration_staging/P1/reports/task7/B4/seed_13"
)

CHECKPOINT_LOG = (
    MANUAL / "runs/main/B4_seed13/checkpoint_log.jsonl"
)

EXPECTED = {
    "round_000": "614816f15b980f9958dd1747a3c0773171d8112ad167e116b7a7651d9623a006",
    "round_001": "cb82cb58ed58a92a8fd0dd33b09322e99191ecd048daf63a36b5ea4182898e1a",
    "round_002": "f16cb78cbdaf4ce5280d79c552adab5ec57f56ca26a3796b02995f0de2441e0e",
}

EXPECTED_CONFIG = (
    "17cf4b837dc42ac5145aea762847ca5dfba4bae58d253560"
    "b3b0dd6a254b73c5"
)

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))

def read_jsonl(path):
    records = []
    errors = []

    for line_no, line in enumerate(
        path.read_text(encoding="utf-8-sig").splitlines(), 1
    ):
        if not line.strip():
            continue

        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            errors.append((line_no, str(exc)))

    return records, errors

print("=== ROOTS ===")
print("REPO:", REPO)
print("MANUAL:", MANUAL)
print("CHECKPOINT_ROOT:", CHECKPOINT_ROOT)
print("CHECKPOINT_ROOT_EXISTS:", CHECKPOINT_ROOT.is_dir())

print("\n=== TRAIN LOGS ===")

train_logs = {}

if CHECKPOINT_ROOT.is_dir():
    for path in sorted(CHECKPOINT_ROOT.rglob("train_log.json")):
        print("\nTRAIN_LOG:", path)
        print("SHA256:", sha256(path))

        try:
            data = read_json(path)
        except Exception as exc:
            print("JSON_ERROR:", repr(exc))
            continue

        for key in (
            "round",
            "seed",
            "training_seed",
            "data_order_seed",
            "config_sha256",
            "config_hash",
            "train_set_sha256",
            "n_examples",
            "epochs",
            "steps",
            "learning_rate",
            "checkpoint_parent",
            "checkpoint",
        ):
            if key in data:
                print(f"{key}:", data[key])

        train_logs[path.parent.name] = data
else:
    print("ERROR: CHECKPOINT_ROOT_NOT_FOUND")

print("\n=== TRAIN SETS ===")

train_sets = {}

for round_name, expected_hash in EXPECTED.items():
    path = TRAIN_SET_ROOT / round_name / "train_set.json"

    print(f"\n{round_name}:")
    print("PATH:", path)
    print("EXISTS:", path.is_file())

    if not path.is_file():
        continue

    actual_hash = sha256(path)
    print("EXPECTED_SHA256:", expected_hash)
    print("ACTUAL_SHA256:", actual_hash)
    print("HASH_MATCH:", actual_hash == expected_hash)

    data = read_json(path)
    train_sets[round_name] = data

    print("ROOT_KEYS:", sorted(data.keys()))
    print("CONFIG_SHA256:", data.get("config_sha256"))
    print("ROUND_FIELD:", data.get("round"))
    print("METHOD:", data.get("method"))
    print("TRAINING_SEED:", data.get("training_seed"))
    print("SOURCE_CHECKPOINT:", data.get("source_checkpoint"))
    print("N_TRAJECTORIES:", data.get("n_trajectories"))

    ids = data.get("trajectory_ids", [])
    tokens = data.get("trajectory_tokens", [])

    print("TRAJECTORY_IDS_TYPE:", type(ids).__name__)
    print("TRAJECTORY_IDS_COUNT:", len(ids) if isinstance(ids, list) else "N/A")
    print(
        "TRAJECTORY_IDS_UNIQUE:",
        len(set(ids)) if isinstance(ids, list) else "N/A"
    )
    print("FIRST_10_IDS:", ids[:10] if isinstance(ids, list) else ids)

    print("TRAJECTORY_TOKENS_TYPE:", type(tokens).__name__)
    print("TRAJECTORY_TOKENS_COUNT:", len(tokens) if isinstance(tokens, list) else "N/A")

    if isinstance(ids, list):
        print("DUPLICATE_IDS:", len(ids) - len(set(ids)))

print("\n=== CHECKPOINT LOG ===")

checkpoint_records = []

if CHECKPOINT_LOG.is_file():
    print("PATH:", CHECKPOINT_LOG)
    print("SHA256:", sha256(CHECKPOINT_LOG))

    checkpoint_records, errors = read_jsonl(CHECKPOINT_LOG)

    print("RECORDS:", len(checkpoint_records))
    print("PARSE_ERRORS:", errors)

    for row in checkpoint_records:
        checkpoint = row.get("checkpoint")
        selected = row.get("selected_trajectory_ids", [])

        print("\nCHECKPOINT:", checkpoint)
        print("ROUND:", row.get("round"))
        print("PARENT:", row.get("parent_checkpoint"))
        print("METHOD:", row.get("method"))
        print("SEED:", row.get("training_seed"))
        print("DATA_ORDER_SEED:", row.get("data_order_seed"))
        print("CONFIG_HASH:", row.get("config_hash"))
        print("CUMULATIVE_TOKENS:", row.get("cumulative_training_tokens"))
        print("CUMULATIVE_STEPS:", row.get("cumulative_optimization_steps"))
        print("SELECTED_COUNT:", len(selected))
        print("SELECTED_UNIQUE:", len(set(selected)))
else:
    print("CHECKPOINT_LOG_NOT_FOUND")

print("\n=== TRAIN SET vs CHECKPOINT SELECTED IDS ===")

for index, round_name in enumerate(
    ("round_000", "round_001", "round_002"), start=1
):
    train_data = train_sets.get(round_name)

    if train_data is None:
        continue

    train_ids = train_data.get("trajectory_ids", [])

    checkpoint_name = f"student_ckpt_{index:03d}"

    checkpoint_row = next(
        (
            row for row in checkpoint_records
            if row.get("checkpoint") == checkpoint_name
        ),
        None,
    )

    print(f"\n{round_name} -> {checkpoint_name}")

    if checkpoint_row is None:
        print("CHECKPOINT_RECORD_MISSING")
        continue

    selected_ids = checkpoint_row.get("selected_trajectory_ids", [])

    train_set = set(train_ids)
    selected_set = set(selected_ids)

    print("TRAIN_SET_COUNT:", len(train_ids))
    print("CHECKPOINT_SELECTED_COUNT:", len(selected_ids))
    print("TRAIN_SET_UNIQUE:", len(train_set))
    print("CHECKPOINT_SELECTED_UNIQUE:", len(selected_set))
    print("INTERSECTION:", len(train_set & selected_set))
    print("TRAIN_ONLY:", len(train_set - selected_set))
    print("CHECKPOINT_ONLY:", len(selected_set - train_set))
    print("EXACT_SET_MATCH:", train_set == selected_set)

    if train_set != selected_set:
        print("TRAIN_ONLY_SAMPLE:", sorted(train_set - selected_set)[:10])
        print("CHECKPOINT_ONLY_SAMPLE:", sorted(selected_set - train_set)[:10])

print("\n=== CONFIG HASH CONSISTENCY ===")

for round_name, data in train_sets.items():
    print(
        round_name,
        "train_set.config_sha256=",
        data.get("config_sha256"),
        "matches_expected=",
        data.get("config_sha256") == EXPECTED_CONFIG,
    )

for directory, data in train_logs.items():
    print(
        directory,
        "train_log.config_sha256=",
        data.get("config_sha256"),
        "matches_expected=",
        data.get("config_sha256") == EXPECTED_CONFIG,
    )

print("\nACTUAL_TRAINING_LINEAGE_AUDIT: COMPLETE")
