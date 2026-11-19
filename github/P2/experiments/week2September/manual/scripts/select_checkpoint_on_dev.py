#!/usr/bin/env python3
"""Freeze seed-13 checkpoint selection using only the verified D_dev_select partition."""
from __future__ import annotations

import argparse
import csv
import io
import json
from datetime import datetime, timezone
from pathlib import Path

from p1p2_artifact_manager import publish_pair_no_overwrite
from p1p2_capability_state import validate_source_identity
from p1p2_controller import read_json, read_jsonl, sha256

VERSION = "p1p2.checkpoint-selection.v2"
SELECTION_POLICY = "strict status == valid on 415 D_dev_select IDs, earliest checkpoint breaks ties"
METHODS = ("B4", "B5", "P1-DEFICIT", "P1P2")
OUTPUT = Path("reports/p1p2_integration/final_validation")


def score(prediction: Path, ids: set[str]) -> dict[str, int | float]:
    rows = read_jsonl(prediction)
    by_id = {row["problem_id"]: row for row in rows}
    if len(by_id) != len(rows):
        raise ValueError(f"Duplicate problem_id in {prediction}")
    matched = ids & by_id.keys()
    correct = sum(by_id[identifier].get("status") == "valid" for identifier in matched)
    return {
        "correct": correct, "incorrect": len(matched) - correct,
        "missing": len(ids) - len(matched), "accuracy": correct / len(ids),
    }


def verified_prediction(root: Path, method: str, checkpoint: int) -> tuple[Path, dict]:
    label = f"S{checkpoint}"
    group = f"{method}_seed13"
    if checkpoint == 0:
        reference = root / "reports/p1p2_integration/source_review/s0_base_model_reference.json"
        prediction = root / "runs/main/S0/eval_dev.jsonl"
        if sha256(prediction) != read_json(reference)["evaluation_prediction_sha256"]:
            raise ValueError(f"Shared S0 prediction fingerprint mismatch: {prediction}")
        return prediction, {"checkpoint_id": "S0", "checkpoint_sha256": sha256(reference)}
    historical = method in ("B4", "B5")
    prediction = root / ("runs/main" if historical else "runs/p1p2_integration") / group / label / "eval_dev.jsonl"
    if historical:
        sidecar = root / "reports/capability/g5_9_historical_20261117" / f"{group}_{label}"
        if method == "B4" and not sidecar.exists():
            sidecar = root / "reports/capability_g4_validation" / f"{group}_{label}"
    else:
        sidecar = root / OUTPUT.parent / "capability_sidecars" / f"{group}_{label}"
    lineage_path = sidecar / "checkpoint_lineage.json"
    lineage = read_json(lineage_path)
    if (lineage.get("method"), lineage.get("seed"), lineage.get("round")) != (method, 13, checkpoint):
        raise ValueError(f"Checkpoint lineage identity mismatch: {sidecar}")
    manifest = read_json(sidecar / "student_capability_evaluation_manifest.json")
    if manifest["outputs"][lineage_path.name]["sha256"] != sha256(lineage_path):
        raise ValueError(f"Checkpoint lineage manifest fingerprint mismatch: {lineage_path}")
    expected = lineage["prediction_sha256"]
    fingerprint_path = sidecar / "input_fingerprint.json"
    fingerprint = read_json(fingerprint_path)
    validate_source_identity(manifest, lineage, fingerprint)
    recorded = fingerprint["inputs"]
    if (manifest["outputs"][fingerprint_path.name]["sha256"] != sha256(fingerprint_path)
            or recorded.get("dev_predictions") != expected):
        raise ValueError(f"Checkpoint lineage conflicts with evaluator inputs: {sidecar}")
    if method == "B4" and (not prediction.is_file() or sha256(prediction) != expected):
        # G4 evaluated a documented derived prediction, not the main-run file.
        prediction = root / OUTPUT.parent / "derived_predictions" / group / f"eval_student_ckpt_{checkpoint:03d}_dev_status.jsonl"
    if not prediction.is_file() or sha256(prediction) != expected:
        raise ValueError(f"Checkpoint lineage prediction mismatch: {prediction}")
    if not historical:
        adapter = root / "models/p1p2_integration" / group / f"student_ckpt_{checkpoint:03d}"
        if sha256(adapter) != lineage["checkpoint_sha256"]:
            raise ValueError(f"Checkpoint lineage adapter mismatch: {adapter}")
    return prediction, lineage


def choose_checkpoint(scores):
    return min(scores, key=lambda row: (-row["correct"], int(row["checkpoint"][1:])))["checkpoint"]


def selection_records(root: Path, *, partial=False):
    split_root = root / "splits/p1p2_vfinal_2026-11-16"
    manifest_path = split_root / "split_manifest.json"
    manifest = read_json(manifest_path)
    ids_path = split_root / "d_dev_select_ids.txt"
    ids = ids_path.read_text(encoding="utf-8-sig").split()
    ids_hash = sha256(ids_path)
    if len(ids) != 415 or len(set(ids)) != 415 or ids_hash != manifest["files"][ids_path.name]["sha256"]:
        raise ValueError(f"Invalid frozen D_dev_select IDs: {ids_path}")
    manifest_hash = sha256(manifest_path)
    dev_path = root / "splits/d_dev_ids.txt"
    dev = dev_path.read_text(encoding="utf-8-sig").split()
    if len(dev) != 500 or len(set(dev)) != 500 or not set(ids) <= set(dev):
        raise ValueError(f"D_dev_select is not a verified subset of D_dev: {dev_path}")
    allowed_status = {"valid", "invalid_format", "invalid_answer"}
    timestamp = datetime.now(timezone.utc).isoformat()
    rows, missing = [], []
    for method in METHODS:
        scores = []
        for checkpoint in range(4):
            label = f"S{checkpoint}"
            if partial and checkpoint == 0 and method != METHODS[0]:
                continue
            try:
                prediction, lineage = verified_prediction(root, method, checkpoint)
            except FileNotFoundError as exc:
                if not partial:
                    raise
                missing.append({"method": method, "checkpoint": label, "reason": str(exc)})
                continue
            predictions = read_jsonl(prediction)
            if (len(predictions) != len(dev) or {row["problem_id"] for row in predictions} != set(dev)
                    or not all(row["status"] in allowed_status for row in predictions)):
                raise ValueError(f"Missing, duplicate or invalid-status D_dev prediction: {prediction}")
            counts = score(prediction, set(ids))
            if counts["missing"]:
                raise ValueError(f"D_dev_select coverage incomplete: {prediction}")
            scores.append({
                "method": "SHARED" if partial and checkpoint == 0 else method, "seed": 13, "checkpoint": label,
                "status": "PARTIAL" if partial else "FINAL", "denominator": len(ids), **counts,
                "prediction_path": str(prediction),
                "prediction_sha256": sha256(prediction), "checkpoint_lineage": lineage,
                "split_manifest_sha256": manifest_hash, "split_ids_sha256": ids_hash,
                "script_version": VERSION, "timestamp_utc": timestamp,
            })
        best = None if partial else choose_checkpoint(scores)
        for row in scores:
            row["selected_checkpoint"] = best
            row["tie_break"] = "earliest checkpoint"
        rows.extend(scores)

    return rows, missing


def select(root: Path, *, partial=False, output: Path | None = None) -> tuple[Path, Path]:
    rows, missing = selection_records(root, partial=partial)
    csv_content = io.StringIO(newline="")
    writer = csv.DictWriter(csv_content, fieldnames=list(rows[0]))
    writer.writeheader()
    for row in rows:
        writer.writerow({**row, "checkpoint_lineage": json.dumps(row["checkpoint_lineage"], sort_keys=True)})
    out = output or root / OUTPUT
    stem = "checkpoint_selection_seed13_partial" if partial else "checkpoint_selection_seed13"
    return publish_pair_no_overwrite(
        out / f"{stem}.csv", csv_content.getvalue().encode("utf-8"),
        out / f"{stem}.json",
        (json.dumps({"schema_version": VERSION, "status": "PARTIAL" if partial else "FINAL",
                     "policy": SELECTION_POLICY,
                     "missing_checkpoints": missing, "rows": rows}, indent=2) + "\n").encode("utf-8"),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manual-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--partial", action="store_true", help="Report available checkpoint scores without freezing any winner")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    for output in select(args.manual_root.resolve(), partial=args.partial, output=args.output):
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
