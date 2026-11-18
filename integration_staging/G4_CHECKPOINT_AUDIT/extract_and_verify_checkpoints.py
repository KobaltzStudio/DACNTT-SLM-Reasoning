from __future__ import annotations

import csv
import hashlib
import json
import zipfile
from pathlib import Path

P2 = Path(r"C:\Users\PC - NGHI\Desktop\Pipeline\P2")
AUDIT = P2 / "integration_staging" / "G4_CHECKPOINT_AUDIT"
DEST_ROOT = AUDIT / "extracted_checkpoints" / "B4_seed13"

CHECKPOINTS = {
    "S1": {
        "zip": P2 / "integration_staging/P1/models/task7/B4/seed_13/student_ckpt_001/student_ckpt_001.zip",
        "expected_zip_sha256": "851742c95cdc1dba0333112f35f2f32d7e8cfe2e4235ae2c5ddc535bc2955615",
    },
    "S2": {
        "zip": P2 / "integration_staging/P1/models/task7/B4/seed_13/student_ckpt_002/student_ckpt_002.zip",
        "expected_zip_sha256": "8ae764306b33f9456ffd18b09b4824784a87b1e827d15178e8b26bdcbe307f6f",
    },
    "S3": {
        "zip": P2 / "integration_staging/P1/models/task7/B4/seed_13/student_ckpt_003/student_ckpt_003.zip",
        "expected_zip_sha256": "cb55d9d34244f24964882f71a5654744d3d7cac8ca2ed6d7ebe77deb36c968df",
    },
}

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def checkpoint_directory_hash(root: Path) -> str:
    files = sorted(p for p in root.rglob("*") if p.is_file())
    if not files:
        raise ValueError(f"Empty checkpoint directory: {root}")

    digest = hashlib.sha256()
    for path in files:
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(sha256_file(path).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()

def main() -> None:
    AUDIT.mkdir(parents=True, exist_ok=True)

    if DEST_ROOT.exists():
        raise FileExistsError(
            f"Destination already exists; refusing to overwrite: {DEST_ROOT}"
        )

    DEST_ROOT.mkdir(parents=True)

    results = []
    failed = False

    for checkpoint, info in CHECKPOINTS.items():
        archive = info["zip"]
        expected_zip_hash = info["expected_zip_sha256"]
        destination = DEST_ROOT / checkpoint

        print(f"\n========== {checkpoint} ==========")
        print(f"ZIP={archive}")

        if not archive.is_file():
            raise FileNotFoundError(f"Checkpoint ZIP missing: {archive}")

        actual_zip_hash = sha256_file(archive)
        zip_hash_match = actual_zip_hash == expected_zip_hash

        print(f"ZIP_SHA256={actual_zip_hash}")
        print(f"ZIP_SHA256_MATCH={zip_hash_match}")

        if not zip_hash_match:
            raise ValueError(f"{checkpoint}: ZIP SHA256 mismatch")

        with zipfile.ZipFile(archive, "r") as zf:
            bad_member = zf.testzip()
            if bad_member is not None:
                raise ValueError(
                    f"{checkpoint}: ZIP integrity failure at {bad_member}"
                )

            members = zf.infolist()
            unsafe = [
                item.filename for item in members
                if Path(item.filename).is_absolute()
                or ".." in Path(item.filename).parts
            ]
            if unsafe:
                raise ValueError(
                    f"{checkpoint}: unsafe ZIP paths: {unsafe}"
                )

            print(f"ZIP_ENTRIES={len(members)}")
            print("ZIP_INTEGRITY=OK")

            destination.mkdir(parents=True, exist_ok=False)
            zf.extractall(destination)

        extracted_files = sorted(
            p for p in destination.rglob("*") if p.is_file()
        )

        names = {p.name for p in extracted_files}
        required = {"adapter_config.json", "adapter_model.safetensors"}
        missing = required - names

        if missing:
            raise ValueError(
                f"{checkpoint}: missing required adapter files: {sorted(missing)}"
            )

        directory_hash = checkpoint_directory_hash(destination)

        print(f"EXTRACTED_FILE_COUNT={len(extracted_files)}")
        print(f"CHECKPOINT_DIRECTORY_SHA256={directory_hash}")
        print("REQUIRED_ADAPTER_FILES=PASS")

        for path in extracted_files:
            results.append({
                "checkpoint": checkpoint,
                "relative_path": path.relative_to(destination).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "zip_sha256": actual_zip_hash,
                "checkpoint_directory_sha256": directory_hash,
            })

        print(f"DESTINATION={destination}")

    csv_path = AUDIT / "extracted_checkpoint_file_hashes.csv"
    json_path = AUDIT / "extracted_checkpoint_verification.json"

    with csv_path.open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=[
                "checkpoint",
                "relative_path",
                "size_bytes",
                "sha256",
                "zip_sha256",
                "checkpoint_directory_sha256",
            ],
        )
        writer.writeheader()
        writer.writerows(results)

    report = {
        "status": "PASS",
        "checkpoint_count": len(CHECKPOINTS),
        "destination_root": str(DEST_ROOT),
        "checkpoints": {
            name: {
                "zip_path": str(info["zip"]),
                "expected_zip_sha256": info["expected_zip_sha256"],
                "actual_zip_sha256": sha256_file(info["zip"]),
                "directory": str(DEST_ROOT / name),
                "directory_sha256": checkpoint_directory_hash(
                    DEST_ROOT / name
                ),
                "files": [
                    {
                        "relative_path": p.relative_to(
                            DEST_ROOT / name
                        ).as_posix(),
                        "size_bytes": p.stat().st_size,
                        "sha256": sha256_file(p),
                    }
                    for p in sorted(
                        (DEST_ROOT / name).rglob("*")
                    )
                    if p.is_file()
                ],
            }
            for name, info in CHECKPOINTS.items()
        },
    }

    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("\n========== EXTRACTION SUMMARY ==========")
    print("EXTRACTION_STATUS=PASS")
    print(f"CHECKPOINTS_EXTRACTED={len(CHECKPOINTS)}")
    print(f"FILE_HASH_CSV={csv_path}")
    print(f"VERIFICATION_JSON={json_path}")

if __name__ == "__main__":
    main()
