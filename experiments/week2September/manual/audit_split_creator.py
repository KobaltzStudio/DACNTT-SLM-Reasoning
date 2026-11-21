import hashlib
import json
from pathlib import Path

root = Path(r"C:\Users\PC - NGHI\Desktop\Pipeline\P2\experiments\week2September\manual")

paths = [
    root / "splits" / "split_manifest.json",
    root / "splits" / "p1p2_vfinal_2026-11-16" / "split_manifest.json",
]

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

for path in paths:
    print("\n" + "=" * 70)
    print("MANIFEST:", path)
    obj = json.loads(path.read_text(encoding="utf-8-sig"))

    for key in (
        "split_version",
        "created_by",
        "created_utc",
        "script_sha256",
        "source_split_manifest",
        "sources",
        "files",
        "counts",
        "rules",
        "policy",
    ):
        if key in obj:
            print(f"\n[{key}]")
            print(json.dumps(obj[key], indent=2, ensure_ascii=False))

    created_by = obj.get("created_by")
    if isinstance(created_by, str):
        candidate = root / created_by
        print("\nCREATOR_PATH:", candidate)
        if candidate.is_file():
            print("CREATOR_ACTUAL_SHA256:", sha256(candidate))
            print("CREATOR_MATCH:",
                  sha256(candidate).lower() == str(obj.get("script_sha256", "")).lower())
        else:
            print("CREATOR_FILE_NOT_FOUND")
