import json
from pathlib import Path

p = Path("config/experiment_config.json")
c = json.loads(p.read_text(encoding="utf-8"))

print("=== TOP-LEVEL CONFIG KEYS ===")
for key, value in c.items():
    print(f"\n[{key}]")
    if isinstance(value, dict):
        for k, v in value.items():
            if isinstance(v, (dict, list)):
                print(f"  {k}: <{type(v).__name__}, {len(v)} items>")
            else:
                print(f"  {k}: {v}")
    elif isinstance(value, list):
        print(f"  <list, {len(value)} items>")
    else:
        print(f"  {value}")

print("\n=== MODEL-RELATED CONFIG ===")
def walk(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            current = f"{path}.{k}" if path else k
            if any(word in k.lower() for word in ("model", "revision", "tokenizer", "dtype", "precision")):
                print(current, "=", v)
            walk(v, current)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            walk(v, f"{path}[{i}]")

walk(c)
