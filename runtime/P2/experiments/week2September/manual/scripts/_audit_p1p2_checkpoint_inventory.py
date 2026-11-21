from pathlib import Path
import json
import hashlib
import csv

ROOT = Path(".")
MODEL_ROOT = ROOT / "models"
RUN_ROOT = ROOT / "runs" / "main"

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

print("===== ADAPTER WEIGHTS =====")
weights = []
if MODEL_ROOT.exists():
    weights = sorted(
        p for p in MODEL_ROOT.rglob("*")
        if p.is_file() and p.name in {
            "adapter_model.safetensors",
            "adapter_model.bin"
        }
    )

for p in weights:
    print(p, p.stat().st_size, sha256(p))

print("TOTAL_ADAPTER_WEIGHT_FILES:", len(weights))

print("\n===== TRAIN LOGS =====")
train_logs = sorted(RUN_ROOT.rglob("train_log.json")) if RUN_ROOT.exists() else []
print("TOTAL_TRAIN_LOGS:", len(train_logs))

for p in train_logs:
    try:
        obj = json.loads(p.read_text(encoding="utf-8-sig"))
        print(
            p,
            "steps=", obj.get("steps"),
            "n_examples=", obj.get("n_examples"),
            "train_set=", obj.get("train_set")
        )
    except Exception as e:
        print("[INVALID]", p, str(e))

print("\n===== CHECKPOINT LOGS =====")
checkpoint_logs = sorted(RUN_ROOT.glob("*/checkpoint_log.jsonl")) if RUN_ROOT.exists() else []
print("TOTAL_CHECKPOINT_LOGS:", len(checkpoint_logs))

for p in checkpoint_logs:
    rows = [
        json.loads(line)
        for line in p.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]
    print(p, "records=", len(rows))
    for row in rows:
        print(
            " ",
            row.get("checkpoint"),
            "parent=", row.get("parent_checkpoint"),
            "round=", row.get("round"),
            "method=", row.get("method"),
            "seed=", row.get("training_seed")
        )
