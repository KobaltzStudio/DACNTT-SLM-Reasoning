from pathlib import Path
import csv
import json
import hashlib
import sys

REPO = Path(r"C:\KLTN-SLM-Reasoning")
MANUAL = REPO / "experiments" / "week2September" / "manual"
EVAL_ROOT = MANUAL / "reports" / "capability" / "student_eval_2026-11-17"
OUTPUT = MANUAL / "reports" / "learning_curve" / "2026-11-18" / "input_schema_audit.txt"

CHECKPOINTS = [
    ("B4_seed13_ckpt001", 0, "student_ckpt_001"),
    ("B4_seed13_ckpt002", 1, "student_ckpt_002"),
    ("B4_seed13_ckpt003", 2, "student_ckpt_003"),
]

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def emit(lines, value=""):
    lines.append(str(value))

def inspect_csv(path, lines):
    emit(lines, f"\n--- CSV: {path.name} ---")
    emit(lines, f"SHA256: {sha256(path)}")
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            emit(lines, f"COLUMNS: {reader.fieldnames}")
            for i, row in enumerate(reader):
                if i >= 8:
                    break
                emit(lines, json.dumps(row, ensure_ascii=False))
    except Exception as exc:
        emit(lines, f"CSV_ERROR: {exc!r}")

def inspect_json(path, lines):
    emit(lines, f"\n--- JSON: {path.name} ---")
    emit(lines, f"SHA256: {sha256(path)}")
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
        if isinstance(obj, dict):
            emit(lines, f"TOP_LEVEL_KEYS: {list(obj.keys())}")
            emit(lines, json.dumps(obj, ensure_ascii=False, indent=2)[:12000])
        elif isinstance(obj, list):
            emit(lines, f"RECORD_COUNT: {len(obj)}")
            for row in obj[:3]:
                emit(lines, json.dumps(row, ensure_ascii=False)[:3000])
        else:
            emit(lines, repr(obj))
    except Exception as exc:
        emit(lines, f"JSON_ERROR: {exc!r}")

def main():
    lines = []
    emit(lines, "LEARNING DYNAMICS INPUT AUDIT")
    emit(lines, f"REPO: {REPO}")
    emit(lines, f"MANUAL: {MANUAL}")
    emit(lines, f"EVAL_ROOT: {EVAL_ROOT}")

    if not EVAL_ROOT.exists():
        raise SystemExit(f"EVAL_ROOT_MISSING: {EVAL_ROOT}")

    for folder_name, round_id, checkpoint_name in CHECKPOINTS:
        folder = EVAL_ROOT / folder_name
        emit(lines, "\n" + "=" * 100)
        emit(lines, f"CHECKPOINT: {folder_name}")
        emit(lines, f"EXPECTED_METHOD: B4")
        emit(lines, f"EXPECTED_SEED: 13")
        emit(lines, f"EXPECTED_ROUND: {round_id}")
        emit(lines, f"EXPECTED_CHECKPOINT: {checkpoint_name}")
        emit(lines, f"FOLDER_EXISTS: {folder.exists()}")

        if not folder.exists():
            continue

        files = sorted(p for p in folder.iterdir() if p.is_file())
        emit(lines, f"FILE_COUNT: {len(files)}")

        for path in files:
            emit(lines, f"FILE: {path.name} | SIZE: {path.stat().st_size}")

        for path in files:
            suffix = path.suffix.lower()
            name = path.name.lower()

            if suffix == ".csv":
                inspect_csv(path, lines)
            elif suffix == ".json" and (
                "manifest" in name
                or "coverage" in name
                or "metric" in name
                or "audit" in name
            ):
                inspect_json(path, lines)

    emit(lines, "\n" + "=" * 100)
    emit(lines, "GRAPH PROTOCOL SEARCH")

    protocol_files = list(MANUAL.rglob("proposal1_graph_protocol.md"))
    if protocol_files:
        for path in protocol_files:
            emit(lines, f"\nPROTOCOL_FOUND: {path}")
            emit(lines, path.read_text(encoding="utf-8-sig", errors="replace"))
    else:
        emit(lines, "EXACT_PROTOCOL_NOT_FOUND")

    # Find other potentially relevant graph/proposal documentation.
    candidates = []
    for path in MANUAL.rglob("*"):
        if not path.is_file():
            continue
        low = path.name.lower()
        if path.suffix.lower() in {".md", ".txt", ".json"} and (
            "graph" in low or "proposal1" in low or "capability" in low
        ):
            candidates.append(path)

    emit(lines, "\nRELATED DOCUMENTS:")
    for path in sorted(candidates):
        emit(lines, str(path.relative_to(MANUAL)))

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\nAUDIT_REPORT: {OUTPUT}")
    print(f"AUDIT_SHA256: {sha256(OUTPUT)}")

if __name__ == "__main__":
    main()
