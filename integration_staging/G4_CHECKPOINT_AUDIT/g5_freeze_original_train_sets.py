import hashlib
import json
import shutil
from pathlib import Path

AUDIT = Path(
    r"C:\Users\PC - NGHI\Desktop\Pipeline\P2\integration_staging\G4_CHECKPOINT_AUDIT"
)

SOURCE_ROOT = Path(
    r"C:\Users\PC - NGHI\Desktop\Pipeline\P2\experiments\week2September\manual\integration_staging\P1\reports\task7\B4\seed_13"
)

DEST_ROOT = AUDIT / "original_train_sets"

EXPECTED = {
    "S1": {
        "round": "round_000",
        "sha256": "614816f15b980f9958dd1747a3c0773171d8112ad167e116b7a7651d9623a006",
    },
    "S2": {
        "round": "round_001",
        "sha256": "cb82cb58ed58a92a8fd0dd33b09322e99191ecd048daf63a36b5ea4182898e1a",
    },
    "S3": {
        "round": "round_002",
        "sha256": "f16cb78cbdaf4ce5280d79c552adab5ec57f56ca26a3796b02995f0de2441e0e",
    },
}

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

if DEST_ROOT.exists():
    raise SystemExit(
        f"STOP: destination already exists; refusing to overwrite: {DEST_ROOT}"
    )

DEST_ROOT.mkdir(parents=True)

manifest = {
    "purpose": "Immutable audit copies of original training-set files",
    "source_root": str(SOURCE_ROOT),
    "destination_root": str(DEST_ROOT),
    "stages": {},
}

print("========== FREEZE ORIGINAL TRAIN SETS ==========")

for stage, spec in EXPECTED.items():
    source = SOURCE_ROOT / spec["round"] / "train_set.json"
    destination_dir = DEST_ROOT / stage
    destination = destination_dir / "train_set.json"

    if not source.is_file():
        raise SystemExit(f"STOP: source missing: {source}")

    source_hash = sha256(source)
    if source_hash != spec["sha256"]:
        raise SystemExit(
            f"STOP: source hash mismatch for {stage}: "
            f"{source_hash} != {spec['sha256']}"
        )

    destination_dir.mkdir(parents=True)
    shutil.copy2(source, destination)

    copied_hash = sha256(destination)
    if copied_hash != spec["sha256"]:
        raise SystemExit(
            f"STOP: copied file hash mismatch for {stage}: "
            f"{copied_hash} != {spec['sha256']}"
        )

    manifest["stages"][stage] = {
        "source_path": str(source),
        "frozen_path": str(destination),
        "expected_sha256": spec["sha256"],
        "source_sha256": source_hash,
        "frozen_sha256": copied_hash,
        "size_bytes": destination.stat().st_size,
        "verification": "PASS",
    }

    print(f"{stage}_SOURCE_SHA256={source_hash}")
    print(f"{stage}_FROZEN_SHA256={copied_hash}")
    print(f"{stage}_COPY_VERIFICATION=PASS")
    print(f"{stage}_FROZEN_PATH={destination}")

manifest["overall_status"] = "PASS"

manifest_path = DEST_ROOT / "original_train_sets_manifest.json"
manifest_path.write_text(
    json.dumps(manifest, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

print()
print("FREEZE_STATUS=PASS")
print(f"MANIFEST={manifest_path}")
