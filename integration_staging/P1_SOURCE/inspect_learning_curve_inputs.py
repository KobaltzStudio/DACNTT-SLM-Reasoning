from pathlib import Path
import csv
import json

ROOT = Path(r"C:\KLTN-SLM-Reasoning")
MANUAL = ROOT / "experiments" / "week2September" / "manual"

PRED_DIR = MANUAL / "reports" / "task7" / "B4" / "seed_13"
CAP_ROOT = MANUAL / "reports" / "capability" / "student_eval_2026-11-17"
CKPTS = ["001", "002", "003"]

GOLD_DIRS = [
    MANUAL / "data" / "gold_vnext_frozen_2026-11-16_r1",
]
ADJUDICATION = (
    MANUAL / "reports" / "capability" / "d3_audit"
    / "adjudication_human_confirmed.csv"
)

def read_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def read_jsonl(path):
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except Exception as exc:
                    raise RuntimeError(f"Invalid JSONL: {path}:{line_no}: {exc}")
    return rows

def show_jsonl(label, path):
    print(f"\n===== {label} =====")
    print("PATH:", path)
    if not path.exists():
        print("MISSING")
        return
    rows = read_jsonl(path)
    print("RECORDS:", len(rows))
    if rows:
        first = rows[0]
        print("FIRST_RECORD_KEYS:", sorted(first.keys()))
        print("FIRST_RECORD:")
        print(json.dumps(first, ensure_ascii=False, indent=2)[:5000])
        ids = [str(x.get("problem_id", "")) for x in rows]
        print("UNIQUE_PROBLEM_IDS:", len(set(ids)))
        print("EMPTY_PROBLEM_IDS:", sum(not x for x in ids))
        print("DUPLICATE_PROBLEM_IDS:", len(ids) - len(set(ids)))

def show_csv(label, path, max_rows=30):
    print(f"\n===== {label} =====")
    print("PATH:", path)
    if not path.exists():
        print("MISSING")
        return
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        print("COLUMNS:", reader.fieldnames)
        print("ROWS:", len(rows))
        for row in rows[:max_rows]:
            print(json.dumps(row, ensure_ascii=False))

def show_manifest(path):
    print(f"\n===== MANIFEST: {path.name} =====")
    print("PATH:", path)
    if not path.exists():
        print("MISSING")
        return
    obj = read_json(path)
    print("TOP_LEVEL_KEYS:", sorted(obj.keys()))
    print(json.dumps(obj, ensure_ascii=False, indent=2)[:7000])

for ckpt in CKPTS:
    name = f"student_ckpt_{ckpt}"
    show_jsonl(
        f"{name} PREDICTIONS",
        PRED_DIR / f"eval_{name}_dev.jsonl",
    )

    cap_dir = CAP_ROOT / f"B4_seed13_ckpt{ckpt}"
    show_csv(
        f"{name} CAPABILITY METRICS",
        cap_dir / "capability_metrics.csv",
    )
    show_manifest(
        cap_dir / "student_capability_evaluation_manifest.json"
    )
    show_jsonl(
        f"{name} CAPABILITY METRICS JSONL",
        cap_dir / "capability_metrics.jsonl",
    )

print("\n===== GOLD FROZEN FILES =====")
for gold_dir in GOLD_DIRS:
    print("DIR:", gold_dir)
    if gold_dir.exists():
        for path in sorted(gold_dir.iterdir()):
            print(path.name, path.stat().st_size, "bytes")
            if path.suffix == ".jsonl":
                show_jsonl(path.name, path)
            elif path.suffix == ".json":
                show_manifest(path)

show_csv("HUMAN CONFIRMED ADJUDICATION", ADJUDICATION, max_rows=100)

print("\nINSPECTION_COMPLETE")