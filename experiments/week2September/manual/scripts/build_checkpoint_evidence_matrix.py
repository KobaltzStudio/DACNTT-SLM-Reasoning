from pathlib import Path
import csv
import hashlib
import json
import re
from collections import defaultdict

MANUAL = Path(__file__).resolve().parents[1]
AUDIT = MANUAL / "reports/p1p2_integration/checkpoint_inventory_audit"
OUT_CSV = AUDIT / "checkpoint_evidence_matrix.csv"
OUT_JSON = AUDIT / "checkpoint_evidence_matrix.json"

BASE_MATRIX = AUDIT / "checkpoint_inventory_matrix.csv"
ARTIFACTS = AUDIT / "checkpoint_inventory_artifacts.csv"
DIR_INVENTORY = AUDIT / "adapter_directory_inventory.csv"
FILE_INVENTORY = AUDIT / "adapter_metadata_inventory.csv"
ALIAS_FILE = AUDIT / "b4_b5_alias_markers.csv"

SIDECAR_ROOT = MANUAL / "reports/capability_g4_validation"
PREDICTION_ROOTS = [
    MANUAL / "reports/p1p2_integration/derived_predictions",
    MANUAL / "reports/task7",
    MANUAL / "reports",
]

EXPECTED_CONFIG_HASH = (
    "17cf4b837dc42ac5145aea762847ca5dfba4bae58d253560b3b0dd6a254b73c5"
)

FIELDS = [
    "method", "seed", "round", "run_id",
    "has_adapter_config", "has_train_log", "has_weights",
    "weights_sha256", "weights_source_paths", "unique_weights_copy_count",
    "has_dev_prediction", "prediction_path", "prediction_rows",
    "prediction_unique_ids", "prediction_coverage_status",
    "has_capability_sidecar", "sidecar_path", "sidecar_coverage_status",
    "sidecar_fingerprint", "sidecar_config_hash", "config_hash_status",
    "checkpoint_hash_status", "train_log_hash_status",
    "reused_from", "alias_status", "evidence_status", "blocker",
]

def read_csv(path):
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def read_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def sha256_file(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def truth(value):
    return str(value).strip().lower() in {"true", "1", "yes"}

def context_from_path(raw_path):
    p = str(raw_path).replace("/", "\\")

    method_match = re.search(
        r"(B[2345])(?:_seed|\\seed_?)(\d+)",
        p,
        re.IGNORECASE,
    )
    if not method_match:
        return None

    method = method_match.group(1).upper()
    seed = method_match.group(2)

    round_match = re.search(
        r"student_ckpt_00([123])",
        p,
        re.IGNORECASE,
    )
    if not round_match:
        round_match = re.search(
            r"(?:_S|\\S)([123])(?:[._\\]|$)",
            p,
            re.IGNORECASE,
        )

    if not round_match:
        return None

    return method, seed, f"S{round_match.group(1)}"


def prediction_context_from_name(path):
    full_path = str(path).replace("/", "\\")
    filename = Path(path).name

    method_seed_match = re.search(
        r"(B[2345])(?:_seed|\\seed_?)(\d+)",
        full_path,
        re.IGNORECASE,
    )
    if not method_seed_match:
        return None

    round_match = re.search(
        r"student_ckpt_00([123])",
        filename,
        re.IGNORECASE,
    )
    if not round_match:
        round_match = re.search(
            r"_S([123])(?:[._]|$)",
            filename,
            re.IGNORECASE,
        )

    if not round_match:
        return None

    return (
        method_seed_match.group(1).upper(),
        method_seed_match.group(2),
        f"S{round_match.group(1)}",
    )


def inspect_jsonl(path):
    rows = 0
    ids = []
    errors = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
                rows += 1
                value = obj.get("problem_id", obj.get("id"))
                if value is not None:
                    ids.append(str(value))
            except Exception as exc:
                errors.append(f"line {line_no}: {exc}")

    return {
        "rows": rows,
        "unique_ids": len(set(ids)),
        "errors": errors,
    }

def find_prediction_files():
    found = defaultdict(list)
    seen = set()

    for root in PREDICTION_ROOTS:
        if not root.exists():
            continue

        for path in root.rglob("*.jsonl"):
            resolved = str(path.resolve())
            if resolved in seen:
                continue
            seen.add(resolved)

            # Ignore unrelated datasets and test artifacts.
            if any(x in resolved.lower() for x in (
                "\\smoke", "\\smoke_tests", "\\__pycache__", "\\.venv\\"
            )):
                continue

            key = prediction_context_from_name(path)
            if key:
                found[key].append(path)

    return found

def main():
    base_rows = read_csv(BASE_MATRIX)
    artifact_rows = read_csv(ARTIFACTS)
    dir_rows = read_csv(DIR_INVENTORY)
    file_rows = read_csv(FILE_INVENTORY)
    alias_rows = read_csv(ALIAS_FILE)

    if len(base_rows) != 36:
        raise RuntimeError(f"Expected 36 registered contexts, got {len(base_rows)}")

    # Map weights and metadata files to registered contexts.
    weight_files = defaultdict(list)
    adapter_configs = defaultdict(list)
    train_logs = defaultdict(list)

    for row in file_rows:
        key = context_from_path(row.get("ParentDirectory", ""))
        if not key:
            continue

        filename = row.get("FileName", "")
        if filename == "adapter_model.safetensors":
            weight_files[key].append(row)
        elif filename == "adapter_model.bin":
            weight_files[key].append(row)
        elif filename == "adapter_config.json":
            adapter_configs[key].append(row)
        elif filename == "train_log.json":
            train_logs[key].append(row)

    # Include structured checkpoint artifact records as additional evidence.
    structured_artifacts = defaultdict(list)
    for row in artifact_rows:
        key = (
            row.get("method", "").upper(),
            str(row.get("seed", "")),
            row.get("round", ""),
        )
        if key[0] and key[1] and key[2]:
            structured_artifacts[key].append(row)

    # Sidecar evidence.
    sidecars = {}
    for root in SIDECAR_ROOT.iterdir() if SIDECAR_ROOT.exists() else []:
        if not root.is_dir():
            continue
        m = re.fullmatch(r"(B[2345])_seed(\d+)_S([123])", root.name, re.I)
        if m:
            sidecars[(m.group(1).upper(), m.group(2), f"S{m.group(3)}")] = root

    # Alias evidence. Keep only markers that explicitly declare reused_from.
    aliases = defaultdict(list)
    for row in alias_rows:
        reused = (row.get("ReusedFrom") or "").strip()
        if not reused:
            continue
        key = context_from_path(row.get("Path", ""))
        if key:
            aliases[key].append({
                "reused_from": reused,
                "reason": row.get("Reason", ""),
                "marker_path": row.get("Path", ""),
            })

    predictions = find_prediction_files()
    output = []

    for base in base_rows:
        method = base["method"].upper()
        seed = str(base["seed"])
        round_id = base["round"]
        key = (method, seed, round_id)
        run_id = f"{method}_seed{seed}_{round_id}"

        weights = weight_files.get(key, [])
        configs = adapter_configs.get(key, [])
        logs = train_logs.get(key, [])

        # Deduplicate identical weight files by their content hash.
        weight_hashes = sorted({
            x.get("SHA256", "").lower()
            for x in weights if x.get("SHA256")
        })
        weight_paths = sorted({
            x.get("FullPath", "")
            for x in weights if x.get("FullPath")
        })

        has_weights = bool(weight_hashes)
        has_config = bool(configs)
        has_train_log = bool(logs)

        # Prediction candidate: choose a file only if exactly one candidate exists.
        pred_candidates = predictions.get(key, [])
        pred_path = ""
        pred_rows = ""
        pred_unique = ""
        pred_status = "NOT_FOUND"

        if len(pred_candidates) == 1:
            pred_path = str(pred_candidates[0])
            info = inspect_jsonl(pred_candidates[0])
            pred_rows = info["rows"]
            pred_unique = info["unique_ids"]
            if info["errors"]:
                pred_status = "JSONL_ERROR"
            elif info["rows"] == 500 and info["unique_ids"] == 500:
                pred_status = "500_UNIQUE_IDS"
            else:
                pred_status = "INCOMPLETE_OR_NON_DDEV"
        elif len(pred_candidates) > 1:
            pred_status = "MULTIPLE_CANDIDATES"

        # Capability sidecar.
        sidecar = sidecars.get(key)
        has_sidecar = False
        sidecar_coverage = "NOT_FOUND"
        fingerprint_value = ""
        sidecar_config_hash = ""
        config_status = "NOT_CHECKED"
        checkpoint_status = "NOT_CHECKED"
        train_log_status = "NOT_CHECKED"

        if sidecar:
            manifest_path = sidecar / "student_capability_evaluation_manifest.json"
            fingerprint_path = sidecar / "input_fingerprint.json"
            lineage_path = sidecar / "checkpoint_lineage.json"
            coverage_path = sidecar / "prediction_coverage_report.json"

            required = [
                manifest_path, fingerprint_path, lineage_path, coverage_path,
                sidecar / "capability_metrics.csv",
                sidecar / "capability_metrics.jsonl",
            ]
            has_sidecar = all(p.is_file() for p in required)

            if has_sidecar:
                manifest = read_json(manifest_path)
                fingerprint = read_json(fingerprint_path)
                lineage = read_json(lineage_path)
                coverage = read_json(coverage_path)

                fingerprint_value = fingerprint.get("fingerprint", "")
                sidecar_config_hash = (
                    manifest.get("input_hashes", {}).get("config", "")
                )

                inputs_equal = (
                    manifest.get("input_hashes", {}) ==
                    fingerprint.get("inputs", {})
                )
                config_status = (
                    "MATCHES_REGISTERED_P1_CONFIG"
                    if sidecar_config_hash == EXPECTED_CONFIG_HASH
                    else "MISMATCH"
                )

                checkpoint_status = (
                    "MANIFEST_LINEAGE_HASH_MATCH"
                    if manifest.get("input_hashes", {}).get("checkpoint")
                    == lineage.get("checkpoint_sha256")
                    else "MISMATCH"
                )

                expected_train_log = manifest.get("input_hashes", {}).get("train_log")
                lineage_train_log = lineage.get("train_log")
                actual_train_log_hash = None
                if lineage_train_log and Path(lineage_train_log).is_file():
                    actual_train_log_hash = sha256_file(Path(lineage_train_log))

                train_log_status = (
                    "PHYSICAL_HASH_MATCH"
                    if actual_train_log_hash and actual_train_log_hash == expected_train_log
                    else "UNVERIFIED_OR_MISMATCH"
                )

                if (
                    inputs_equal and
                    config_status == "MATCHES_REGISTERED_P1_CONFIG" and
                    checkpoint_status == "MANIFEST_LINEAGE_HASH_MATCH" and
                    coverage.get("status") == "PASS"
                ):
                    sidecar_coverage = "PASS"
                else:
                    sidecar_coverage = "INCOMPLETE_OR_MISMATCH"

        alias_entries = aliases.get(key, [])
        reused_from = ";".join(sorted({
            x["reused_from"] for x in alias_entries
        }))
        alias_status = "ALIAS_MARKER_PRESENT" if alias_entries else "NO_ALIAS_MARKER_FOUND"

        blockers = []
        if not has_weights:
            blockers.append("WEIGHTS_NOT_FOUND_IN_CURRENT_INVENTORY")
        if not has_train_log:
            blockers.append("TRAIN_LOG_NOT_FOUND_IN_CURRENT_INVENTORY")
        if pred_status != "500_UNIQUE_IDS":
            blockers.append(f"PREDICTION_{pred_status}")
        if not has_sidecar:
            blockers.append("CAPABILITY_SIDECAR_NOT_FOUND_OR_INCOMPLETE")
        elif sidecar_coverage != "PASS":
            blockers.append("SIDECAR_VALIDATION_INCOMPLETE")
        if alias_entries:
            blockers.append("ALIAS_IDENTITY_REQUIRES_DEDUPLICATION")

        if has_sidecar and sidecar_coverage == "PASS":
            evidence_status = "SIDECAR_VERIFIED"
        elif has_weights and has_train_log:
            evidence_status = "WEIGHTS_AND_METADATA_FOUND"
        elif has_config or has_train_log:
            evidence_status = "METADATA_ONLY"
        elif pred_status == "500_UNIQUE_IDS":
            evidence_status = "PREDICTION_ONLY"
        else:
            evidence_status = "MISSING_IN_CURRENT_INVENTORY"

        output.append({
            "method": method,
            "seed": seed,
            "round": round_id,
            "run_id": run_id,
            "has_adapter_config": has_config,
            "has_train_log": has_train_log,
            "has_weights": has_weights,
            "weights_sha256": ";".join(weight_hashes),
            "weights_source_paths": ";".join(weight_paths),
            "unique_weights_copy_count": len(weight_hashes),
            "has_dev_prediction": bool(pred_path),
            "prediction_path": pred_path,
            "prediction_rows": pred_rows,
            "prediction_unique_ids": pred_unique,
            "prediction_coverage_status": pred_status,
            "has_capability_sidecar": has_sidecar,
            "sidecar_path": str(sidecar) if sidecar else "",
            "sidecar_coverage_status": sidecar_coverage,
            "sidecar_fingerprint": fingerprint_value,
            "sidecar_config_hash": sidecar_config_hash,
            "config_hash_status": config_status,
            "checkpoint_hash_status": checkpoint_status,
            "train_log_hash_status": train_log_status,
            "reused_from": reused_from,
            "alias_status": alias_status,
            "evidence_status": evidence_status,
            "blocker": ";".join(blockers),
        })

    # Stable ordering.
    output.sort(key=lambda x: (
        x["method"], int(x["seed"]), int(x["round"][1:])
    ))

    AUDIT.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(output)

    summary = {
        "schema_version": "p1p2.checkpoint_evidence_matrix.v1",
        "registered_context_count": len(output),
        "unique_weight_hash_count": len({
            h
            for row in output
            for h in row["weights_sha256"].split(";")
            if h
        }),
        "contexts_with_weights": sum(bool(x["has_weights"]) for x in output),
        "contexts_with_train_log": sum(bool(x["has_train_log"]) for x in output),
        "contexts_with_500_prediction": sum(
            x["prediction_coverage_status"] == "500_UNIQUE_IDS" for x in output
        ),
        "contexts_with_sidecar_pass": sum(
            x["sidecar_coverage_status"] == "PASS" for x in output
        ),
        "contexts_with_alias_marker": sum(
            x["alias_status"] == "ALIAS_MARKER_PRESENT" for x in output
        ),
        "config_hash_expected": EXPECTED_CONFIG_HASH,
        "output_csv": str(OUT_CSV),
        "contexts": output,
    }

    with OUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print("CHECKPOINT_EVIDENCE_MATRIX=CREATED")
    print("REGISTERED_CONTEXTS:", len(output))
    print("UNIQUE_WEIGHT_HASHES:", summary["unique_weight_hash_count"])
    print("CONTEXTS_WITH_WEIGHTS:", summary["contexts_with_weights"])
    print("CONTEXTS_WITH_TRAIN_LOG:", summary["contexts_with_train_log"])
    print("CONTEXTS_WITH_500_PREDICTION:", summary["contexts_with_500_prediction"])
    print("CONTEXTS_WITH_SIDECAR_PASS:", summary["contexts_with_sidecar_pass"])
    print("CONTEXTS_WITH_ALIAS_MARKER:", summary["contexts_with_alias_marker"])
    print("CSV:", OUT_CSV)
    print("JSON:", OUT_JSON)

if __name__ == "__main__":
    main()
