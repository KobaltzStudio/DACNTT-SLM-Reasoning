import hashlib
import shutil
from pathlib import Path

AUDIT = Path(
    r"C:\Users\PC - NGHI\Desktop\Pipeline\P2\integration_staging\G4_CHECKPOINT_AUDIT"
)

PREFLIGHT = AUDIT / "g5_capability_preflight.py"
BACKUP = AUDIT / "g5_capability_preflight.py.before_original_train_sets.bak"

EXPECTED = {
    "S1": "614816f15b980f9958dd1747a3c0773171d8112ad167e116b7a7651d9623a006",
    "S2": "cb82cb58ed58a92a8fd0dd33b09322e99191ecd048daf63a36b5ea4182898e1a",
    "S3": "f16cb78cbdaf4ce5280d79c552adab5ec57f56ca26a3796b02995f0de2441e0e",
}

REPLACEMENTS = {
    '"train_set": MANUAL / "runs" / "main" / "B4_seed13" / "round_000" / "train_set.json",':
    '"train_set": AUDIT / "original_train_sets" / "S1" / "train_set.json",',

    '"train_set": MANUAL / "runs" / "main" / "B4_seed13" / "round_001" / "train_set.json",':
    '"train_set": AUDIT / "original_train_sets" / "S2" / "train_set.json",',

    '"train_set": MANUAL / "runs" / "main" / "B4_seed13" / "round_002" / "train_set.json",':
    '"train_set": AUDIT / "original_train_sets" / "S3" / "train_set.json",',
}

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

if not PREFLIGHT.is_file():
    raise SystemExit(f"STOP: preflight not found: {PREFLIGHT}")

if BACKUP.exists():
    raise SystemExit(
        f"STOP: backup already exists; refusing to overwrite: {BACKUP}"
    )

# Verify all frozen source files before changing the preflight.
for stage, expected_hash in EXPECTED.items():
    frozen = AUDIT / "original_train_sets" / stage / "train_set.json"

    if not frozen.is_file():
        raise SystemExit(f"STOP: frozen train_set missing: {frozen}")

    actual_hash = sha256(frozen)
    if actual_hash != expected_hash:
        raise SystemExit(
            f"STOP: {stage} frozen hash mismatch: "
            f"{actual_hash} != {expected_hash}"
        )

original = PREFLIGHT.read_text(encoding="utf-8-sig")
updated = original

for old, new in REPLACEMENTS.items():
    count = updated.count(old)
    if count != 1:
        raise SystemExit(
            f"STOP: expected exactly one occurrence, found {count}: {old}"
        )
    updated = updated.replace(old, new, 1)

# Create backup only after all preconditions pass.
shutil.copy2(PREFLIGHT, BACKUP)

# Write the updated script.
PREFLIGHT.write_text(updated, encoding="utf-8")

# Verify the updated file contains all new paths and none of the old paths.
written = PREFLIGHT.read_text(encoding="utf-8")

for old, new in REPLACEMENTS.items():
    if old in written or written.count(new) != 1:
        shutil.copy2(BACKUP, PREFLIGHT)
        raise SystemExit(
            f"PATCH_ROLLBACK: verification failed for replacement: {new}"
        )

print("========== PREFLIGHT PATCH ==========")
print("BACKUP_CREATED=True")
print(f"BACKUP_PATH={BACKUP}")
print("REPLACEMENTS=3")
print("S1_PATH=PASS")
print("S2_PATH=PASS")
print("S3_PATH=PASS")
print("FROZEN_TRAIN_SET_HASHES=PASS")
print("PATCH_STATUS=PASS")
print(f"PATCHED_FILE={PREFLIGHT}")
