#!/usr/bin/env python3
"""Build auditable capability learning dynamics from immutable P1/P2 sidecars.

The builder discovers sidecars recursively, validates their own manifests and
recorded hashes, normalizes the evaluator's metric schema, and publishes
seed-13 outputs without overwriting existing artifacts.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath
from typing import Any

from capability_eval import load_approved_gold, validate_manifest_count
from p1p2_controller import sha256
from p1p2_paths import artifact_path, legacy_root
from select_checkpoint_on_dev import verified_prediction

CAPABILITIES = (
    "addition", "subtraction", "multiplication", "division",
    "percentage", "fraction", "ratio",
)
EXPECTED_SUPPORT = {
    "addition": 30, "subtraction": 51, "multiplication": 73,
    "division": 47, "percentage": 29, "fraction": 31, "ratio": 30,
}
MANIFEST_NAME = "student_capability_evaluation_manifest.json"
G4_CHECKPOINTS = ("integration_staging", "G4_CHECKPOINT_AUDIT", "extracted_checkpoints")
REQUIRED_FILES = (
    "capability_metrics.jsonl",
    "prediction_coverage_report.json",
    "checkpoint_lineage.json",
    "input_fingerprint.json",
)
OUTPUT_NAMES = (
    "capability_learning_dynamics_seed13.csv",
    "capability_learning_dynamics_seed13.json",
    "capability_learning_dynamics_seed13.md",
    "capability_sidecar_inventory_seed13.csv",
)

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as f:
        value = json.load(f)
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value

def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8-sig") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            obj = json.loads(line)
            if not isinstance(obj, dict):
                raise ValueError(f"{path}:{line_no}: expected JSON object")
            rows.append(obj)
    return rows

def first_value(*values: Any) -> Any:
    for value in values:
        if value is not None and value != "":
            return value
    return None

def normalize_round(value: Any, checkpoint: Any = None) -> str:
    raw = str(first_value(value, checkpoint, "")).strip()
    if raw in {"0", "S0", "s0", "round_000", "round_0"}:
        return "S0"
    if raw.upper() in {"S1", "S2", "S3"}:
        return raw.upper()
    if raw.startswith("round_"):
        try:
            n = int(raw.split("_")[-1])
            return f"S{n + 1}" if n in (0, 1, 2) else f"S{n}"
        except ValueError:
            pass
    try:
        n = int(raw)
        return f"S{n}"
    except ValueError:
        pass
    return str(first_value(checkpoint, raw, "UNKNOWN"))

def validate_one(sidecar: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    problems: list[str] = []
    manifest_path = sidecar / MANIFEST_NAME
    if not manifest_path.is_file():
        raise ValueError("manifest_missing")
    manifest = read_json(manifest_path)
    if manifest.get("schema_version") != "p1p2.capability-manifest.v1":
        raise ValueError(f"invalid_manifest_schema:{manifest_path}")

    file_paths = {name: sidecar / name for name in REQUIRED_FILES}
    missing = [name for name, p in file_paths.items() if not p.is_file()]
    if missing:
        raise ValueError("required_files_missing:" + ",".join(missing))

    lineage = read_json(file_paths["checkpoint_lineage.json"])
    fingerprint = read_json(file_paths["input_fingerprint.json"])
    coverage = read_json(file_paths["prediction_coverage_report.json"])
    metrics = read_jsonl(file_paths["capability_metrics.jsonl"])

    # The v1 evaluator writes input hashes in both the manifest and fingerprint.
    inputs = fingerprint.get("inputs")
    if not isinstance(inputs, dict) or not inputs:
        problems.append("fingerprint_inputs_missing")
        inputs = {}
    manifest_inputs = manifest.get("input_hashes")
    if manifest_inputs != inputs:
        problems.append("manifest_fingerprint_inputs_mismatch")

    recorded_fingerprint = fingerprint.get("fingerprint")
    if not recorded_fingerprint:
        problems.append("fingerprint_missing")
    if recorded_fingerprint:
        canonical = json.dumps(inputs, sort_keys=True, separators=(",", ":")).encode("utf-8")
        expected_fp = hashlib.sha256(canonical).hexdigest()
        if recorded_fingerprint != expected_fp:
            problems.append("fingerprint_digest_mismatch")

    # Validate sidecar output hashes if present. Manifest does not hash itself.
    outputs = manifest.get("outputs", {})
    if not isinstance(outputs, dict) or set(outputs) != {*REQUIRED_FILES, "capability_metrics.csv"}:
        problems.append("manifest_output_inventory_mismatch")
    else:
        for name, meta in outputs.items():
            path = sidecar / name
            if not path.is_file():
                problems.append(f"manifest_output_missing:{name}")
                continue
            expected_hash = meta.get("sha256") if isinstance(meta, dict) else None
            if not expected_hash or sha256_file(path) != expected_hash:
                problems.append(f"manifest_output_hash_mismatch:{name}")

    method = str(first_value(manifest.get("method"), lineage.get("method"), "UNKNOWN"))
    seed_raw = first_value(manifest.get("seed"), lineage.get("seed"))
    try:
        seed = int(seed_raw)
    except (TypeError, ValueError):
        seed = -1
        problems.append("seed_missing_or_invalid")

    round_value = first_value(manifest.get("round"), lineage.get("round"))
    checkpoint = first_value(
        manifest.get("checkpoint"),
        lineage.get("checkpoint_id"),
        lineage.get("checkpoint"),
    )
    checkpoint_label = normalize_round(round_value, checkpoint)
    expected_round = int(checkpoint_label[1:]) if checkpoint_label in ("S0", "S1", "S2", "S3") else None
    if (expected_round is None or manifest.get("checkpoint") != checkpoint_label
            or (lineage.get("method"), lineage.get("seed"), lineage.get("round"))
            != (method, seed, expected_round)
            or manifest.get("round") != expected_round
            or lineage.get("run_id") != manifest.get("run_id")
            or (checkpoint_label == "S0") != (method == "SHARED" and seed == 0)):
        problems.append("manifest_lineage_identity_mismatch")

    # Require the approved-85 capability evaluation protocol, not legacy 22-row data.
    gold_n = first_value(coverage.get("gold_records"), coverage.get("gold_unique_ids"),
                         coverage.get("gold_count"), coverage.get("approved_gold_records"))
    pred_n = first_value(coverage.get("prediction_records"), coverage.get("prediction_count"))
    pred_unique = first_value(coverage.get("prediction_unique_ids"), coverage.get("prediction_unique_count"))
    status = str(coverage.get("status", "")).upper()
    policy = str(first_value(coverage.get("strict_correctness_policy"),
                             coverage.get("correctness_policy"),
                             manifest.get("strict_metric"), ""))
    gold_policy = str(first_value(coverage.get("gold_policy"), manifest.get("gold_policy"), ""))

    try:
        if int(gold_n) != 85:
            problems.append(f"gold_records_not_85:{gold_n}")
    except (TypeError, ValueError):
        problems.append("gold_record_count_missing")
    try:
        if int(pred_n) != 500 or int(pred_unique) != 500:
            problems.append(f"prediction_coverage_not_500:{pred_n}/{pred_unique}")
    except (TypeError, ValueError):
        problems.append("prediction_coverage_fields_missing")
    if status not in {"PASS", "PASS_WITH_COVERAGE_REPORTED"}:
        problems.append(f"coverage_status_not_pass:{status or 'missing'}")
    if policy != "status == valid" or coverage.get("lenient_correct_excluded") is not True:
        problems.append(f"strict_correctness_policy_unrecognized:{policy}")
    if (coverage.get("split") != "D_dev" or coverage.get("gold_unique_ids") != 85
            or coverage.get("gold_matched_prediction_ids") != 85):
        problems.append("gold_or_dev_coverage_mismatch")
    if gold_policy != "approved_85_primary":
        problems.append(f"gold_policy_not_approved_85:{gold_policy}")

    # Cross-check lineage hashes against fingerprint aliases where available.
    lineage_checkpoint_hash = lineage.get("checkpoint_sha256")
    fingerprint_checkpoint_hash = inputs.get("checkpoint")
    lineage_prediction_hash = first_value(
        lineage.get("prediction_sha256"), lineage.get("dev_predictions_sha256")
    )
    fingerprint_prediction_hash = inputs.get("dev_predictions")
    if lineage_checkpoint_hash and fingerprint_checkpoint_hash and lineage_checkpoint_hash != fingerprint_checkpoint_hash:
        problems.append("checkpoint_hash_lineage_fingerprint_mismatch")
    if lineage_prediction_hash and fingerprint_prediction_hash and lineage_prediction_hash != fingerprint_prediction_hash:
        problems.append("prediction_hash_lineage_fingerprint_mismatch")
    checkpoint_hash = first_value(lineage_checkpoint_hash, fingerprint_checkpoint_hash)
    prediction_hash = first_value(lineage_prediction_hash, fingerprint_prediction_hash)
    if not checkpoint_hash:
        problems.append("checkpoint_hash_missing")
    if not prediction_hash:
        problems.append("prediction_hash_missing")

    checkpoint_path = first_value(lineage.get("checkpoint_path"), coverage.get("checkpoint_path"))
    prediction_path = first_value(
        coverage.get("prediction_file"), coverage.get("prediction_path"),
        lineage.get("prediction_file"), lineage.get("dev_predictions")
    )

    # Validate exact seven capability rows and normalize old/new evaluator field names.
    by_cap = {}
    for row in metrics:
        cap = str(row.get("capability", "")).strip().lower()
        if cap in by_cap:
            problems.append(f"duplicate_capability:{cap}")
        by_cap[cap] = row
    if set(by_cap) != set(CAPABILITIES):
        problems.append("capability_rows_not_exactly_seven")

    normalized = []
    for cap in CAPABILITIES:
        row = by_cap.get(cap)
        if row is None:
            continue
        try:
            support = int(row.get("n_support"))
            correct = int(row.get("n_correct"))
            incorrect = int(first_value(row.get("n_incorrect"), support - correct))
            mastery = float(first_value(row.get("mastery"), row.get("mastery_accuracy")))
            ci_low = float(row.get("ci95_low"))
            ci_high = float(row.get("ci95_high"))
        except (TypeError, ValueError):
            problems.append(f"invalid_metric_values:{cap}")
            continue
        if support != EXPECTED_SUPPORT[cap]:
            problems.append(f"support_mismatch:{cap}:{support}")
        if correct + incorrect != support:
            problems.append(f"correctness_count_mismatch:{cap}")
        if support <= 0 or not math.isclose(mastery, correct / support, rel_tol=1e-8, abs_tol=1e-8):
            problems.append(f"mastery_mismatch:{cap}")
        if not (0.0 <= ci_low <= ci_high <= 1.0):
            problems.append(f"invalid_ci:{cap}")
        normalized.append({
            "method": method,
            "seed": seed,
            "checkpoint": checkpoint_label,
            "checkpoint_id": str(first_value(row.get("checkpoint_id"), checkpoint, "")),
            "capability": cap,
            "n_gold_records": 85,
            "n_support": support,
            "n_correct": correct,
            "n_incorrect": incorrect,
            "mastery": mastery,
            "ci95_low": ci_low,
            "ci95_high": ci_high,
            "sidecar_source": str(sidecar.resolve()),
            "sidecar_fingerprint": str(first_value(recorded_fingerprint, manifest.get("fingerprint"), "")),
            "checkpoint_sha256": str(checkpoint_hash or ""),
            "prediction_sha256": str(prediction_hash or ""),
            "checkpoint_path": str(checkpoint_path or ""),
            "prediction_path": str(prediction_path or ""),
            "shared_checkpoint_group": str(first_value(
                lineage.get("shared_checkpoint_group"),
                manifest.get("shared_checkpoint_group"), ""
            )),
            "checkpoint_alias_status": "not_established",
        })

    if len(normalized) != 7:
        problems.append(f"normalized_metric_rows_not_7:{len(normalized)}")

    record = {
        "sidecar_source": str(sidecar.resolve()),
        "sidecar_manifest_sha256": sha256_file(manifest_path),
        "input_hashes": inputs,
        "manifest_schema": manifest.get("schema_version", manifest.get("schema", "unspecified")),
        "method": method,
        "seed": seed,
        "checkpoint": checkpoint_label,
        "checkpoint_id": str(first_value(lineage.get("checkpoint_id"), checkpoint, "")),
        "gold_records": gold_n,
        "prediction_records": pred_n,
        "coverage_status": status,
        "gold_policy": gold_policy,
        "fingerprint": recorded_fingerprint,
        "checkpoint_sha256": checkpoint_hash,
        "prediction_sha256": prediction_hash,
        "checkpoint_path": checkpoint_path,
        "prediction_path": prediction_path,
        "shared_checkpoint_group": first_value(
            lineage.get("shared_checkpoint_group"),
            manifest.get("shared_checkpoint_group")
        ),
        "metric_rows": len(metrics),
        "valid": not problems,
        "reasons": problems,
    }
    if problems:
        raise SidecarRejected(record)
    return normalized, record

class SidecarRejected(Exception):
    def __init__(self, record: dict[str, Any]):
        self.record = record
        super().__init__(";".join(record["reasons"]))

def discover(roots: list[Path]) -> list[Path]:
    found: set[Path] = set()
    for root in roots:
        if not root.exists():
            continue
        if root.is_file() and root.name == MANIFEST_NAME:
            found.add(root.parent.resolve())
            continue
        if root.is_dir():
            for manifest in root.rglob(MANIFEST_NAME):
                directories = manifest.relative_to(root).parts[:-1]
                if not any(part.startswith(".") for part in directories):
                    found.add(manifest.parent.resolve())
    return sorted(found, key=lambda p: str(p).lower())


def canonicalize(inventory, preferred=None):
    preferred = preferred or {}
    groups = {}
    for row in inventory:
        if row.get("valid"):
            key = row["method"], row["seed"], row["checkpoint"]
            groups.setdefault(key, []).append(row)
    chosen = set()
    for key, group in groups.items():
        identities = {(row["prediction_sha256"], row["checkpoint_sha256"], row["fingerprint"]) for row in group}
        canonical = group[0]["sidecar_source"]
        if len(identities) != 1:
            expected = preferred.get(key)
            matches = [row for row in group
                       if (row["prediction_sha256"], row["checkpoint_sha256"]) == expected]
            if len(matches) != 1:
                for row in group:
                    row["valid"] = False
                    row["reasons"].append("conflicting_logical_checkpoint")
                continue
            canonical = matches[0]["sidecar_source"]
        chosen.add(canonical)
        for row in group:
            row["canonical_source"] = canonical
            row["duplicate"] = row["sidecar_source"] != canonical and len(identities) == 1
            row["alternate_provenance"] = row["sidecar_source"] != canonical and len(identities) > 1
    return chosen


def gold_inputs(manual):
    paths = {
        "gold_manifest": manual / "data/gold_vfinal/gold_vfinal_manifest.json",
        "gold_labels": manual / "data/gold_vfinal/supplement_annotations_vfinal.jsonl",
        "approval_csv": manual / "data/gold_releases/vFinal_2026-11-16/gold_supplement_85_approved_review.csv",
        "dev_ids": manual / "splits/d_dev_ids.txt",
    }
    validate_manifest_count(paths["gold_manifest"])
    dev_ids = set(paths["dev_ids"].read_text(encoding="utf-8-sig").split())
    load_approved_gold(paths["gold_labels"], paths["approval_csv"], dev_ids)
    return {name: sha256_file(path) for name, path in paths.items()}


def locate_prediction(manual, row, source_root=None):
    method, seed, checkpoint = row["method"], row["seed"], row["checkpoint"]
    group = f"{method}_seed{seed}"
    candidates = []
    if row.get("prediction_path"):
        if source_root is None:
            locator = Path(row["prediction_path"])
            candidates.append(locator if locator.is_absolute() else manual / locator)
        else:
            candidates.append(artifact_path(manual, row["prediction_path"], source_root))
    if method == "SHARED":
        candidates.append(manual / "runs/main/S0/eval_dev.jsonl")
    else:
        namespace = "p1p2_integration" if method in {"P1-DEFICIT", "P1P2"} else "main"
        candidates.append(manual / "runs" / namespace / group / checkpoint / "eval_dev.jsonl")
        if method == "B4" and checkpoint in {"S1", "S2", "S3"}:
            candidates.append(manual / "reports/p1p2_integration/derived_predictions" / group
                              / f"eval_student_ckpt_{int(checkpoint[1:]):03d}_dev_status.jsonl")
    existing = [path for path in candidates if path.is_file()]
    matched = next((path for path in existing if sha256_file(path) == row["prediction_sha256"]), None)
    if matched is None:
        reason = "prediction_bytes_mismatch" if existing else "prediction_bytes_missing"
        raise SidecarRejected({**row, "valid": False, "reasons": [reason]})
    return matched


def mapped_checkpoint_path(manual: Path, recorded: str, source_root: PureWindowsPath) -> Path:
    """Map the manual tree and the separate, fingerprinted G4 checkpoint archive."""
    if len(source_root.parents) > 2 and len(manual.parents) > 2:
        g4_source = source_root.parents[2].joinpath(*G4_CHECKPOINTS)
        if PureWindowsPath(recorded).is_relative_to(g4_source):
            return artifact_path(manual.parents[2].joinpath(*G4_CHECKPOINTS), recorded, g4_source)
    return artifact_path(manual, recorded, source_root)

def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "method", "seed", "checkpoint", "checkpoint_id", "capability",
        "n_gold_records", "n_support", "n_correct", "n_incorrect",
        "mastery", "ci95_low", "ci95_high", "sidecar_source",
        "sidecar_fingerprint", "checkpoint_sha256", "prediction_sha256",
        "checkpoint_path", "prediction_path", "shared_checkpoint_group",
        "checkpoint_alias_status",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

def main() -> int:
    ap = argparse.ArgumentParser(description="Audit and build G6 capability learning dynamics")
    ap.add_argument("--manual", required=True, help="Canonical P2 manual directory")
    ap.add_argument("--output", default=None)
    ap.add_argument("--extra-root", action="append", default=[])
    ap.add_argument("--legacy-windows-root", type=legacy_root,
                    help="Map archived Windows prediction/checkpoint paths to the staged manual root")
    ap.add_argument("--expected-sidecars", type=int, help="Optional historical count for comparison")
    ap.add_argument("--inventory-only", action="store_true")
    ap.add_argument("--seed", type=int, default=13)
    args = ap.parse_args()

    manual = Path(args.manual).resolve()
    output = Path(args.output).resolve() if args.output else manual / "reports/p1p2_integration/final_validation"

    # Scope discovery to the approved G5.9/G4 sidecar roots. The legacy
    # student_eval_2026-11-17 tree contains 22-Gold artifacts and is excluded.
    roots = [
        manual / "reports/capability/g5_9_real_data_s0",
        manual / "reports/capability/g5_9_historical_20261117",
        manual / "reports/capability_g4_validation",
        manual / "reports/p1p2_integration/capability_sidecars",
    ]
    roots.extend(Path(x).resolve() for x in args.extra_root)
    roots = list(dict.fromkeys(roots))

    print("G6_DISCOVERY_ROOTS:")
    for root in roots:
        print(f"  {root} | exists={root.exists()}")

    sidecars = discover(roots)
    print(f"G6_DISCOVERED_MANIFESTS: {len(sidecars)}")
    for path in sidecars:
        print(f"  SIDECAR: {path}")

    inventory: list[dict[str, Any]] = []
    accepted_metrics: list[dict[str, Any]] = []
    expected_gold = gold_inputs(manual)

    for sidecar in sidecars:
        try:
            metrics, record = validate_one(sidecar)
            if any(record["input_hashes"].get(key) != value for key, value in expected_gold.items()):
                raise SidecarRejected({**record, "valid": False, "reasons": ["gold_input_provenance_mismatch"]})
            prediction = locate_prediction(manual, record, args.legacy_windows_root)
            record["verified_prediction_path"] = str(prediction)
            for row in metrics:
                row["prediction_path"] = str(prediction)
            checkpoint = record.get("checkpoint_path")
            if checkpoint:
                checkpoint = (mapped_checkpoint_path(manual, checkpoint, args.legacy_windows_root)
                              if args.legacy_windows_root else Path(checkpoint))
                if args.legacy_windows_root and not checkpoint.exists():
                    raise SidecarRejected({**record, "valid": False, "reasons": ["checkpoint_bytes_missing"]})
                if checkpoint.exists() and sha256(checkpoint) != record["checkpoint_sha256"]:
                    raise SidecarRejected({**record, "valid": False, "reasons": ["checkpoint_bytes_mismatch"]})
            inventory.append(record)
            accepted_metrics.extend(metrics)
        except SidecarRejected as exc:
            inventory.append(exc.record)
        except Exception as exc:
            inventory.append({
                "sidecar_source": str(sidecar),
                "valid": False,
                "reasons": [f"read_error:{type(exc).__name__}:{exc}"],
            })

    preferred = {}
    for method in ("B4", "B5", "P1-DEFICIT", "P1P2"):
        for checkpoint in (1, 2, 3):
            if args.seed != 13:
                continue
            try:
                prediction, lineage = verified_prediction(manual, method, checkpoint)
            except (OSError, ValueError, KeyError):
                continue
            preferred[method, 13, f"S{checkpoint}"] = sha256(prediction), lineage["checkpoint_sha256"]
    canonical = canonicalize(inventory, preferred)
    accepted_count = sum(bool(row.get("valid")) for row in inventory)
    accepted_metrics = [row for row in accepted_metrics if row["sidecar_source"] in canonical]
    print(f"G6_ACCEPTED_SIDECARS: {accepted_count}")
    print(f"G6_REJECTED_SIDECARS: {len(inventory) - accepted_count}")

    target_methods = {"B4", "B5", "P1-DEFICIT", "P1P2"}
    seed_rows = [
        row for row in accepted_metrics
        if (
            (int(row["seed"]) == args.seed and row["method"] in target_methods)
            or (row["method"] == "SHARED" and int(row["seed"]) == 0 and row["checkpoint"] == "S0")
        )
    ]
    seed_inventory = [
        row for row in inventory
        if (
            (row.get("seed") == args.seed and row.get("method") in target_methods)
            or (row.get("method") == "SHARED" and row.get("seed") == 0 and row.get("checkpoint") == "S0")
        )
    ]

    # B4/B5 S1 prediction equality is recorded as an alias, not as proof
    # of physical weight equality. Physical states are deduplicated only
    # by matching checkpoint SHA-256.
    b4_s1_hashes = {
        row["prediction_sha256"] for row in seed_rows
        if row["method"] == "B4" and row["checkpoint"] == "S1" and row["prediction_sha256"]
    }
    b5_s1_hashes = {
        row["prediction_sha256"] for row in seed_rows
        if row["method"] == "B5" and row["checkpoint"] == "S1" and row["prediction_sha256"]
    }
    alias_hashes = b4_s1_hashes & b5_s1_hashes
    for row in seed_rows:
        if (
            row["method"] in {"B4", "B5"}
            and row["checkpoint"] == "S1"
            and row["prediction_sha256"] in alias_hashes
        ):
            row["checkpoint_alias_status"] = (
                "prediction_alias_confirmed_physical_weight_hash_not_independently_verified"
            )

    seed_rows.sort(key=lambda row: (
        row["method"],
        {"S0": 0, "S1": 1, "S2": 2, "S3": 3}.get(row["checkpoint"], 99),
        CAPABILITIES.index(row["capability"]),
    ))

    required_pairs = {("SHARED", "S0")}
    for method in ("B4", "B5", "P1-DEFICIT", "P1P2"):
        for checkpoint in ("S1", "S2", "S3"):
            required_pairs.add((method, checkpoint))

    available_pairs = {(row["method"], row["checkpoint"]) for row in seed_inventory if row.get("valid")}
    missing_pairs = sorted(
        required_pairs - available_pairs,
        key=lambda item: (item[0], {"S0": 0, "S1": 1, "S2": 2, "S3": 3}.get(item[1], 99)),
    )

    if args.inventory_only:
        output.mkdir(parents=True, exist_ok=True)
        report = output / "g6_pretraining_inventory.json"
        with report.open("x", encoding="utf-8") as stream:
            json.dump({
                "status": "PARTIAL" if missing_pairs else "PASS",
                "raw_sidecars": len(sidecars), "accepted_sidecars": accepted_count,
                "logical_sidecars": len(canonical),
                "duplicates": sum(bool(row.get("duplicate")) for row in inventory),
                "alternate_provenance_sidecars": sum(bool(row.get("alternate_provenance")) for row in inventory),
                "missing_method_checkpoint_pairs": missing_pairs,
                "gold_input_sha256": expected_gold, "sidecars": inventory, "rows": seed_rows,
            }, stream, indent=2)
        print(f"G6_INVENTORY={report}")
        return 0

    if not seed_rows:
        output.mkdir(parents=True, exist_ok=True)
        diagnostic = output / f"g6_sidecar_discovery_diagnostic_seed{args.seed}.json"
        if diagnostic.exists():
            print(f"G6_DIAGNOSTIC_EXISTS_NO_OVERWRITE: {diagnostic}")
            return 3
        diagnostic_payload = {
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "expected_sidecars": args.expected_sidecars,
            "discovered_sidecars": len(sidecars),
            "accepted_sidecars": accepted_count,
            "rejected_sidecars": len(inventory) - accepted_count,
            "all_sidecars": inventory,
        }
        diagnostic.write_text(json.dumps(diagnostic_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"G6_BUILD_STATUS: FAIL: no valid G6 sidecar metrics for seed {args.seed}")
        print(f"G6_DIAGNOSTIC: {diagnostic}")
        return 2

    discovery_ok = args.expected_sidecars is None or len(sidecars) == args.expected_sidecars
    validation_ok = accepted_count == len(sidecars)
    matrix_ok = not missing_pairs
    gate_complete = discovery_ok and validation_ok and matrix_ok

    output.mkdir(parents=True, exist_ok=True)
    if gate_complete:
        names = OUTPUT_NAMES
        status = "PASS"
    else:
        names = (
            "g6_partial_learning_dynamics_seed13.csv",
            "g6_partial_learning_dynamics_seed13.json",
            "g6_partial_learning_dynamics_seed13.md",
            "g6_partial_sidecar_inventory_seed13.json",
        )
        status = "PARTIAL"

    target_paths = [output / name for name in names]
    inventory_csv = output / "capability_sidecar_inventory_seed13.csv"
    existing = [str(path) for path in target_paths if path.exists()]
    if not gate_complete and inventory_csv.exists():
        existing.append(str(inventory_csv))
    if existing:
        print("G6_OUTPUT_EXISTS_NO_OVERWRITE:")
        for path in existing:
            print(f"  {path}")
        return 3

    inventory_payload = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "analysis_scope": f"single_seed_{args.seed}",
        "expected_sidecars_all_roots": args.expected_sidecars,
        "discovered_sidecars_all_roots": len(sidecars),
        "accepted_sidecars_all_roots": accepted_count,
        "rejected_sidecars_all_roots": len(inventory) - accepted_count,
        "seed13_scope_includes_shared_S0_once": True,
        "required_method_checkpoint_matrix": [
            {"method": method, "checkpoint": checkpoint}
            for method, checkpoint in sorted(
                required_pairs,
                key=lambda item: (item[0], {"S0": 0, "S1": 1, "S2": 2, "S3": 3}.get(item[1], 99)),
            )
        ],
        "missing_method_checkpoint_pairs": [
            {"method": method, "checkpoint": checkpoint} for method, checkpoint in missing_pairs
        ],
        "seed_scope_sidecars": seed_inventory,
        "all_sidecars": inventory,
    }

    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "g6_status": status,
        "analysis_scope": f"single_seed_{args.seed}",
        "seed": args.seed,
        "expected_sidecars_all_roots": args.expected_sidecars,
        "discovered_sidecars_all_roots": len(sidecars),
        "accepted_sidecars_all_roots": accepted_count,
        "rejected_sidecars_all_roots": len(inventory) - accepted_count,
        "seed_valid_sidecars_in_scope": sum(1 for row in seed_inventory if row.get("valid")),
        "seed_metric_rows": len(seed_rows),
        "methods_present": sorted({row["method"] for row in seed_rows}),
        "checkpoints_present": sorted(
            {row["checkpoint"] for row in seed_rows},
            key=lambda value: {"S0": 0, "S1": 1, "S2": 2, "S3": 3}.get(value, 99),
        ),
        "missing_method_checkpoint_pairs": [
            {"method": method, "checkpoint": checkpoint} for method, checkpoint in missing_pairs
        ],
        "shared_S0_included_once": sum(
            1 for row in seed_rows if row["method"] == "SHARED" and row["checkpoint"] == "S0"
        ) > 0,
        "independent_checkpoint_hashes": len({
            row["checkpoint_sha256"] for row in seed_rows if row["checkpoint_sha256"]
        }),
        "B4_B5_S1_alias_note": (
            "Matching prediction hashes are annotated as an alias; only matching checkpoint SHA-256 "
            "proves identical physical checkpoint content."
        ),
        "capabilities": list(CAPABILITIES),
        "support_vector": EXPECTED_SUPPORT,
        "correctness_policy": "status == valid",
        "confidence_interval": "Wilson 95%",
        "aggregation": "single-seed; no mean +/- SD across seeds",
        "rows": seed_rows,
    }

    write_csv(target_paths[0], seed_rows)
    target_paths[1].write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fields = sorted({key for row in inventory for key in row})
    with inventory_csv.open("x", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(inventory)
    if not gate_complete:
        target_paths[3].write_text(json.dumps(inventory_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        f"# Capability learning dynamics — seed {args.seed}",
        "",
        f"**G6 status: {status}.** Analysis is single-seed; no mean ± SD across seeds.",
        "",
        f"- Discovered sidecars across approved roots: {len(sidecars)} (expected {args.expected_sidecars})",
        f"- Valid sidecars across approved roots: {accepted_count}",
        f"- Metric rows in seed-{args.seed} scope (including shared S0): {len(seed_rows)}",
        "- Correctness: `status == valid`",
        "- Gold evaluation: 85 approved records; D_dev coverage: 500 IDs",
        "- Shared S0 baseline is included once.",
        "- B4/B5 S1 prediction alias is annotated; prediction equality is not proof of physical weight equality.",
        "",
        "## Required method/checkpoint matrix",
        "",
        "| Method | Checkpoint | Status |",
        "|---|---|---|",
    ]
    for method, checkpoint in sorted(
        required_pairs,
        key=lambda item: (item[0], {"S0": 0, "S1": 1, "S2": 2, "S3": 3}.get(item[1], 99)),
    ):
        state = "PRESENT" if (method, checkpoint) in available_pairs else "MISSING"
        lines.append(f"| {method} | {checkpoint} | {state} |")

    lines += [
        "",
        "## Capability metrics",
        "",
        "| Method | Checkpoint | Capability | Correct / Support | Mastery | Wilson 95% CI |",
        "|---|---|---|---:|---:|---:|",
    ]
    for row in seed_rows:
        lines.append(
            f"| {row['method']} | {row['checkpoint']} | {row['capability']} | "
            f"{row['n_correct']}/{row['n_support']} | {row['mastery']:.4f} | "
            f"[{row['ci95_low']:.4f}, {row['ci95_high']:.4f}] |"
        )
    lines += ["", "## Sidecar validation", ""]
    for record in seed_inventory:
        lines.append(
            f"- {record.get('method')} {record.get('checkpoint')}: "
            f"{'VALID' if record.get('valid') else 'REJECTED'} — {record.get('sidecar_source')}"
        )
    target_paths[2].write_text("\n".join(lines) + "\n", encoding="utf-8")

    if gate_complete:
        print("G6_BUILD_STATUS: PASS")
        print(f"G6_SEED{args.seed}_METRIC_ROWS: {len(seed_rows)}")
        print(f"G6_OUTPUT: {output}")
        return 0

    print("G6_BUILD_STATUS: PARTIAL")
    print(f"DISCOVERY_OK: {discovery_ok} ({len(sidecars)}/{args.expected_sidecars})")
    print(f"SIDECAR_VALIDATION_OK: {validation_ok} ({accepted_count}/{len(sidecars)})")
    print("MISSING_METHOD_CHECKPOINT_PAIRS:")
    for method, checkpoint in missing_pairs:
        print(f"  {method} {checkpoint}")
    print(f"G6_PARTIAL_OUTPUT: {output}")
    return 4

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"G6_FATAL: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
