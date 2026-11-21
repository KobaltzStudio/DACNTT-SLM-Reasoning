import hashlib
import json
from pathlib import Path

root = Path(r"C:\Users\PC - NGHI\Desktop\Pipeline\P2\experiments\week2September\manual")

paths = {
    "working_config": root / "config" / "experiment_config.json",
    "staging_p1_config": root / "integration_staging" / "P1" / "config" / "experiment_config.json",
    "working_split": root / "splits" / "split_manifest.json",
    "staging_split": root / "integration_staging" / "P1" / "splits" / "split_manifest.json",
}

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

loaded = {}

for name, path in paths.items():
    print(f"\n[{name}]")
    print("path:", path)
    if not path.is_file():
        print("MISSING")
        continue

    digest = sha256(path)
    print("sha256:", digest)

    if path.suffix == ".json":
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
        loaded[name] = obj

        if "splits" in obj:
            print("declared_split:", obj["splits"].get("manifest"))
            print("declared_split_sha256:", obj["splits"].get("manifest_sha256"))
        else:
            print("declared_split:", obj.get("declared_split"))
            print("declared_split_sha256:", obj.get("declared_split_sha256"))

if "working_config" in loaded and "staging_p1_config" in loaded:
    a = loaded["working_config"]
    b = loaded["staging_p1_config"]

    print("\n[CONFIG STRUCTURAL DIFF]")
    keys = sorted(set(a) | set(b))
    for key in keys:
        if a.get(key) != b.get(key):
            print(f"\nDIFFERENT KEY: {key}")
            print("WORKING:")
            print(json.dumps(a.get(key), indent=2, ensure_ascii=False))
            print("STAGING:")
            print(json.dumps(b.get(key), indent=2, ensure_ascii=False))
    if a == b:
        print("CONFIG_OBJECTS_IDENTICAL=True")
