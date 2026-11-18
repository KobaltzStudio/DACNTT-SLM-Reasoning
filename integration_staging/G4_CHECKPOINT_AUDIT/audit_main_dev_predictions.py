from pathlib import Path
from collections import Counter
import hashlib
import json
import csv
import sys

ROOT = Path(r"C:\Users\PC - NGHI\Desktop\Pipeline\P2")
MAIN = ROOT / "experiments" / "week2September" / "manual" / "runs" / "main"
OUT = ROOT / "integration_staging" / "G4_CHECKPOINT_AUDIT"

ID_KEYS = ("problem_id", "id", "question_id", "example_id")
CORRECT_KEYS = (
    "correct", "is_correct", "exact_match", "answer_correct",
    "pred_correct", "gold_match"
)
WEIGHT_NAMES = {
    "adapter_model.safetensors",
    "adapter_model.bin",
    "pytorch_model.bin",
    "model.safetensors",
    "model.safetensors.index.json",
}
WEIGHT_SUFFIXES = (".safetensors", ".bin", ".pt", ".pth")

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def read_jsonl(path):
    rows = []
    errors = []
    with path.open("r", encoding="utf-8-sig") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except Exception as exc:
                errors.append(f"line {line_no}: {exc}")
    return rows, errors

def first_present(row, keys):
    for key in keys:
        if key in row:
            return key, row[key]
    return None, None

def write_csv(path, rows):
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

if not MAIN.is_dir():
    raise SystemExit(f"MAIN_RUNS_NOT_FOUND: {MAIN}")

OUT.mkdir(parents=True, exist_ok=True)

prediction_files = sorted(MAIN.rglob("eval_dev.jsonl"))
summary_files = sorted(MAIN.rglob("eval_dev.summary.json"))
done_files = sorted(MAIN.glob("*/.done/eval_dev_*.json"))

prediction_report = []
schema_counter = Counter()
id_key_counter = Counter()
correct_key_counter = Counter()
all_samples = {}

for path in prediction_files:
    rows, errors = read_jsonl(path)
    rel = path.relative_to(MAIN).as_posix()
    id_values = []
    id_keys_seen = Counter()
    correct_keys_seen = Counter()
    key_counter = Counter()

    for row in rows:
        if isinstance(row, dict):
            key_counter.update(row.keys())
            id_key, id_value = first_present(row, ID_KEYS)
            if id_key:
                id_keys_seen[id_key] += 1
                if id_value is not None:
                    id_values.append(str(id_value))
            correct_key, _ = first_present(row, CORRECT_KEYS)
            if correct_key:
                correct_keys_seen[correct_key] += 1

    duplicates = len(id_values) - len(set(id_values))
    missing_id_rows = len(rows) - sum(id_keys_seen.values())
    schema_counter.update(key_counter.keys())
    id_key_counter.update(id_keys_seen)
    correct_key_counter.update(correct_keys_seen)

    prediction_report.append({
        "relative_path": rel,
        "row_count": len(rows),
        "parse_error_count": len(errors),
        "id_field_counts": json.dumps(dict(id_keys_seen), ensure_ascii=False),
        "correctness_field_counts": json.dumps(dict(correct_keys_seen), ensure_ascii=False),
        "unique_id_count": len(set(id_values)),
        "duplicate_id_count": duplicates,
        "rows_without_recognized_id": missing_id_rows,
        "sha256": sha256(path),
        "size_bytes": path.stat().st_size,
        "parse_errors": " || ".join(errors[:5]),
    })

    all_samples[rel] = {
        "first_row": rows[0] if rows else None,
        "second_row": rows[1] if len(rows) > 1 else None,
        "top_level_keys": sorted(set().union(
            *(r.keys() for r in rows[:100] if isinstance(r, dict))
        )) if rows else [],
    }

write_csv(OUT / "main_eval_dev_prediction_audit.csv", prediction_report)

weight_report = []
for path in sorted(MAIN.rglob("*")):
    if path.is_file() and (
        path.name in WEIGHT_NAMES or path.suffix.lower() in WEIGHT_SUFFIXES
    ):
        weight_report.append({
            "relative_path": path.relative_to(MAIN).as_posix(),
            "file_name": path.name,
            "size_bytes": path.stat().st_size,
            "sha256": sha256(path),
        })

write_csv(OUT / "main_checkpoint_weight_inventory.csv", weight_report)

summary_report = []
for path in summary_files:
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
        summary_report.append({
            "relative_path": path.relative_to(MAIN).as_posix(),
            "valid_json": True,
            "top_level_keys": json.dumps(
                sorted(obj.keys()) if isinstance(obj, dict) else [],
                ensure_ascii=False
            ),
            "content_preview": json.dumps(obj, ensure_ascii=False)[:1200],
            "error": "",
        })
    except Exception as exc:
        summary_report.append({
            "relative_path": path.relative_to(MAIN).as_posix(),
            "valid_json": False,
            "top_level_keys": "",
            "content_preview": "",
            "error": str(exc),
        })

write_csv(OUT / "main_eval_dev_summary_audit.csv", summary_report)

done_report = []
for path in done_files:
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
        done_report.append({
            "relative_path": path.relative_to(MAIN).as_posix(),
            "valid_json": True,
            "size_bytes": path.stat().st_size,
            "content": json.dumps(obj, ensure_ascii=False),
            "error": "",
        })
    except Exception as exc:
        done_report.append({
            "relative_path": path.relative_to(MAIN).as_posix(),
            "valid_json": False,
            "size_bytes": path.stat().st_size,
            "content": "",
            "error": str(exc),
        })

write_csv(OUT / "main_done_marker_audit.csv", done_report)

sample_path = OUT / "main_eval_dev_schema_samples.json"
sample_path.write_text(
    json.dumps(all_samples, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

lines = []
lines.append("MAIN DEV PREDICTION AUDIT")
lines.append(f"MAIN_ROOT={MAIN}")
lines.append(f"PREDICTION_FILE_COUNT={len(prediction_files)}")
lines.append(f"SUMMARY_FILE_COUNT={len(summary_files)}")
lines.append(f"DONE_JSON_COUNT={len(done_files)}")
lines.append(f"WEIGHT_FILE_COUNT={len(weight_report)}")
lines.append("")
lines.append("PREDICTION FILE COUNTS BY TOP-LEVEL RUN:")
run_counts = Counter(p.relative_to(MAIN).parts[0] for p in prediction_files)
for run, count in sorted(run_counts.items()):
    lines.append(f"{run}: {count}")
lines.append("")
lines.append("ID FIELD OCCURRENCES:")
lines.append(json.dumps(dict(id_key_counter), ensure_ascii=False))
lines.append("CORRECTNESS FIELD OCCURRENCES:")
lines.append(json.dumps(dict(correct_key_counter), ensure_ascii=False))
lines.append("")
lines.append("PREDICTION FILE DETAILS:")
for row in prediction_report:
    lines.append(
        f"{row['relative_path']} | rows={row['row_count']} "
        f"| unique_ids={row['unique_id_count']} "
        f"| duplicates={row['duplicate_id_count']} "
        f"| no_id={row['rows_without_recognized_id']} "
        f"| parse_errors={row['parse_error_count']}"
    )

(OUT / "main_dev_prediction_audit_summary.txt").write_text(
    "\n".join(lines), encoding="utf-8"
)

print("\n".join(lines))
print("\nOUTPUT_FILES:")
for name in (
    "main_eval_dev_prediction_audit.csv",
    "main_checkpoint_weight_inventory.csv",
    "main_eval_dev_summary_audit.csv",
    "main_done_marker_audit.csv",
    "main_eval_dev_schema_samples.json",
    "main_dev_prediction_audit_summary.txt",
):
    print(OUT / name)
