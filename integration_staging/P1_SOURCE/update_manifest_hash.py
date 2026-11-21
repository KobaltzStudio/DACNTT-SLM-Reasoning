import json
from pathlib import Path

config_path = Path("config/experiment_config.json")
config = json.loads(config_path.read_text(encoding="utf-8"))

config["splits"]["manifest_sha256"] = (
    "85f4559246542d197c427318afb3eefb8b8492573b69ac23e691fc19ce93bbda"
)

config_path.write_text(
    json.dumps(config, indent=2, ensure_ascii=False) + "\n",
    encoding="utf-8"
)

print("[UPDATED]", config_path)
print("New manifest SHA256:", config["splits"]["manifest_sha256"])
