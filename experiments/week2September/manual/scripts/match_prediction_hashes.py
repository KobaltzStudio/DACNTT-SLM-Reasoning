import csv
import hashlib
import json
from pathlib import Path

manual = Path(r"C:\Users\PC - NGHI\Desktop\Pipeline\P2\experiments\week2September\manual")
p1 = Path(r"C:\Users\PC - NGHI\Desktop\Pipeline\P1")
stage = manual / "integration_staging" / "P1"

inventory_files = [
    stage / "reports" / "capability" / "student_eval_2026-11-17" / "checkpoint_prediction_inventory.json",
    stage / "reports" / "learning_curve" / "2026-11-17" / "B4_seed13_checkpoint_inventory.json",
]

expected = {}

def walk(obj, context=""):
    if isinstance(obj, dict):
        checkpoint = obj.get("checkpoint", context)
        for key, value in obj.items():
            if key == "prediction_sha256" and isinstance(value, str) and len(value) == 64:
                expected.setdefault(value.lower(), []).append(str(checkpoint))
            elif isinstance(value, (dict, list)):
                walk(value, str(checkpoint))
    elif isinstance(obj, list):
        for item in obj:
            walk(item, context)

for inv in inventory_files:
    if inv.exists():
        walk(json.loads(inv.read_text(encoding="utf-8-sig")))

print("EXPECTED_PREDICTION_HASHES:", len(expected))

roots = [
    p1 / "reports",
    stage / "reports",
    manual / "runs" / "main",
]

matches = {key: [] for key in expected}
scanned = 0

for root in roots:
    if not root.exists():
        print("MISSING_ROOT:", root)
        continue

    for file in root.rglob("*.jsonl"):
        try:
            if not file.is_file():
                continue
            scanned += 1
            h = hashlib.sha256()
            with file.open("rb") as f:
                for block in iter(lambda: f.read(1024 * 1024), b""):
                    h.update(block)
            digest = h.hexdigest().lower()
            if digest in matches:
                matches[digest].append(str(file))
        except (OSError, PermissionError) as exc:
            print("READ_WARNING:", file, str(exc))

out = manual / "reports" / "p1p2_integration" / "prediction_hash_matches.csv"
out.parent.mkdir(parents=True, exist_ok=True)

with out.open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.writer(f)
    writer.writerow(["prediction_sha256", "checkpoint_context", "matched_file", "match_count"])
    for digest, contexts in expected.items():
        paths = matches[digest]
        writer.writerow([
            digest,
            ";".join(contexts),
            ";".join(paths),
            len(paths),
        ])

print("JSONL_FILES_SCANNED:", scanned)
print("HASHES_WITH_MATCH:", sum(bool(v) for v in matches.values()))
print("HASHES_WITHOUT_MATCH:", sum(not v for v in matches.values()))
print("HASH_MATCH_REPORT:", out)

for digest, contexts in expected.items():
    print("\nHASH:", digest)
    print("CONTEXT:", ";".join(contexts))
    for path in matches[digest]:
        print("MATCH:", path)
