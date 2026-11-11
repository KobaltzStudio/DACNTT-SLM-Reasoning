import hashlib
import json
from pathlib import Path

paths = [
    Path("splits/split_manifest.json"),
    Path("config/experiment_config.json"),
    Path("config/experiment_config_v1.json"),
]

for p in paths:
    if not p.exists():
        print(f"[MISSING] {p}")
        continue

    digest = hashlib.sha256(p.read_bytes()).hexdigest()
    print(f"{p}: {digest}")

config = json.loads(Path("config/experiment_config.json").read_text(encoding="utf-8"))
print("\nExpected manifest SHA256:")
print(config["splits"]["manifest_sha256"])
