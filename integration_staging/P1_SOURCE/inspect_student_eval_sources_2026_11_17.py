from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
MANUAL = ROOT / "experiments" / "week2September" / "manual"
OUT_DIR = MANUAL / "reports" / "capability" / "student_eval_2026-11-17"
OUT_DIR.mkdir(parents=True, exist_ok=True)

GOLD_DIR = MANUAL / "data" / "gold_vnext_frozen_2026-11-16_r1"
GOLD_FILES = [
    GOLD_DIR / "batch_100_annotations_vnext.jsonl",
    GOLD_DIR / "supplement_annotations_vnext.jsonl",
]
ADJ_CSV = MANUAL / "reports" / "capability" / "d3_audit" / "adjudication_human_confirmed.csv"

PREDICTION_FILE = (
    MANUAL / "reports" / "task7" / "B4" / "seed_13"
    / "eval_student_ckpt_001_dev.jsonl"
)
SUMMARY_FILE = PREDICTION_FILE.with_name("eval_student_ckpt_001_dev.summary.json")

CHECKPOINT_DIR = (
    MANUAL / "models" / "task7" / "B4" / "seed_13" / "student_ckpt_001"
)

TASK7_DIR = MANUAL / "scripts"

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def read_jsonl(path: Path):
    rows = []
    with path.open("r", encoding="utf-8-sig") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except Exception as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
    return rows

def summarize_jsonl(path: Path):
    result = {"path": str(path), "exists": path.exists()}
    if not path.exists():
        return result

    rows = read_jsonl(path)
    ids = [r.get("problem_id") for r in rows if isinstance(r, dict)]
    id_counts = Counter(ids)
    result.update({
        "size_bytes": path.stat().st_size,
        "sha256": sha256(path),
        "records": len(rows),
        "first_record_keys": sorted(rows[0].keys()) if rows and isinstance(rows[0], dict) else [],
        "first_records": rows[:3],
        "missing_problem_id_records": sum(x is None for x in ids),
        "duplicate_problem_ids": sorted(k for k, v in id_counts.items() if k is not None and v > 1),
        "unique_problem_ids": len(set(x for x in ids if x is not None)),
    })
    return result

def summarize_csv(path: Path):
    result = {"path": str(path), "exists": path.exists()}
    if not path.exists():
        return result

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fields = reader.fieldnames or []

    result.update({
        "size_bytes": path.stat().st_size,
        "sha256": sha256(path),
        "records": len(rows),
        "columns": fields,
        "first_records": rows[:5],
    })

    status_fields = [
        c for c in fields
        if any(token in c.lower() for token in (
            "status", "adjud", "decision", "confirm", "review", "split", "source"
        ))
    ]
    result["status_value_counts"] = {
        col: dict(Counter((r.get(col) or "").strip() for r in rows))
        for col in status_fields
    }

    if "problem_id" in fields:
        ids = [r.get("problem_id") for r in rows]
        counts = Counter(ids)
        result["unique_problem_ids"] = len(set(x for x in ids if x))
        result["duplicate_problem_ids"] = sorted(
            k for k, v in counts.items() if k and v > 1
        )

    return result

def read_json(path: Path):
    if not path.exists():
        return {"path": str(path), "exists": False}
    with path.open("r", encoding="utf-8-sig") as f:
        value = json.load(f)
    return {
        "path": str(path),
        "exists": True,
        "size_bytes": path.stat().st_size,
        "sha256": sha256(path),
        "content": value,
    }

def inspect_checkpoint(path: Path):
    result = {"path": str(path), "exists": path.exists()}
    if not path.exists():
        return result

    result["files"] = [
        {
            "name": p.name,
            "relative_path": str(p.relative_to(path)),
            "size_bytes": p.stat().st_size,
        }
        for p in sorted(path.rglob("*"))
        if p.is_file()
    ]

    for name in ("adapter_config.json", "config.json", "tokenizer_config.json", "train_log.json"):
        p = path / name
        if p.exists() and p.suffix == ".json":
            result[name] = read_json(p)

    return result

def main():
    report = {
        "repository": str(ROOT),
        "gold_files": [summarize_jsonl(p) for p in GOLD_FILES],
        "adjudication_csv": summarize_csv(ADJ_CSV),
        "prediction_file": summarize_jsonl(PREDICTION_FILE),
        "evaluation_summary": read_json(SUMMARY_FILE),
        "checkpoint": inspect_checkpoint(CHECKPOINT_DIR),
        "task7_scripts": [],
    }

    if TASK7_DIR.exists():
        for p in sorted(TASK7_DIR.glob("*task7*.py")):
            report["task7_scripts"].append({
                "path": str(p),
                "size_bytes": p.stat().st_size,
            })

    out_json = OUT_DIR / "student_eval_source_inspection.json"
    out_md = OUT_DIR / "student_eval_source_inspection.md"

    out_json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = [
        "# Student Evaluation Source Inspection",
        "",
        f"- Repository: `{ROOT}`",
        "",
        "## Frozen Gold JSONL",
    ]

    for item in report["gold_files"]:
        lines += [
            f"### `{item['path']}`",
            f"- Exists: {item['exists']}",
            f"- Records: {item.get('records', 'N/A')}",
            f"- Unique IDs: {item.get('unique_problem_ids', 'N/A')}",
            f"- Missing IDs: {item.get('missing_problem_id_records', 'N/A')}",
            f"- Duplicate IDs: {item.get('duplicate_problem_ids', 'N/A')}",
            f"- Keys: {item.get('first_record_keys', 'N/A')}",
            f"- SHA256: {item.get('sha256', 'N/A')}",
            "",
        ]

    adj = report["adjudication_csv"]
    lines += [
        "## Adjudication CSV",
        f"- Exists: {adj['exists']}",
        f"- Records: {adj.get('records', 'N/A')}",
        f"- Columns: {adj.get('columns', 'N/A')}",
        f"- Status counts: `{json.dumps(adj.get('status_value_counts', {}), ensure_ascii=False)}`",
        "",
        "## Student Prediction File",
        f"- Exists: {report['prediction_file']['exists']}",
        f"- Records: {report['prediction_file'].get('records', 'N/A')}",
        f"- Unique IDs: {report['prediction_file'].get('unique_problem_ids', 'N/A')}",
        f"- Missing IDs: {report['prediction_file'].get('missing_problem_id_records', 'N/A')}",
        f"- Duplicate IDs: {report['prediction_file'].get('duplicate_problem_ids', 'N/A')}",
        f"- Keys: {report['prediction_file'].get('first_record_keys', 'N/A')}",
        f"- SHA256: {report['prediction_file'].get('sha256', 'N/A')}",
        "",
        "## Checkpoint",
        f"- Exists: {report['checkpoint']['exists']}",
        f"- File count: {len(report['checkpoint'].get('files', []))}",
        "",
        "## Task 7 scripts",
    ]

    lines += [f"- `{x['path']}`" for x in report["task7_scripts"]]
    lines += [
        "",
        "## Full details",
        f"- JSON: `{out_json}`",
    ]

    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("SOURCE_INSPECTION_STATUS: PASS")
    print(f"GOLD_FILES: {len(GOLD_FILES)}")
    print(f"ADJUDICATION_CSV_EXISTS: {ADJ_CSV.exists()}")
    print(f"PREDICTION_FILE_EXISTS: {PREDICTION_FILE.exists()}")
    print(f"CHECKPOINT_EXISTS: {CHECKPOINT_DIR.exists()}")
    print(f"JSON: {out_json}")
    print(f"MARKDOWN: {out_md}")

if __name__ == "__main__":
    main()
