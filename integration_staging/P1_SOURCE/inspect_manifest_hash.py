import hashlib
import json
from pathlib import Path

config_path = Path("config/experiment_config.json")
manifest_path = Path("splits/split_manifest.json")

config = json.loads(config_path.read_text(encoding="utf-8"))

actual_hash = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
expected_hash = config["splits"]["manifest_sha256"]

print("Manifest:", manifest_path)
print("Expected SHA256:", expected_hash)
print("Actual SHA256:  ", actual_hash)
print("Match:", expected_hash == actual_hash)

print("\nManifest file size:", manifest_path.stat().st_size)
print("Config split section:")
print(json.dumps(config["splits"], indent=2, ensure_ascii=False))
