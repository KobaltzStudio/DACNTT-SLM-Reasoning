from __future__ import annotations

import csv
import hashlib
import json
import re
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path.cwd()
ARCHIVE = ROOT / "runs" / "main" / "main.zip"
D_DEV = ROOT / "splits" / "d_dev_ids.txt"
DERIVED = ROOT / "reports" / "p1p2_integration" / "derived_predictions"
OUT = ROOT / "reports" / "p1p2_integration" / "checkpoint_inventory_audit" / "g5_9_provenance_deep"
RUN_ID = datetime.now(timezone.utc).strftime("run_%Y%m%d_%H%M%S")
RUN_DIR = OUT / RUN_ID

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def read_json_bytes(data: bytes) -> Any:
    return json.loads(data.decode("utf-8-sig"))

def read_jsonl_bytes(data: bytes) -> list[dict[str, Any]]:
    rows = []
    for line_no, line in enumerate(data.decode("utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        obj = json.loads(line)
        if not isinstance(obj, dict):
            raise ValueError(f"JSONL line {line_no} is not an object")
        rows.append(obj)
    return rows

def safe_json(zf: zipfile.ZipFile, name: str) -> dict[str, Any]:
    try:
        return {"member": name, "status": "OK", "content": read_json_bytes(zf.read(name))}
    except KeyError:
        return {"member": name, "status": "MISSING"}
    except Exception as exc:
        return {"member": name, "status": "ERROR", "error": repr(exc)}

def summarize_prediction(zf: zipfile.ZipFile, member: str, dev_ids: set[str]) -> dict[str, Any]:
    try:
        raw = zf.read(member)
        rows = read_jsonl_bytes(raw)
        ids = [str(r.get("problem_id", "")).strip() for r in rows]
        id_set = set(ids)
        statuses = Counter(str(r.get("status")) for r in rows)
        return {
            "member": member,
            "status": "OK",
            "sha256": sha256_bytes(raw),
            "bytes": len(raw),
            "rows": len(rows),
            "unique_problem_ids": len(id_set),
            "duplicate_ids": len(ids) - len(id_set),
            "missing_ids": len(dev_ids - id_set),
            "outside_dev_ids": len(id_set - dev_ids),
            "ids_equal_d_dev": id_set == dev_ids and len(ids) == len(id_set),
            "status_counts": dict(statuses),
            "first_row_keys": sorted(rows[0].keys()) if rows else [],
            "first_row": rows[0] if rows else None,
        }
    except Exception as exc:
        return {"member": member, "status": "ERROR", "error": repr(exc)}

def main() -> None:
    for path in (ARCHIVE, D_DEV):
        if not path.is_file():
            raise FileNotFoundError(f"Required input missing: {path}")
    RUN_DIR.mkdir(parents=True, exist_ok=False)

    dev_ids = {
        line.strip()
        for line in D_DEV.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    }
    if len(dev_ids) != 500:
        raise ValueError(f"Expected 500 unique D_dev IDs; found {len(dev_ids)}")

    result: dict[str, Any] = {
        "run_id": RUN_ID,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "root": str(ROOT),
        "archive": str(ARCHIVE),
        "archive_sha256": hashlib.sha256(ARCHIVE.read_bytes()).hexdigest(),
        "d_dev_path": str(D_DEV),
        "d_dev_unique_ids": len(dev_ids),
        "contexts": [],
        "s0": {},
        "derived": {},
        "errors": [],
    }

    with zipfile.ZipFile(ARCHIVE, "r") as zf:
        bad_member = zf.testzip()
        result["zip_integrity"] = "OK" if bad_member is None else f"BAD:{bad_member}"
        names = set(zf.namelist())

        # S0: prediction, marker, summary, and any available baseline metadata.
        result["s0"]["prediction"] = summarize_prediction(
            zf, "S0/eval_dev.jsonl", dev_ids
        )
        result["s0"]["marker"] = safe_json(zf, "S0/.done/eval_dev_S0.json")
        result["s0"]["summary"] = safe_json(zf, "S0/eval_dev.summary.json")
        result["s0"]["candidate_metadata"] = {
            name: {"bytes": zf.getinfo(name).file_size,
                   "sha256": sha256_bytes(zf.read(name))}
            for name in sorted(names)
            if name.startswith("S0/")
            and any(token in name.lower() for token in (
                "adapter_config", "train_log", "checkpoint", "manifest", "config"
            ))
        }

        # Per-method/seed/checkpoint: preserve raw train logs and checkpoint logs.
        contexts = sorted({
            f"{method}_seed{seed}"
            for method in ("B2", "B3", "B4", "B5")
            for seed in ("13", "42", "2026")
        })
        for context in contexts:
            entry: dict[str, Any] = {
                "context": context,
                "rounds": {},
                "checkpoint_log": None,
                "markers": {},
            }
            checkpoint_log_name = f"{context}/checkpoint_log.jsonl"
            if checkpoint_log_name in names:
                try:
                    raw = zf.read(checkpoint_log_name)
                    entry["checkpoint_log"] = {
                        "member": checkpoint_log_name,
                        "sha256": sha256_bytes(raw),
                        "records": read_jsonl_bytes(raw),
                    }
                except Exception as exc:
                    entry["checkpoint_log"] = {"status": "ERROR", "error": repr(exc)}
            else:
                entry["checkpoint_log"] = {"status": "MISSING"}

            for round_no, checkpoint in enumerate(("S1", "S2", "S3")):
                base = f"{context}/{checkpoint}"
                train_log_name = f"{base}/adapter/train_log.json"
                adapter_config_name = f"{base}/adapter/adapter_config.json"
                eval_name = f"{base}/eval_dev.jsonl"
                entry["rounds"][checkpoint] = {
                    "train_log": safe_json(zf, train_log_name),
                    "adapter_config": safe_json(zf, adapter_config_name),
                    "prediction": summarize_prediction(zf, eval_name, dev_ids),
                }

            for marker in sorted(n for n in names if n.startswith(f"{context}/.done/")):
                if any(token in marker for token in (
                    "train_", "eval_dev_", "select_", "validate_log_"
                )):
                    entry["markers"][marker] = safe_json(zf, marker)
            result["contexts"].append(entry)

        # S0 and all registered runs: collect selection markers for context.
        result["selection_marker_names"] = sorted(
            n for n in names if "/.done/select_" in n
        )

    # Derived prediction package: manifest and exact file hashes.
    result["derived"]["exists"] = DERIVED.is_dir()
    if DERIVED.is_dir():
        derived_files = []
        for path in sorted(DERIVED.rglob("*")):
            if path.is_file():
                raw = path.read_bytes()
                item = {
                    "relative_path": str(path.relative_to(ROOT)),
                    "bytes": len(raw),
                    "sha256": sha256_bytes(raw),
                }
                if path.name.lower().endswith(".json"):
                    try:
                        item["json_content"] = json.loads(raw.decode("utf-8-sig"))
                    except Exception as exc:
                        item["json_error"] = repr(exc)
                elif path.suffix.lower() == ".jsonl":
                    try:
                        rows = read_jsonl_bytes(raw)
                        item["rows"] = len(rows)
                        item["first_row_keys"] = sorted(rows[0].keys()) if rows else []
                        item["status_counts"] = dict(
                            Counter(str(r.get("status")) for r in rows)
                        )
                    except Exception as exc:
                        item["jsonl_error"] = repr(exc)
                derived_files.append(item)
        result["derived"]["files"] = derived_files

    json_path = RUN_DIR / "g5_9_provenance_deep.json"
    json_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Compact CSV: one row per method/seed/checkpoint.
    csv_path = RUN_DIR / "checkpoint_prediction_inventory.csv"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "context", "checkpoint", "prediction_member", "prediction_sha256",
            "rows", "unique_problem_ids", "duplicate_ids", "missing_ids",
            "outside_dev_ids", "ids_equal_d_dev", "status_counts",
            "train_log_member", "train_log_status", "adapter_config_status",
        ])
        writer.writeheader()
        for context in result["contexts"]:
            for checkpoint, item in context["rounds"].items():
                pred = item["prediction"]
                train = item["train_log"]
                adapter = item["adapter_config"]
                writer.writerow({
                    "context": context["context"],
                    "checkpoint": checkpoint,
                    "prediction_member": pred.get("member"),
                    "prediction_sha256": pred.get("sha256"),
                    "rows": pred.get("rows"),
                    "unique_problem_ids": pred.get("unique_problem_ids"),
                    "duplicate_ids": pred.get("duplicate_ids"),
                    "missing_ids": pred.get("missing_ids"),
                    "outside_dev_ids": pred.get("outside_dev_ids"),
                    "ids_equal_d_dev": pred.get("ids_equal_d_dev"),
                    "status_counts": json.dumps(pred.get("status_counts", {})),
                    "train_log_member": train.get("member"),
                    "train_log_status": train.get("status"),
                    "adapter_config_status": adapter.get("status"),
                })

    txt_path = RUN_DIR / "g5_9_provenance_deep_summary.txt"
    lines = [
        f"RUN_ID={RUN_ID}",
        f"ZIP_INTEGRITY={result['zip_integrity']}",
        f"MAIN_ZIP_SHA256={result['archive_sha256']}",
        f"D_DEV_UNIQUE_IDS={len(dev_ids)}",
        f"S0_PREDICTION={json.dumps(result['s0']['prediction'], ensure_ascii=False)}",
        f"S0_MARKER={json.dumps(result['s0']['marker'], ensure_ascii=False)}",
        f"S0_SUMMARY={json.dumps(result['s0']['summary'], ensure_ascii=False)}",
        f"CONTEXT_COUNT={len(result['contexts'])}",
        f"DERIVED_FILE_COUNT={len(result['derived'].get('files', []))}",
        f"JSON_REPORT={json_path}",
        f"CSV_REPORT={csv_path}",
    ]
    txt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("G5_9_PROVENANCE_DEEP=COMPLETED")
    print(f"ZIP_INTEGRITY={result['zip_integrity']}")
    print(f"D_DEV_UNIQUE_IDS={len(dev_ids)}")
    print(f"S0_ROWS={result['s0']['prediction'].get('rows')}")
    print(f"S0_IDS_EQUAL_D_DEV={result['s0']['prediction'].get('ids_equal_d_dev')}")
    print(f"CONTEXT_COUNT={len(result['contexts'])}")
    print(f"DERIVED_FILE_COUNT={len(result['derived'].get('files', []))}")
    print(f"OUTPUT_DIR={RUN_DIR}")

if __name__ == "__main__":
    main()
