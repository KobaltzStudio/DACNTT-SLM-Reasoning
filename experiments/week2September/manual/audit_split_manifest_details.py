import hashlib
import json
from pathlib import Path

ROOT = Path(r"C:\Users\PC - NGHI\Desktop\Pipeline\P2\experiments\week2September\manual")

FILES = {
    "working_tree": ROOT / "splits" / "split_manifest.json",
    "p1_staging": ROOT / "integration_staging" / "P1" / "splits" / "split_manifest.json",
    "p1p2_vfinal": ROOT / "splits" / "p1p2_vfinal_2026-11-16" / "split_manifest.json",
    "config_v2": ROOT / "config" / "experiment_config.json",
    "config_v1": ROOT / "config" / "experiment_config_v1.json",
}

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def load_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))

def summarize(obj):
    if not isinstance(obj, dict):
        return {"root_type": type(obj).__name__}

    result = {"root_keys": sorted(obj.keys())}

    # Print potentially relevant split metadata without assuming a fixed schema.
    for key, value in obj.items():
        key_lower = key.lower()
        if any(token in key_lower for token in (
            "seed", "count", "size", "split", "hash", "version",
            "dev", "test", "train", "manifest", "source"
        )):
            result[key] = value

    return result

print("=== FILE HASHES AND SUMMARIES ===")
loaded = {}

for name, path in FILES.items():
    print(f"\n[{name}]")
    print(f"path={path}")
    print(f"exists={path.is_file()}")

    if not path.is_file():
        continue

    print(f"sha256={sha256(path)}")

    try:
        obj = load_json(path)
        loaded[name] = obj

        if name.startswith("config_"):
            print(json.dumps({
                "config_version": obj.get("config_version"),
                "status": obj.get("status"),
                "declared_split": obj.get("splits", {}).get("manifest"),
                "declared_split_sha256": obj.get("splits", {}).get("manifest_sha256"),
                "seeds": obj.get("seeds"),
                "sources": obj.get("sources"),
            }, indent=2, ensure_ascii=False))
        else:
            print(json.dumps(summarize(obj), indent=2, ensure_ascii=False))

    except Exception as exc:
        print(f"JSON_ERROR={exc}")

print("\n=== WORKING TREE VS P1 STAGING ===")
if "working_tree" in loaded and "p1_staging" in loaded:
    print("JSON_OBJECT_EQUAL:",
          loaded["working_tree"] == loaded["p1_staging"])

print("\n=== CONFIG DECLARED HASH CHECKS ===")
for config_name in ("config_v1", "config_v2"):
    if config_name not in loaded:
        continue

    expected = loaded[config_name].get("splits", {}).get("manifest_sha256", "")
    expected = expected.lower()

    for manifest_name in ("working_tree", "p1_staging", "p1p2_vfinal"):
        if manifest_name not in FILES or not FILES[manifest_name].is_file():
            continue

        actual = sha256(FILES[manifest_name]).lower()
        print(
            f"{config_name} -> {manifest_name}: "
            f"expected={expected}, actual={actual}, match={expected == actual}"
        )
