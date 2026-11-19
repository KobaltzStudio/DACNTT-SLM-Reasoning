#!/usr/bin/env python3
"""Build an immutable P1 capability state from a validated sidecar."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CAPABILITIES = (
    "addition",
    "subtraction",
    "multiplication",
    "division",
    "percentage",
    "fraction",
    "ratio",
)

EXPECTED_SUPPORT = {
    "addition": 30,
    "subtraction": 51,
    "multiplication": 73,
    "division": 47,
    "percentage": 29,
    "fraction": 31,
    "ratio": 30,
}

SOURCE_METHODS = {
    "B2", "B3", "B4", "B5", "P1-DEFICIT", "P1P2"
}

EXPECTED_OUTPUT_NAMES = {
    "capability_metrics.csv",
    "capability_metrics.jsonl",
    "prediction_coverage_report.json",
    "checkpoint_lineage.json",
    "input_fingerprint.json",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def stable_state(value: dict[str, Any]) -> dict[str, Any]:
    return {
        key: item
        for key, item in value.items()
        if key != "created_at_utc"
    }


def require_equal(label: str, left: Any, right: Any) -> None:
    if left != right:
        raise ValueError(
            f"PROVENANCE_MISMATCH {label}: "
            f"manifest={left!r}, lineage={right!r}"
        )


def validate_source_identity(
    manifest: dict[str, Any],
    lineage: dict[str, Any],
    fingerprint: dict[str, Any],
) -> tuple[int, str, int, str]:
    required_fields = (
        "run_id", "method", "seed", "round",
        "checkpoint_id", "checkpoint_sha256",
    )

    for field in required_fields:
        if field not in lineage:
            raise ValueError(f"Missing lineage field: {field}")

    for field in ("run_id", "method", "seed", "round"):
        if field not in manifest:
            raise ValueError(f"Missing manifest field: {field}")

    for field in ("run_id", "method", "seed", "round"):
        require_equal(field, manifest[field], lineage[field])

    source_round = int(lineage["round"])
    source_method = str(lineage["method"])
    source_seed = int(lineage["seed"])
    run_id = str(lineage["run_id"])

    if source_round not in (0, 1, 2, 3):
        raise ValueError(f"Invalid source round: {source_round}")

    if source_round == 0:
        if source_method != "SHARED" or source_seed != 0:
            raise ValueError("S0 must originate from SHARED seed 0")
        expected_run_id = "SHARED_seed0_S0"
    else:
        if source_method not in SOURCE_METHODS:
            raise ValueError(f"Unsupported source method: {source_method}")
        expected_run_id = (
            f"{source_method}_seed{source_seed}_S{source_round}"
        )

    if run_id != expected_run_id:
        raise ValueError(
            f"RUN_ID_MISMATCH: {run_id!r} != {expected_run_id!r}"
        )

    expected_checkpoint = f"S{source_round}"
    if manifest.get("checkpoint") != expected_checkpoint:
        raise ValueError(
            "Manifest checkpoint does not match source round: "
            f"{manifest.get('checkpoint')!r} != {expected_checkpoint!r}"
        )

    checkpoint_id = str(lineage["checkpoint_id"]).strip()
    checkpoint_sha256 = str(lineage["checkpoint_sha256"]).lower()

    if not checkpoint_id:
        raise ValueError("Empty checkpoint_id")

    if len(checkpoint_sha256) != 64:
        raise ValueError("Invalid checkpoint_sha256 length")

    if any(ch not in "0123456789abcdef" for ch in checkpoint_sha256):
        raise ValueError("Invalid checkpoint_sha256 characters")

    manifest_inputs = manifest.get("input_hashes")
    fingerprint_inputs = fingerprint.get("inputs")

    if not isinstance(manifest_inputs, dict):
        raise ValueError("Manifest input_hashes must be an object")

    if not isinstance(fingerprint_inputs, dict):
        raise ValueError("Fingerprint inputs must be an object")

    if manifest_inputs != fingerprint_inputs:
        raise ValueError(
            "Manifest input_hashes do not match fingerprint inputs"
        )

    if fingerprint_inputs.get("checkpoint") != checkpoint_sha256:
        raise ValueError(
            "Checkpoint hash in lineage does not match input fingerprint"
        )

    expected_fingerprint = hashlib.sha256(
        json.dumps(
            fingerprint_inputs,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()

    if fingerprint.get("fingerprint") != expected_fingerprint:
        raise ValueError("Input fingerprint digest is invalid")

    return source_round, source_method, source_seed, run_id


def validate_metrics(metrics_path: Path) -> dict[str, dict[str, Any]]:
    by_capability: dict[str, dict[str, Any]] = {}

    with metrics_path.open("r", encoding="utf-8-sig") as stream:
        for line_no, line in enumerate(stream, 1):
            if not line.strip():
                continue

            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError(f"Invalid metric row at line {line_no}")

            capability = row.get("capability")
            if capability not in CAPABILITIES:
                raise ValueError(f"Unknown capability: {capability!r}")

            if capability in by_capability:
                raise ValueError(f"Duplicate capability row: {capability}")

            if row.get("strict_metric") != "status_equals_valid":
                raise ValueError("Capability row does not use strict metric")

            if row.get("gold_policy") != "approved_85_primary":
                raise ValueError("Capability row uses an invalid Gold policy")

            support = int(row["n_support"])
            correct = int(row["n_correct"])
            incorrect = int(row["n_incorrect"])

            if support != EXPECTED_SUPPORT[capability]:
                raise ValueError(
                    f"Support mismatch for {capability}: "
                    f"{support} != {EXPECTED_SUPPORT[capability]}"
                )

            if correct < 0 or incorrect < 0:
                raise ValueError(f"Negative metric count: {capability}")

            if correct + incorrect != support:
                raise ValueError(f"Count mismatch: {capability}")

            mastery = correct / support
            deficit = 1.0 - mastery

            if not math.isfinite(float(row["mastery"])):
                raise ValueError(f"Non-finite mastery: {capability}")

            if not math.isfinite(float(row["deficit"])):
                raise ValueError(f"Non-finite deficit: {capability}")

            if abs(float(row["mastery"]) - mastery) > 1e-12:
                raise ValueError(f"Mastery mismatch: {capability}")

            if abs(float(row["deficit"]) - deficit) > 1e-12:
                raise ValueError(f"Deficit mismatch: {capability}")

            by_capability[capability] = {
                "n_support": support,
                "n_correct": correct,
                "n_incorrect": incorrect,
                "mastery": mastery,
                "deficit": deficit,
                "ci95_low": row.get("ci95_low"),
                "ci95_high": row.get("ci95_high"),
            }

    if set(by_capability) != set(CAPABILITIES):
        raise ValueError(
            "Capability coverage is incomplete: "
            f"{sorted(by_capability)}"
        )

    return by_capability


def publish_exclusive(output: Path, content: bytes) -> None:
    """Publish through a same-directory hard link; never replace a target."""
    output.parent.mkdir(parents=True, exist_ok=True)

    fd, temp_name = tempfile.mkstemp(
        prefix=f".{output.name}.staging.",
        suffix=".tmp",
        dir=str(output.parent),
    )
    temp_path = Path(temp_name)

    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())

        try:
            os.link(temp_path, output)
        except FileExistsError:
            raise
        except OSError as exc:
            raise RuntimeError(
                "ATOMIC_NO_OVERWRITE_UNAVAILABLE: hard-link publication "
                f"failed; temporary file preserved at {temp_path}: {exc}"
            ) from exc

        temp_path.unlink(missing_ok=True)

    except Exception:
        if temp_path.exists():
            print(f"RECOVERY_TEMP_PRESERVED={temp_path}")
        raise


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create immutable capability state from a sidecar"
    )
    parser.add_argument("--sidecar-dir", required=True)
    parser.add_argument(
        "--target-method",
        required=True,
        choices=["P1-DEFICIT", "P1P2"],
    )
    parser.add_argument("--target-seed", required=True, type=int)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    state = build_state(Path(args.sidecar_dir).resolve(), args.target_method, args.target_seed)
    return write_state(state, Path(args.out).resolve())


def build_state(sidecar: Path, target_method: str, target_seed: int) -> dict[str, Any]:
    """Validate the sidecar and derive state without writing any artifacts."""

    required = {
        "metrics": sidecar / "capability_metrics.jsonl",
        "coverage": sidecar / "prediction_coverage_report.json",
        "lineage": sidecar / "checkpoint_lineage.json",
        "fingerprint": sidecar / "input_fingerprint.json",
        "manifest": sidecar / "student_capability_evaluation_manifest.json",
    }

    for label, path in required.items():
        if not path.is_file():
            raise FileNotFoundError(f"Missing sidecar {label}: {path}")

    manifest = read_json(required["manifest"])
    coverage = read_json(required["coverage"])
    lineage = read_json(required["lineage"])
    fingerprint = read_json(required["fingerprint"])

    if manifest.get("schema_version") != "p1p2.capability-manifest.v1":
        raise ValueError("Unexpected capability sidecar schema")

    if manifest.get("gold_policy") != "approved_85_primary":
        raise ValueError("Sidecar does not use approved 85 Gold policy")

    if manifest.get("strict_metric") != "status == valid":
        raise ValueError("Sidecar does not use strict status==valid metric")

    if coverage.get("status") != "PASS":
        raise ValueError("Prediction coverage report is not PASS")

    if coverage.get("split") != "D_dev":
        raise ValueError("Capability evaluation must use D_dev")

    if coverage.get("prediction_records") != 500:
        raise ValueError("Expected exactly 500 D_dev prediction records")

    if coverage.get("prediction_unique_ids") != 500:
        raise ValueError("Expected 500 unique D_dev prediction IDs")

    if coverage.get("gold_records") != 85:
        raise ValueError("Expected exactly 85 approved Gold records")

    if coverage.get("gold_unique_ids") != 85:
        raise ValueError("Expected 85 unique approved Gold IDs")

    if coverage.get("gold_matched_prediction_ids") != 85:
        raise ValueError("Not all approved Gold IDs have predictions")

    if coverage.get("lenient_correct_excluded") is not True:
        raise ValueError("lenient_correct must be excluded")

    output_metadata = manifest.get("outputs", {})
    if set(output_metadata) != EXPECTED_OUTPUT_NAMES:
        raise ValueError(
            "Sidecar manifest output inventory mismatch: "
            f"{sorted(output_metadata)}"
        )

    for name, metadata in output_metadata.items():
        output_path = sidecar / name

        if not output_path.is_file():
            raise FileNotFoundError(
                f"Manifest output is missing: {output_path}"
            )

        if sha256_file(output_path) != metadata.get("sha256"):
            raise ValueError(f"Sidecar output hash mismatch: {name}")

        if output_path.stat().st_size != metadata.get("size_bytes"):
            raise ValueError(f"Sidecar output size mismatch: {name}")

    source_round, source_method, source_seed, source_run_id = (
        validate_source_identity(manifest, lineage, fingerprint)
    )

    by_capability = validate_metrics(required["metrics"])

    if target_seed < 0:
        raise ValueError("target-seed must be non-negative")

    return {
        "schema_version": "p1p2.capability-state.v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "target": {
            "method": target_method,
            "seed": target_seed,
            "selection_round": source_round + 1,
        },
        "source": {
            "run_id": source_run_id,
            "method": source_method,
            "seed": source_seed,
            "round": source_round,
            "checkpoint": manifest["checkpoint"],
            "checkpoint_id": lineage["checkpoint_id"],
            "checkpoint_sha256": lineage["checkpoint_sha256"],
            "sidecar_manifest_sha256": sha256_file(required["manifest"]),
            "input_fingerprint": fingerprint["fingerprint"],
        },
        "metric_policy": {
            "correctness": "status == valid",
            "gold_policy": "approved_85_primary",
            "lenient_correct_used": False,
            "mastery": "n_correct / n_support",
            "deficit": "1 - mastery",
        },
        "capabilities": by_capability,
    }


def write_state(state: dict[str, Any], output: Path) -> int:
    content = (
        json.dumps(state, ensure_ascii=False, indent=2) + "\n"
    ).encode("utf-8")

    output.parent.mkdir(parents=True, exist_ok=True)

    if output.exists():
        existing = read_json(output)

        if stable_state(existing) != stable_state(state):
            raise FileExistsError(
                "Existing capability state has different provenance or "
                f"metrics; refusing overwrite: {output}"
            )

        print("CAPABILITY_STATE=EXACT_REUSE")

    if not output.exists():
        try:
            publish_exclusive(output, content)
            print("CAPABILITY_STATE=CREATED")
        except FileExistsError:
            existing = read_json(output)

            if stable_state(existing) != stable_state(state):
                raise FileExistsError(
                    "Concurrent state publication produced a different "
                    f"state; refusing overwrite: {output}"
                )

            print("CAPABILITY_STATE=EXACT_REUSE")

    source, target = state["source"], state["target"]
    print(f"SOURCE_RUN_ID={source['run_id']}")
    print(f"SOURCE_METHOD={source['method']}")
    print(f"SOURCE_SEED={source['seed']}")
    print(f"SOURCE_ROUND={source['round']}")
    print(f"TARGET_METHOD={target['method']}")
    print(f"TARGET_SEED={target['seed']}")
    print(f"SELECTION_ROUND={target['selection_round']}")
    print(f"CAPABILITY_COUNT={len(state['capabilities'])}")
    print(f"STATE_SHA256={sha256_file(output)}")
    print(f"STATE_PATH={output}")
    print("CAPABILITY_STATE_VALIDATION=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
