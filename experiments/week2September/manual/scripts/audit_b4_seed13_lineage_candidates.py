import hashlib
import json
from pathlib import Path

ROOT = Path(".").resolve()

EXPECTED = {
    "round_000": "614816f15b980f9958dd1747a3c0773171d8112ad167e116b7a7651d9623a006",
    "round_001": "cb82cb58ed58a92a8fd0dd33b09322e99191ecd048daf63a36b5ea4182898e1a",
    "round_002": "f16cb78cbdaf4ce5280d79c552adab5ec57f56ca26a3796b02995f0de2441e0e",
}

print("=== TRAIN SET HASH SEARCH ===")

matches = {name: [] for name in EXPECTED}
scan_errors = []

for path in ROOT.rglob("train_set.json"):
    if not path.is_file():
        continue

    try:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()

        for round_name, expected_hash in EXPECTED.items():
            if digest == expected_hash:
                matches[round_name].append(path.resolve())

    except OSError as exc:
        scan_errors.append(f"{path}: {exc}")

for round_name, paths in matches.items():
    print(f"\n{round_name}: MATCH_COUNT={len(paths)}")

    for path in paths:
        print("MATCH:", path)

print("\n=== B4 SEED 13 LOG CANDIDATES ===")

candidates = [
    ROOT / "integration_staging/P1/reports/task7/B4/seed_13/selection_log.jsonl",
    ROOT / "runs/main/B4_seed13/checkpoint_log.jsonl",
    ROOT / "runs/main/B4_seed13/round_000/selection_log.jsonl",
    ROOT / "runs/main/B4_seed13/round_001/selection_log.jsonl",
    ROOT / "runs/main/B4_seed13/round_002/selection_log.jsonl",
]

for path in candidates:
    print(f"\nFILE: {path}")
    print("EXISTS:", path.is_file())

    if not path.is_file():
        continue

    raw = path.read_bytes()

    print("SHA256:", hashlib.sha256(raw).hexdigest())
    print("BYTES:", len(raw))

    if path.suffix.lower() == ".jsonl":
        records = []

        for line_number, line in enumerate(
            path.read_text(encoding="utf-8-sig").splitlines(), start=1
        ):
            if not line.strip():
                continue

            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                print(f"JSONL_PARSE_ERROR at line {line_number}: {exc}")
                break

        print("RECORDS:", len(records))

        for record in records[:3]:
            print("SAMPLE:", json.dumps(record, ensure_ascii=False))

    else:
        print(path.read_text(encoding="utf-8-sig", errors="replace")[:5000])

for error in scan_errors:
    print("READ_ERROR:", error)

print("\n=== TRAIN SET SEARCH SUMMARY ===")

for round_name, paths in matches.items():
    print(f"{round_name}: {len(paths)} matching file(s)")

print("\nLINEAGE_CANDIDATE_AUDIT: COMPLETE")
