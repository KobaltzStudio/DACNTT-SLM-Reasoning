from __future__ import annotations

import csv
import hashlib
import json
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

EXPECTED_SUPPORT = {
    "addition": 30,
    "subtraction": 51,
    "multiplication": 73,
    "division": 47,
    "fraction": 31,
    "percentage": 29,
    "ratio": 30,
}

VALID_STATUSES = {
    "valid",
    "invalid_answer",
    "invalid_format",
}

MODEL_ID = "Qwen/Qwen2.5-1.5B-Instruct"
MODEL_REVISION = "989aa7980e4cf806f80c7fef2b1adb7bc71aa306"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(
        path.read_text(encoding="utf-8-sig")
    )

    if not isinstance(value, dict):
        raise ValueError(
            f"Expected JSON object: {path}"
        )

    return value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    with path.open(
        "r",
        encoding="utf-8-sig",
    ) as stream:

        for line_no, line in enumerate(stream, 1):
            if not line.strip():
                continue

            row = json.loads(line)

            if not isinstance(row, dict):
                raise ValueError(
                    f"Expected JSON object at {path}:{line_no}"
                )

            rows.append(row)

    return rows


def require_file(path: Path, label: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(
            f"Missing {label}: {path}"
        )


def main() -> int:
    paths = {
        "capability_eval":
            ROOT / "scripts" / "capability_eval.py",

        "test_capability_eval":
            ROOT / "scripts" / "test_capability_eval.py",

        "prediction":
            ROOT / "runs" / "main" / "S0" / "eval_dev.jsonl",

        "summary":
            ROOT / "runs" / "main" / "S0" / "eval_dev.summary.json",

        "marker":
            ROOT / "runs" / "main" / "S0" / ".done" / "eval_dev_S0.json",

        "gold_manifest":
            ROOT / "data" / "gold_vfinal" / "gold_vfinal_manifest.json",

        "gold_labels":
            ROOT / "data" / "gold_vfinal" / "supplement_annotations_vfinal.jsonl",

        "approval":
            ROOT / "reports" / "capability" /
            "p1_day14_final_2026-11-14" / "approved" /
            "gold_supplement_85_approved_review.csv",

        "dev_ids":
            ROOT / "splits" / "d_dev_ids.txt",

        "config":
            ROOT / "config" / "experiment_config.json",
    }

    print("=== G5.9 S0 INPUT PREFLIGHT ===")

    for name, path in paths.items():
        require_file(path, name)
        print(f"FOUND: {name}: {path}")

    # ---------------------------------------------------------
    # 1. Validate frozen Gold manifest.
    # ---------------------------------------------------------

    manifest = read_json(paths["gold_manifest"])

    if manifest.get("gold_version") != "vFinal":
        raise ValueError(
            "Gold manifest is not vFinal"
        )

    if manifest.get("supplement_count") != 85:
        raise ValueError(
            "Gold manifest supplement_count must equal 85"
        )

    # ---------------------------------------------------------
    # 2. Validate D_dev.
    # ---------------------------------------------------------

    dev_ids_list = [
        line.strip()
        for line in paths["dev_ids"]
        .read_text(encoding="utf-8-sig")
        .splitlines()
        if line.strip()
    ]

    dev_ids = set(dev_ids_list)

    if len(dev_ids_list) != 500 or len(dev_ids) != 500:
        raise ValueError(
            "D_dev must contain exactly 500 unique IDs: "
            f"rows={len(dev_ids_list)}, unique={len(dev_ids)}"
        )

    # ---------------------------------------------------------
    # 3. Validate approved Gold labels.
    # ---------------------------------------------------------

    gold_rows = read_jsonl(paths["gold_labels"])

    gold_ids = [
        str(row.get("problem_id", "")).strip()
        for row in gold_rows
    ]

    if (
        len(gold_rows) != 85
        or len(set(gold_ids)) != 85
        or not set(gold_ids).issubset(dev_ids)
    ):
        raise ValueError(
            "Gold labels must contain 85 unique IDs "
            "inside D_dev"
        )

    support = Counter(
        capability
        for row in gold_rows
        for capability in row.get("capabilities_manual", [])
    )

    if dict(support) != EXPECTED_SUPPORT:
        raise ValueError(
            f"Gold capability support mismatch: {dict(support)}"
        )

    # ---------------------------------------------------------
    # 4. Validate human approval.
    # ---------------------------------------------------------

    with paths["approval"].open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as stream:
        approval_rows = list(csv.DictReader(stream))

    required_columns = {
        "problem_id",
        "review_status",
        "human_approval",
    }

    if (
        not approval_rows
        or not required_columns.issubset(
            set(approval_rows[0])
        )
    ):
        raise ValueError(
            "Approval CSV is missing required columns"
        )

    approval_ids = [
        str(row.get("problem_id", "")).strip()
        for row in approval_rows
    ]

    if (
        len(approval_rows) != 85
        or len(set(approval_ids)) != 85
        or set(approval_ids) != set(gold_ids)
    ):
        raise ValueError(
            "Approval IDs do not exactly match Gold IDs"
        )

    approved_statuses = {
        "APPROVED_NO_LABEL_CHANGE",
        "APPROVED_WITH_SOURCE_CLARIFICATION",
    }

    for row in approval_rows:
        if (
            row.get("review_status", "").strip()
            not in approved_statuses
        ):
            raise ValueError(
                f"Unapproved Gold row: {row.get('problem_id')}"
            )

        if not row.get(
            "human_approval", ""
        ).strip().startswith("APPROVED_BY_USER_"):
            raise ValueError(
                "Missing explicit human approval: "
                f"{row.get('problem_id')}"
            )

    # ---------------------------------------------------------
    # 5. Validate S0 prediction coverage and strict status.
    # ---------------------------------------------------------

    predictions = read_jsonl(paths["prediction"])

    prediction_ids = [
        str(row.get("problem_id", "")).strip()
        for row in predictions
    ]

    if (
        len(predictions) != 500
        or len(set(prediction_ids)) != 500
        or set(prediction_ids) != dev_ids
    ):
        raise ValueError(
            "S0 prediction must have exactly 500 "
            "unique D_dev IDs"
        )

    status_counts = Counter(
        str(row.get("status", ""))
        for row in predictions
    )

    unknown = set(status_counts) - VALID_STATUSES

    if unknown:
        raise ValueError(
            f"Unknown prediction statuses: {sorted(unknown)}"
        )

    # ---------------------------------------------------------
    # 6. Validate S0 evaluation metadata.
    # ---------------------------------------------------------

    summary = read_json(paths["summary"])

    if (
        summary.get("checkpoint") != "S0"
        or summary.get("split") != "dev"
    ):
        raise ValueError(
            "S0 summary does not identify S0 / dev"
        )

    if (
        summary.get("model") != MODEL_ID
        or summary.get("revision") != MODEL_REVISION
    ):
        raise ValueError(
            "S0 model/revision differs from expected base model"
        )

    if (
        summary.get("adapter") is not None
        or summary.get("n_problems") != 500
    ):
        raise ValueError(
            "S0 summary must describe 500-row base-model "
            "evaluation with adapter=null"
        )

    marker = read_json(paths["marker"])
    evaluation_command = str(marker.get("command", ""))

    if (
        "eval_student.py" not in evaluation_command
        or "--tag S0" not in evaluation_command
        or "--split dev" not in evaluation_command
    ):
        raise ValueError(
            "S0 marker does not contain the expected "
            "evaluation command"
        )

    print("S0_PREDICTION_COVERAGE=PASS")
    print("GOLD_85_AND_APPROVAL=PASS")
    print("D_DEV_SPLIT=PASS")
    print("S0_MODEL_REVISION=PASS")

    # ---------------------------------------------------------
    # 7. Run the existing capability evaluator unit tests.
    #    Redirect temporary files into the P2 repository.
    # ---------------------------------------------------------

    test_temp_root = (
        ROOT / "reports" / "p1p2_integration" /
        "source_review" / "g59_s0_test_temp"
    )

    test_temp_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    test_env = os.environ.copy()
    test_env["TEMP"] = str(test_temp_root)
    test_env["TMP"] = str(test_temp_root)
    test_env["TMPDIR"] = str(test_temp_root)

    test_result = subprocess.run(
        [
            sys.executable,
            str(paths["test_capability_eval"]),
        ],
        cwd=ROOT,
        env=test_env,
        text=True,
        capture_output=True,
    )

    if test_result.stdout:
        print(test_result.stdout, end="")

    if test_result.stderr:
        print(
            test_result.stderr,
            file=sys.stderr,
            end="",
        )

    if test_result.returncode != 0:
        raise RuntimeError(
            "capability_eval unit tests failed: "
            f"exit_code={test_result.returncode}"
        )

    print("CAPABILITY_EVAL_UNIT_TESTS=PASS")

    # ---------------------------------------------------------
    # 8. Create a transparent S0 base-model reference.
    #    This is NOT a physical model weights archive.
    # ---------------------------------------------------------

    descriptor = {
        "schema": "p1p2.base_model_reference.v1",
        "reference_type": "immutable_huggingface_model_revision",
        "model_id": MODEL_ID,
        "revision": MODEL_REVISION,
        "adapter": None,
        "physical_weights_included": False,
        "note": (
            "Provenance reference for the S0 base model. "
            "This file is not a copy or hash of model weights."
        ),
        "evaluation_marker_sha256":
            sha256_file(paths["marker"]),
        "evaluation_summary_sha256":
            sha256_file(paths["summary"]),
        "evaluation_prediction_sha256":
            sha256_file(paths["prediction"]),
    }

    reference_path = (
        ROOT / "reports" / "p1p2_integration" /
        "source_review" / "s0_base_model_reference.json"
    )

    reference_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    descriptor_bytes = (
        json.dumps(
            descriptor,
            ensure_ascii=False,
            indent=2,
        ) + "\n"
    ).encode("utf-8")

    if reference_path.exists():
        if reference_path.read_bytes() != descriptor_bytes:
            raise FileExistsError(
                "Existing S0 reference differs. "
                f"Refusing overwrite: {reference_path}"
            )
    else:
        reference_path.write_bytes(descriptor_bytes)

    # ---------------------------------------------------------
    # 9. Run the real-data S0 capability sidecar.
    # ---------------------------------------------------------

    out_root = (
        ROOT / "reports" / "capability" /
        "g5_9_real_data_s0"
    )

    command_args = [
        sys.executable,
        str(paths["capability_eval"]),
        "--run-id", "SHARED_seed0_S0",
        "--method", "SHARED",
        "--seed", "0",
        "--round", "0",
        "--checkpoint", str(reference_path),
        "--dev-predictions", str(paths["prediction"]),
        "--gold-manifest", str(paths["gold_manifest"]),
        "--gold-labels", str(paths["gold_labels"]),
        "--approval-csv", str(paths["approval"]),
        "--dev-ids", str(paths["dev_ids"]),
        "--config", str(paths["config"]),
        "--shared-checkpoint-group",
        f"{MODEL_ID}@{MODEL_REVISION}",
        "--out-root", str(out_root),
    ]

    result = subprocess.run(
        command_args,
        cwd=ROOT,
        text=True,
        capture_output=True,
    )

    if result.stdout:
        print(result.stdout, end="")

    if result.stderr:
        print(
            result.stderr,
            file=sys.stderr,
            end="",
        )

    if result.returncode != 0:
        raise RuntimeError(
            "capability_eval.py failed: "
            f"exit_code={result.returncode}"
        )

    # ---------------------------------------------------------
    # 10. Validate the published sidecar.
    # ---------------------------------------------------------

    sidecar = out_root / "SHARED_seed0_S0"

    required_outputs = [
        "capability_metrics.csv",
        "capability_metrics.jsonl",
        "prediction_coverage_report.json",
        "checkpoint_lineage.json",
        "input_fingerprint.json",
        "student_capability_evaluation_manifest.json",
    ]

    for name in required_outputs:
        require_file(
            sidecar / name,
            f"sidecar output {name}",
        )

    coverage = read_json(
        sidecar / "prediction_coverage_report.json"
    )

    if (
        coverage.get("status") != "PASS"
        or coverage.get("prediction_records") != 500
        or coverage.get("prediction_unique_ids") != 500
    ):
        raise ValueError(
            "Published S0 sidecar coverage report failed"
        )

    output_manifest = read_json(
        sidecar / "student_capability_evaluation_manifest.json"
    )

    if output_manifest.get("run_id") != "SHARED_seed0_S0":
        raise ValueError(
            "Published sidecar manifest has unexpected run_id"
        )

    output_hashes = output_manifest.get("outputs", {})

    for name in required_outputs:
        if name == "student_capability_evaluation_manifest.json":
            continue

        metadata = output_hashes.get(name)

        if (
            not isinstance(metadata, dict)
            or metadata.get("sha256")
            != sha256_file(sidecar / name)
        ):
            raise ValueError(
                f"Sidecar output hash mismatch: {name}"
            )

    with (
        sidecar / "capability_metrics.csv"
    ).open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as stream:
        metric_rows = list(csv.DictReader(stream))

    if len(metric_rows) != 7:
        raise ValueError(
            "Expected 7 capability metric rows; "
            f"found {len(metric_rows)}"
        )

    for row in metric_rows:
        if row.get("strict_metric") != "status_equals_valid":
            raise ValueError(
                "Capability metric does not use strict status==valid"
            )

        expected = EXPECTED_SUPPORT.get(
            row.get("capability"),
            -2,
        )

        if int(row.get("n_support", -1)) != expected:
            raise ValueError(
                f"Capability support mismatch: {row}"
            )

    print(
        "S0_STATUS_COUNTS="
        + json.dumps(
            dict(status_counts),
            sort_keys=True,
        )
    )

    print(
        "S0_PREDICTION_SHA256="
        + sha256_file(paths["prediction"])
    )

    print(
        "S0_REFERENCE_SHA256="
        + sha256_file(reference_path)
    )

    print("S0_SIDECAR=" + str(sidecar))
    print("G5_9_S0_REAL_DATA_SIDECAR=PASS")

    print(
        "SCOPE_NOTE=PASS applies to shared S0 baseline only; "
        "historical B4 seed13 S1-S3 provenance remains unresolved."
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
