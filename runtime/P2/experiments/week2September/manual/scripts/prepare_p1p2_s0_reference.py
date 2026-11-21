#!/usr/bin/env python3
"""Create an immutable, transparent S0 base-model reference descriptor."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

MODEL_ID = "Qwen/Qwen2.5-1.5B-Instruct"
MODEL_REVISION = "989aa7980e4cf806f80c7fef2b1adb7bc71aa306"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        default=str(Path(__file__).resolve().parents[1]),
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()

    prediction = root / "runs/main/S0/eval_dev.jsonl"
    summary_path = root / "runs/main/S0/eval_dev.summary.json"
    marker_path = root / "runs/main/S0/.done/eval_dev_S0.json"

    for path in (prediction, summary_path, marker_path):
        if not path.is_file():
            raise FileNotFoundError(f"Missing S0 source: {path}")

    summary = read_json(summary_path)
    marker = read_json(marker_path)

    if summary.get("checkpoint") != "S0":
        raise ValueError("S0 summary checkpoint field mismatch")
    if summary.get("split") != "dev":
        raise ValueError("S0 summary split field mismatch")
    if summary.get("model") != MODEL_ID:
        raise ValueError("S0 model ID mismatch")
    if summary.get("revision") != MODEL_REVISION:
        raise ValueError("S0 model revision mismatch")
    if summary.get("adapter") is not None:
        raise ValueError("S0 must be a base model with adapter=null")
    if summary.get("n_problems") != 500:
        raise ValueError("S0 summary must report 500 problems")

    command = str(marker.get("command", ""))
    if (
        "eval_student.py" not in command
        or "--tag S0" not in command
        or "--split dev" not in command
    ):
        raise ValueError("S0 marker command is not the expected evaluation")

    prediction_ids = []
    with prediction.open("r", encoding="utf-8-sig") as stream:
        for line_no, line in enumerate(stream, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            problem_id = str(row.get("problem_id", "")).strip()
            if not problem_id:
                raise ValueError(
                    f"Empty problem_id in S0 prediction line {line_no}"
                )
            prediction_ids.append(problem_id)

    if len(prediction_ids) != 500:
        raise ValueError(
            f"Expected 500 S0 predictions, got {len(prediction_ids)}"
        )
    if len(set(prediction_ids)) != 500:
        raise ValueError("S0 prediction IDs are not unique")

    descriptor = {
        "schema": "p1p2.base_model_reference.v1",
        "reference_type": "immutable_huggingface_model_revision",
        "model_id": MODEL_ID,
        "revision": MODEL_REVISION,
        "adapter": None,
        "physical_weights_included": False,
        "note": (
            "Identity/provenance descriptor for the shared S0 base model. "
            "This file is not a physical model checkpoint or weights archive."
        ),
        "evaluation_marker_sha256": sha256_file(marker_path),
        "evaluation_summary_sha256": sha256_file(summary_path),
        "evaluation_prediction_sha256": sha256_file(prediction),
        "prediction_records": len(prediction_ids),
        "prediction_unique_ids": len(set(prediction_ids)),
    }

    output = (
        root
        / "reports/p1p2_integration/source_review/"
        / "s0_base_model_reference.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)

    content = (
        json.dumps(descriptor, ensure_ascii=False, indent=2) + "\n"
    ).encode("utf-8")

    if output.exists():
        if output.read_bytes() != content:
            raise FileExistsError(
                "Existing S0 descriptor differs; refusing overwrite: "
                + str(output)
            )
        print("S0_REFERENCE=EXACT_REUSE")
    else:
        output.write_bytes(content)
        print("S0_REFERENCE=CREATED")

    print(f"S0_PREDICTION_SHA256={sha256_file(prediction)}")
    print(f"S0_REFERENCE_SHA256={sha256_file(output)}")
    print(f"S0_REFERENCE_PATH={output}")
    print("PHYSICAL_WEIGHTS_INCLUDED=False")
    print("S0_REFERENCE_VALIDATION=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
