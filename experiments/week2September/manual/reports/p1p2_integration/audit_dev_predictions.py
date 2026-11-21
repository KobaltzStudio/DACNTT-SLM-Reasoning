import json
from pathlib import Path

root = Path(".")
methods = ["B2", "B3", "B4", "B5"]
seeds = [13, 42, 2026]
checkpoints = ["S1", "S2", "S3"]

expected_ids = {
    x.strip()
    for x in (root / "splits/d_dev_ids.txt").read_text(encoding="utf-8-sig").splitlines()
    if x.strip()
}

errors = []

for method in methods:
    for seed in seeds:
        for checkpoint in checkpoints:
            path = root / f"runs/main/{method}_seed{seed}/{checkpoint}/eval_dev.jsonl"

            if not path.exists():
                errors.append(f"MISSING: {path}")
                continue

            rows = [
                json.loads(line)
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

            ids = [str(row.get("problem_id", "")) for row in rows]

            if len(rows) != 500:
                errors.append(f"ROW_COUNT: {path}: {len(rows)}")

            if len(set(ids)) != len(ids):
                errors.append(f"DUPLICATE_IDS: {path}")

            if set(ids) != expected_ids:
                errors.append(
                    f"ID_SET_MISMATCH: {path}: "
                    f"missing={len(expected_ids - set(ids))}, "
                    f"extra={len(set(ids) - expected_ids)}"
                )

            statuses = {}
            for row in rows:
                status = row.get("status", row.get("verification_status"))
                statuses[status] = statuses.get(status, 0) + 1

            print(
                f"{method} seed={seed} {checkpoint}: "
                f"rows={len(rows)}, unique_ids={len(set(ids))}, "
                f"statuses={statuses}"
            )

s0 = root / "runs/main/S0/eval_dev.jsonl"
if not s0.exists():
    errors.append(f"MISSING: {s0}")
else:
    rows = [
        json.loads(line)
        for line in s0.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    ids = [str(row.get("problem_id", "")) for row in rows]

    if len(rows) != 500 or len(set(ids)) != 500 or set(ids) != expected_ids:
        errors.append("S0 prediction coverage mismatch")

print("\n=== AUDIT RESULT ===")
if errors:
    print("FAIL")
    for error in errors:
        print("-", error)
    raise SystemExit(1)

print("PASS: 36 trained predictions + 1 shared S0 have exact D_dev coverage")
