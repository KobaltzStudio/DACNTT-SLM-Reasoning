from pathlib import Path
from collections import Counter
import csv
import hashlib
import json

REPO = Path(r"C:\KLTN-SLM-Reasoning")
MANUAL = REPO / "experiments" / "week2September" / "manual"

MODEL_ROOT = MANUAL / "models" / "task7"
PREDICTION_ROOT = MANUAL / "reports" / "task7"
DEV_IDS_FILE = MANUAL / "splits" / "d_dev_ids.txt"

OUT_DIR = MANUAL / "reports" / "capability" / "student_eval_2026-11-17"
OUT_JSON = OUT_DIR / "checkpoint_prediction_inventory.json"
OUT_CSV = OUT_DIR / "checkpoint_prediction_inventory.csv"


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_jsonl(path):
    rows = []
    with path.open("r", encoding="utf-8-sig") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: {exc}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_no}: expected JSON object")
            rows.append(row)
    return rows


def read_dev_ids():
    return {
        x.strip()
        for x in DEV_IDS_FILE.read_text(encoding="utf-8-sig").splitlines()
        if x.strip()
    }


def load_train_log(checkpoint_dir):
    candidates = [
        checkpoint_dir / "train_log.json",
        checkpoint_dir / "training_log.json",
        checkpoint_dir / "train_log.txt",
    ]
    for path in candidates:
        if not path.is_file():
            continue
        if path.suffix.lower() == ".json":
            try:
                return {"path": str(path), "data": json.loads(
                    path.read_text(encoding="utf-8-sig")
                )}
            except Exception as exc:
                return {"path": str(path), "parse_error": str(exc)}
        return {"path": str(path), "text_preview": path.read_text(
            encoding="utf-8-sig", errors="replace"
        )[:4000]}
    return None


def infer_path_metadata(path, root):
    rel = path.relative_to(root)
    parts = rel.parts
    seed = next((p for p in parts if p.startswith("seed_")), None)
    method = parts[0] if parts else None
    return {
        "relative_path": str(rel),
        "method_path_component": method,
        "seed_path_component": seed,
    }


def main():
    if not MODEL_ROOT.is_dir():
        raise SystemExit(f"MODEL_ROOT_NOT_FOUND: {MODEL_ROOT}")
    if not PREDICTION_ROOT.is_dir():
        raise SystemExit(f"PREDICTION_ROOT_NOT_FOUND: {PREDICTION_ROOT}")
    if not DEV_IDS_FILE.is_file():
        raise SystemExit(f"D_DEV_IDS_NOT_FOUND: {DEV_IDS_FILE}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dev_ids = read_dev_ids()

    checkpoints = []
    for adapter in sorted(MODEL_ROOT.rglob("adapter_model.safetensors")):
        checkpoint_dir = adapter.parent
        metadata = infer_path_metadata(checkpoint_dir, MODEL_ROOT)
        checkpoints.append({
            "checkpoint_dir": str(checkpoint_dir),
            "adapter_file": str(adapter),
            "adapter_size_bytes": adapter.stat().st_size,
            "adapter_sha256": sha256(adapter),
            **metadata,
            "train_log": load_train_log(checkpoint_dir),
        })

    prediction_files = []
    for path in sorted(PREDICTION_ROOT.rglob("*.jsonl")):
        lower = path.name.lower()
        if "dev" not in lower:
            continue
        try:
            rows = read_jsonl(path)
            ids = [
                str(r.get("problem_id", "")).strip()
                for r in rows
            ]
            missing_id_rows = sum(not x for x in ids)
            counts = Counter(x for x in ids if x)
            duplicates = sorted(k for k, v in counts.items() if v > 1)
            prediction_ids = set(counts)
            checkpoint_values = sorted({
                str(r.get("checkpoint", "")).strip()
                for r in rows
            })
            correct_types = Counter(
                type(r.get("correct")).__name__ for r in rows
            )
            prediction_files.append({
                "prediction_file": str(path),
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
                "records": len(rows),
                "unique_problem_ids": len(prediction_ids),
                "missing_problem_id_records": missing_id_rows,
                "duplicate_problem_ids": duplicates,
                "prediction_ids_outside_d_dev": sorted(prediction_ids - dev_ids),
                "d_dev_ids_missing_from_prediction": sorted(dev_ids - prediction_ids),
                "checkpoint_values": checkpoint_values,
                "correct_field_types": dict(correct_types),
                "path_metadata": infer_path_metadata(path, PREDICTION_ROOT),
                "inventory_parse_status": "PASS",
            })
        except Exception as exc:
            prediction_files.append({
                "prediction_file": str(path),
                "inventory_parse_status": "FAIL",
                "error": str(exc),
            })

    result = {
        "model_root": str(MODEL_ROOT),
        "prediction_root": str(PREDICTION_ROOT),
        "d_dev_count": len(dev_ids),
        "checkpoint_count": len(checkpoints),
        "prediction_file_count": len(prediction_files),
        "checkpoints": checkpoints,
        "prediction_files": prediction_files,
    }

    OUT_JSON.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    flat_rows = []
    for pred in prediction_files:
        flat_rows.append({
            "prediction_file": pred.get("prediction_file"),
            "records": pred.get("records"),
            "unique_problem_ids": pred.get("unique_problem_ids"),
            "checkpoint_values": ";".join(pred.get("checkpoint_values", [])),
            "duplicate_count": len(pred.get("duplicate_problem_ids", [])),
            "outside_d_dev_count": len(pred.get("prediction_ids_outside_d_dev", [])),
            "missing_d_dev_count": len(pred.get("d_dev_ids_missing_from_prediction", [])),
            "correct_field_types": json.dumps(pred.get("correct_field_types", {})),
            "status": pred.get("inventory_parse_status"),
            "error": pred.get("error"),
        })

    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(flat_rows[0].keys()) if flat_rows else [
            "prediction_file", "records", "unique_problem_ids",
            "checkpoint_values", "duplicate_count", "outside_d_dev_count",
            "missing_d_dev_count", "correct_field_types", "status", "error"
        ])
        writer.writeheader()
        writer.writerows(flat_rows)

    print("CHECKPOINT_INVENTORY_STATUS: PASS")
    print("D_DEV_COUNT:", len(dev_ids))
    print("CHECKPOINT_COUNT:", len(checkpoints))
    print("PREDICTION_FILE_COUNT:", len(prediction_files))
    print("\nCHECKPOINTS:")
    for item in checkpoints:
        print("-", item["checkpoint_dir"])
        print("  seed:", item["seed_path_component"])
        print("  train_log:", bool(item["train_log"]))

    print("\nDEV PREDICTIONS:")
    for item in prediction_files:
        print("-", item["prediction_file"])
        print("  records:", item.get("records"))
        print("  unique IDs:", item.get("unique_problem_ids"))
        print("  checkpoint:", item.get("checkpoint_values"))
        print("  duplicates:", len(item.get("duplicate_problem_ids", [])))
        print("  outside D_dev:", len(item.get("prediction_ids_outside_d_dev", [])))
        print("  missing D_dev:", len(item.get("d_dev_ids_missing_from_prediction", [])))
        print("  status:", item["inventory_parse_status"])

    print("\nOUTPUTS:")
    print(OUT_JSON)
    print(OUT_CSV)


if __name__ == "__main__":
    main()
