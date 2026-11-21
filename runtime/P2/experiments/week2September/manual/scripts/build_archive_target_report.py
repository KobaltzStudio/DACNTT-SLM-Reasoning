from pathlib import Path
import csv
import re

BASE = Path(
    r"C:\Users\PC - NGHI\Desktop\Pipeline\P2"
    r"\experiments\week2September\manual"
)

AUDIT = BASE / "reports/p1p2_integration/checkpoint_inventory_audit"
SOURCE = AUDIT / "archive_member_inventory.csv"
OUT = AUDIT / "archive_target_report"

OUT.mkdir(parents=True, exist_ok=True)

if not SOURCE.exists():
    raise SystemExit(f"INVENTORY_NOT_FOUND: {SOURCE}")

with SOURCE.open("r", encoding="utf-8-sig", newline="") as f:
    rows = list(csv.DictReader(f))

TARGET_ARCHIVES = [
    r"runs\main\main.zip",
    r"integration_staging.zip",
    r"manual_P2_1.zip",
    r"manual_P2_2.zip",
    r"seed_13.zip",
    r"student_ckpt_001.zip",
    r"student_ckpt_002.zip",
    r"student_ckpt_003.zip",
    r"runs\pilot\pilot.zip",
    r"P1_extractor_v3_working_2026-11-14.zip",
]

def archive_matches(path, target):
    p = path.replace("/", "\\").lower()
    t = target.replace("/", "\\").lower()
    return p.endswith(t)

targets = [
    dict(row)
    for row in rows
    if any(
        archive_matches(row["archive_path"], target)
        for target in TARGET_ARCHIVES
    )
]

def classify(name):
    n = name.lower().replace("\\", "/")
    base = n.rsplit("/", 1)[-1]

    if re.search(
        r"eval_student.*dev.*\.jsonl$|eval_student.*\.jsonl$",
        base
    ):
        return "PREDICTION_JSONL"

    if base.endswith(".jsonl") and (
        "prediction" in n or "derived_prediction" in n
    ):
        return "PREDICTION_JSONL"

    if base in {"adapter_model.safetensors", "adapter_model.bin"}:
        return "CHECKPOINT_WEIGHT"

    if "train_log" in base:
        return "TRAIN_LOG"

    if base.endswith(".done") or "/.done/" in n:
        return "DONE_MARKER"

    if base == "adapter_config.json":
        return "ADAPTER_CONFIG"

    if base.endswith((".zip", ".7z", ".tar", ".gz")):
        return "NESTED_ARCHIVE"

    if "checkpoint" in n or "student_ckpt" in n:
        return "CHECKPOINT_METADATA"

    if "manifest" in n or "lineage" in n:
        return "MANIFEST_OR_LINEAGE"

    return "OTHER_RELEVANT"

for row in targets:
    row["classification"] = classify(row["member_path"])

fields = [
    "archive_path",
    "member_path",
    "size_bytes",
    "classification",
    "crc",
]

def save_csv(path, data):
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fields,
            extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(data)

save_csv(OUT / "target_archive_members.csv", targets)

categories = [
    "PREDICTION_JSONL",
    "CHECKPOINT_WEIGHT",
    "TRAIN_LOG",
    "DONE_MARKER",
    "ADAPTER_CONFIG",
    "NESTED_ARCHIVE",
    "CHECKPOINT_METADATA",
    "MANIFEST_OR_LINEAGE",
]

for category in categories:
    selected = [
        row for row in targets
        if row["classification"] == category
    ]
    save_csv(OUT / f"{category.lower()}.csv", selected)

print("TARGET_ARCHIVE_REPORT=CREATED")
print(f"TARGET_MEMBER_COUNT={len(targets)}")

for category in categories:
    count = sum(
        row["classification"] == category
        for row in targets
    )
    print(f"{category}={count}")

print(f"OUTPUT_DIR={OUT}")
