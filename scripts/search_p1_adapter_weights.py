from pathlib import Path
import hashlib
import csv
import os

ROOT = Path(r"C:\Users\PC - NGHI")
OUTPUT = Path(r"C:\Users\PC - NGHI\Desktop\P1_weight_search_corrected_2026-11-16.csv")

EXCLUDED = {
    ".venv",
    "venv",
    "node_modules",
    "appdata",
    ".cache",
    "site-packages",
    "__pycache__",
}

TARGET_NAMES = {
    "adapter_model.safetensors",
    "adapter_model.bin",
}

EXPECTED = {
    "8f50d3ab6772c7c01d0c244fd661348a0f61164916cf5396d4f916d7c38c6398",
    "759ea14d7a3953b609a70b06b14515d2b309ee209f00843bff6d70c8508a71fc",
    "22d99c60743ed2897586ff22601ff7e8491dbf6495bbac8e0edd5c88880b7106",
}

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().lower()

def main():
    rows = []

    for current, dirs, files in os.walk(ROOT):
        dirs[:] = [
            d for d in dirs
            if d.lower() not in EXCLUDED
        ]

        current_path = Path(current)
        current_lower = str(current_path).lower()

        for filename in files:
            path = current_path / filename
            name_lower = filename.lower()

            is_adapter = name_lower in TARGET_NAMES
            is_safetensors_in_p1_context = (
                name_lower.endswith(".safetensors")
                and any(
                    token in current_lower
                    for token in ("p1", "checkpoint", "student_ckpt")
                )
            )

            if not (is_adapter or is_safetensors_in_p1_context):
                continue

            try:
                digest = sha256(path)
                rows.append({
                    "file": str(path),
                    "bytes": path.stat().st_size,
                    "sha256": digest,
                    "matches_expected_checkpoint": digest in EXPECTED,
                })
            except (OSError, PermissionError) as exc:
                print("UNREADABLE:", path, repr(exc))

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "file",
                "bytes",
                "sha256",
                "matches_expected_checkpoint",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    print("SEARCH_COMPLETE")
    print("MATCHED_FILES:", len(rows))
    print("EXPECTED_HASH_MATCHES:", sum(
        row["matches_expected_checkpoint"] for row in rows
    ))
    print("REPORT:", OUTPUT)

    for row in rows:
        print(
            "FILE:", row["file"],
            "| BYTES:", row["bytes"],
            "| SHA256:", row["sha256"],
            "| EXPECTED_MATCH:", row["matches_expected_checkpoint"],
        )

if __name__ == "__main__":
    main()
