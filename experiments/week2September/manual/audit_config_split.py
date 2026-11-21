import hashlib
import json
from pathlib import Path

manual = Path(r"C:\Users\PC - NGHI\Desktop\Pipeline\P2\experiments\week2September\manual")

config_path = manual / "config" / "experiment_config.json"
split_path = manual / "splits" / "split_manifest.json"

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

config = json.loads(config_path.read_text(encoding="utf-8-sig"))

actual_config_hash = sha256(config_path)
actual_split_hash = sha256(split_path)
declared_split_hash = config["splits"]["manifest_sha256"].lower()

result = {
    "config_path": str(config_path),
    "config_sha256": actual_config_hash,
    "split_manifest_path": str(split_path),
    "actual_split_manifest_sha256": actual_split_hash,
    "declared_split_manifest_sha256": declared_split_hash,
    "split_hash_matches": actual_split_hash == declared_split_hash,
    "config_version": config.get("config_version"),
    "status": config.get("status"),
    "training_seeds": config.get("seeds", {}).get("training_seeds"),
    "optional_extra_seeds": config.get("seeds", {}).get("optional_extra_seeds"),
}

print(json.dumps(result, indent=2, ensure_ascii=False))
