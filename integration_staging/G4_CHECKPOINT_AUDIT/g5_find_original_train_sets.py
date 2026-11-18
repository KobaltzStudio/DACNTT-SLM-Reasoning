import hashlib
import json
import os
from pathlib import Path

EXPECTED = {
    "S1": "614816f15b980f9958dd1747a3c0773171d8112ad167e116b7a7651d9623a006",
    "S2": "cb82cb58ed58a92a8fd0dd33b09322e99191ecd048daf63a36b5ea4182898e1a",
    "S3": "f16cb78cbdaf4ce5280d79c552adab5ec57f56ca26a3796b02995f0de2441e0e",
}

ROOTS = [
    Path(r"C:\Users\PC - NGHI\Desktop\Pipeline"),
    Path(r"C:\KLTN-SLM-Reasoning"),
]

EXCLUDED = {
    ".venv", "venv", "__pycache__", "node_modules",
    ".git", "site-packages", "AppData",
}

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

expected_to_stage = {v: k for k, v in EXPECTED.items()}
matches = {k: [] for k in EXPECTED}
scanned = 0
errors = []

print("========== ORIGINAL TRAIN_SET SEARCH ==========")

for root in ROOTS:
    if not root.exists():
        print(f"ROOT_NOT_FOUND={root}")
        continue

    print(f"SCANNING_ROOT={root}")

    for current, dirs, files in os.walk(root):
        dirs[:] = [
            d for d in dirs
            if d not in EXCLUDED
        ]

        if "train_set.json" not in files:
            continue

        path = Path(current) / "train_set.json"
        scanned += 1

        try:
            digest = sha256(path)
            if digest in expected_to_stage:
                stage = expected_to_stage[digest]
                matches[stage].append(str(path))
                print(f"EXACT_MATCH_{stage}={path}")
        except Exception as exc:
            errors.append((str(path), str(exc)))

print()
print(f"TRAIN_SET_FILES_SCANNED={scanned}")

for stage in ("S1", "S2", "S3"):
    print(f"{stage}_EXACT_MATCH_COUNT={len(matches[stage])}")
    for path in matches[stage]:
        print(f"{stage}_MATCH_PATH={path}")

print(f"SCAN_ERRORS={len(errors)}")
for path, error in errors[:20]:
    print(f"SCAN_ERROR={path} | {error}")

report = {
    "expected_hashes": EXPECTED,
    "roots": [str(x) for x in ROOTS],
    "files_scanned": scanned,
    "matches": matches,
    "errors": errors,
}

output = Path(__file__).with_name("g5_original_train_set_search.json")
output.write_text(
    json.dumps(report, indent=2, ensure_ascii=False),
    encoding="utf-8"
)

print(f"REPORT={output}")
