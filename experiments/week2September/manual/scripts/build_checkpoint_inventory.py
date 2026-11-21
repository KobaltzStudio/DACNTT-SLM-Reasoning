from pathlib import Path
import csv
import hashlib
import json
from datetime import datetime, timezone

MANUAL = Path(r"C:\KLTN-SLM-Reasoning\experiments\week2September\manual")
OUT = MANUAL / "reports" / "learning_curve" / "2026-11-17"
OUT.mkdir(parents=True, exist_ok=True)

PIPELINE = MANUAL / "scripts" / "run_b4_b5.py"
MODEL_ROOT = MANUAL / "models" / "task7" / "B4" / "seed_13"
TRAIN_ROOT = MANUAL / "reports" / "task7" / "B4" / "seed_13"
CAP_ROOT = MANUAL / "reports" / "capability" / "student_eval_2026-11-17"

CHECKPOINTS = [
    ("student_ckpt_001", 0, 4),
    ("student_ckpt_002", 1, 4),
    ("student_ckpt_003", 2, 1),
]

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def read_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def count_jsonl(path):
    count = 0
    ids = set()
    duplicates = 0
    missing_ids = 0
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            obj = json.loads(line)
            count += 1
            pid = str(obj.get("problem_id", "")).strip()
            if not pid:
                missing_ids += 1
            elif pid in ids:
                duplicates += 1
            else:
                ids.add(pid)
    return count, len(ids), duplicates, missing_ids

def optional_hash(path):
    return sha256(path) if path.exists() and path.is_file() else ""

rows = []
for checkpoint, rnd, expected_micro in CHECKPOINTS:
    adapter_dir = MODEL_ROOT / checkpoint
    train_log_path = adapter_dir / "train_log.json"
    adapter_config_path = adapter_dir / "adapter_config.json"
    adapter_weights_path = adapter_dir / "adapter_model.safetensors"

    train_set_path = (
        MANUAL / "reports" / "task7" / "B4" / "seed_13"
        / f"round_{rnd:03d}" / "train_set.json"
    )
    prediction_path = (
        TRAIN_ROOT / f"eval_{checkpoint}_dev.jsonl"
    )
    eval_summary_path = (
        TRAIN_ROOT / f"eval_{checkpoint}_dev.summary.json"
    )

    cap_dir = CAP_ROOT / f"B4_seed13_ckpt{checkpoint[-3:]}"
    cap_csv = cap_dir / "capability_metrics.csv"
    cap_manifest = cap_dir / "student_capability_evaluation_manifest.json"
    coverage_report = cap_dir / "prediction_coverage_report.json"

    required = {
        "adapter_config": adapter_config_path,
        "adapter_weights": adapter_weights_path,
        "train_log": train_log_path,
        "train_set": train_set_path,
        "prediction": prediction_path,
        "eval_summary": eval_summary_path,
        "capability_csv": cap_csv,
        "capability_manifest": cap_manifest,
        "coverage_report": coverage_report,
    }

    missing = [name for name, path in required.items() if not path.exists()]
    if missing:
        raise FileNotFoundError(
            f"{checkpoint}: missing required artifacts: {missing}"
        )

    log = read_json(train_log_path)
    summary = read_json(eval_summary_path)
    manifest = read_json(cap_manifest)
    coverage = read_json(coverage_report)

    n_pred, n_unique, n_dup, n_missing_ids = count_jsonl(prediction_path)

    row = {
        "checkpoint": checkpoint,
        "method": "B4",
        "seed": 13,
        "round": rnd,
        "parent": log.get("checkpoint_parent", ""),
        "train_set_examples": log.get("n_examples", ""),
        "training_steps": log.get("steps", ""),
        "effective_batch": log.get("effective_batch", ""),
        "micro_batch": log.get("micro_batch", ""),
        "grad_accum": log.get("grad_accum", ""),
        "learning_rate": log.get("learning_rate", log.get("lr", "")),
        "train_set_sha256_log": log.get("train_set_sha256", ""),
        "train_set_sha256_actual": sha256(train_set_path),
        "pool_sha256": log.get("pool_sha256", ""),
        "adapter_config_sha256": sha256(adapter_config_path),
        "adapter_weights_sha256": sha256(adapter_weights_path),
        "train_log_sha256": sha256(train_log_path),
        "prediction_sha256": sha256(prediction_path),
        "prediction_records": n_pred,
        "prediction_unique_ids": n_unique,
        "prediction_duplicate_ids": n_dup,
        "prediction_missing_ids": n_missing_ids,
        "eval_backend": summary.get("backend", ""),
        "base_model": summary.get("model", ""),
        "base_model_revision": summary.get("revision", ""),
        "eval_accuracy": summary.get("accuracy", ""),
        "eval_lenient_accuracy": summary.get("lenient_accuracy", ""),
        "eval_format_compliance": summary.get("format_compliance", ""),
        "eval_mean_output_tokens": summary.get("mean_output_tokens", ""),
        "eval_do_sample": summary.get("decoding", {}).get("do_sample", ""),
        "eval_max_new_tokens": summary.get("decoding", {}).get("max_new_tokens", ""),
        "eval_prompt_version": summary.get("decoding", {}).get("prompt_version", ""),
        "capability_csv_sha256": optional_hash(cap_csv),
        "capability_manifest_sha256": optional_hash(cap_manifest),
        "coverage_report_sha256": optional_hash(coverage_report),
        "coverage_status": coverage.get("status", ""),
        "gold_matched": coverage.get("gold_matched", ""),
        "gold_missing": coverage.get("gold_missing", ""),
        "gold_coverage": coverage.get("coverage", ""),
        "gold_batch_sha256": manifest.get("gold_batch_sha256", ""),
        "gold_supplement_sha256": manifest.get("gold_supplement_sha256", ""),
        "adjudication_sha256": manifest.get("adjudication_sha256", ""),
        "expected_micro_batch": expected_micro,
        "micro_batch_matches_expected": (
            str(log.get("micro_batch", "")) == str(expected_micro)
        ),
    }
    rows.append(row)

pipeline_hash = optional_hash(PIPELINE)
csv_path = OUT / "B4_seed13_checkpoint_inventory.csv"
json_path = OUT / "B4_seed13_checkpoint_inventory.json"

fieldnames = list(rows[0].keys())
with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

payload = {
    "created_utc": datetime.now(timezone.utc).isoformat(),
    "scope": {
        "method": "B4",
        "seed": 13,
        "checkpoints": [r["checkpoint"] for r in rows],
        "evaluation_split": "D_dev",
        "evaluation_backend": "HF",
    },
    "pipeline": {
        "path": str(PIPELINE),
        "sha256": pipeline_hash,
    },
    "checkpoints": rows,
}
json_path.write_text(
    json.dumps(payload, ensure_ascii=False, indent=2),
    encoding="utf-8",
)

print("INVENTORY_STATUS: PASS")
print("CHECKPOINTS:", len(rows))
for row in rows:
    print(
        row["checkpoint"],
        "steps=", row["training_steps"],
        "micro=", row["micro_batch"],
        "grad_accum=", row["grad_accum"],
        "predictions=", row["prediction_records"],
        "unique_ids=", row["prediction_unique_ids"],
        "backend=", row["eval_backend"],
    )
print("PIPELINE_SHA256:", pipeline_hash)
print("CSV:", csv_path)
print("JSON:", json_path)