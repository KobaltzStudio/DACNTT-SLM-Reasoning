#!/usr/bin/env python3
"""Audit D_test input metadata or run the separately approved, G7-gated final test."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path

from capability_eval import publish_staged_directory
from p1p2_artifact_manager import sha256_file, sha256_json
from p1p2_controller import read_json, read_jsonl, sha256
from p1p2_paths import artifact_path
from select_checkpoint_on_dev import SELECTION_POLICY, VERSION, selection_records

ROOT = Path(__file__).resolve().parents[1]
METHODS = ("P1-DEFICIT", "P1P2")
SCHEMA = "p1p2.final-d-test.v1"
EVALUATOR_FILES = (
    "scripts/run_final_d_test.py", "scripts/eval_student.py", "scripts/eval_metrics.py",
    "scripts/answer_utils.py", "scripts/student_common.py",
    "scripts/generate_teacher_trajectories_batch.py", "scripts/select_checkpoint_on_dev.py",
    "config/experiment_config.json",
)


def verified_text(path: Path, expected: str) -> str:
    """Accept only the frozen bytes or their exact Windows CRLF checkout representation."""
    raw = path.read_bytes()
    for digest in (hashlib.sha256(raw).hexdigest(),
                   hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest()):
        if digest == expected:
            return hashlib.sha256(raw).hexdigest()
    raise ValueError(f"Frozen split fingerprint mismatch: {path}")


def audit_split(root: Path) -> tuple[set[str], dict[str, str]]:
    cfg = read_json(root / "config/experiment_config.json")
    original = root / "splits/split_manifest.json"
    release = root / "splits/p1p2_vfinal_2026-11-16/split_manifest.json"
    release_data = read_json(release)
    if cfg["splits"]["manifest"] != "splits/split_manifest.json":
        raise ValueError("Unexpected source split manifest locator")
    raw_manifest = verified_text(original, cfg["splits"]["manifest_sha256"])
    if release_data["source_split_manifest"] != {"path": "splits/split_manifest.json", "sha256": raw_manifest}:
        raise ValueError("P1/P2 release does not bind the original split manifest bytes")
    split = read_json(original)
    hashes = {"split_manifest": raw_manifest, "p1p2_split_manifest": sha256_file(release)}
    partitions = {}
    for key in ("d_test", "d_dev", "d_pool"):
        meta = split["files"][key]
        relative = f"splits/{key}_ids.txt"
        if meta["path"] != relative:
            raise ValueError(f"Unexpected split locator: {key}")
        path = root / relative
        hashes[key + "_ids"] = verified_text(path, meta["sha256"])
        ids = path.read_text(encoding="utf-8-sig").split()
        if len(set(ids)) != len(ids) or len(ids) != split["counts"][key]:
            raise ValueError(f"Invalid split ID coverage: {key}")
        partitions[key] = set(ids)
    ids = partitions["d_test"]
    if len(ids) != 1319 or release_data["counts"]["d_test"] != len(ids) or ids & (
            partitions["d_dev"] | partitions["d_pool"]):
        raise ValueError("Invalid D_test cardinality or overlap")
    meta = split["sources"]["gsm8k_test"]
    if meta["path"] != "data/raw/gsm8k_test.jsonl":
        raise ValueError("Unexpected GSM8K test locator")
    raw = root / meta["path"]
    hashes["gsm8k_test"] = verified_text(raw, meta["sha256"])
    with raw.open(encoding="utf-8-sig") as stream:
        source_ids = [json.loads(line)["problem_id"] for line in stream if line.strip()]
    if len(source_ids) != len(ids) or set(source_ids) != ids:
        raise ValueError("GSM8K source and D_test IDs differ")
    return ids, hashes


def evaluator_sources(root: Path) -> dict[str, str]:
    return {name: sha256_file(root / name) for name in EVALUATOR_FILES}


def frozen_winner(root: Path, selection: Path, digest: str, method: str) -> dict:
    if method not in METHODS:
        raise ValueError("Final D_test method must be an integrated P1/P2 method")
    raw = selection.read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError("Frozen G7 selection manifest SHA-256 mismatch")
    data = json.loads(raw.decode("utf-8-sig"))
    if (data.get("schema_version") != VERSION or data.get("status") != "FINAL"
            or data.get("policy") != SELECTION_POLICY or data.get("missing_checkpoints") != []):
        raise ValueError("G7 must be FINAL with every candidate and the frozen policy")
    expected, _ = selection_records(root, partial=False)

    def stable(rows):
        # A sealed manifest may subsequently be read on another host.
        return [{k: v for k, v in row.items() if k not in {"timestamp_utc", "prediction_path"}} for row in rows]

    if stable(data["rows"]) != stable(expected):
        raise ValueError("Frozen G7 results differ from verified D_dev_select and checkpoint lineage")
    return next(row for row in expected if row["method"] == method
                and row["checkpoint"] == row["selected_checkpoint"])


def summarize_test(rows, ids, tag, summary):
    observed = [row["problem_id"] for row in rows]
    allowed = {"valid", "invalid_format", "invalid_answer"}
    if len(observed) != len(ids) or set(observed) != ids or any(
            row["checkpoint"] != tag or row["status"] not in allowed for row in rows):
        raise ValueError("Invalid final D_test prediction coverage, status or tag")
    n = len(ids)
    correct = sum(row["status"] == "valid" for row in rows)
    accuracy = correct / n
    if (summary.get("checkpoint"), summary.get("split"), summary.get("n_problems"),
            summary.get("n_valid"), summary.get("accuracy")) != (tag, "test", n, correct, accuracy):
        raise ValueError("Final D_test evaluator summary does not match strict predictions")
    z = 1.959963984540054
    denom = 1 + z * z / n
    center = (accuracy + z * z / (2 * n)) / denom
    margin = z * math.sqrt(accuracy * (1 - accuracy) / n + z * z / (4 * n * n)) / denom
    return {"n": n, "n_correct": correct, "n_incorrect": n - correct,
            "strict_accuracy": accuracy, "confidence_interval": {"method": "Wilson", "level": 0.95,
                "low": max(0.0, center - margin), "high": min(1.0, center + margin)}}


def evaluate_frozen(args):
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    from eval_student import evaluate, torch

    if not torch.cuda.is_available() or not torch.cuda.is_bf16_supported():
        raise RuntimeError("Approved final test requires a CUDA GPU with BF16 support")
    evaluate(args)


def run(root, method, selection, selection_sha, evaluator_sha, *, evaluator=evaluate_frozen):
    root = root.resolve()
    ids, split = audit_split(root)
    sources = evaluator_sources(root)
    if sha256_json(sources) != evaluator_sha:
        raise ValueError("Frozen evaluator SHA-256 mismatch")
    winner = frozen_winner(root, selection, selection_sha, method)
    checkpoint = winner["checkpoint"]
    tag = f"{method}_seed13_{checkpoint}"
    adapter = (None if checkpoint == "S0" else
               artifact_path(root, f"models/p1p2_integration/{method}_seed13/student_ckpt_{int(checkpoint[1:]):03d}"))
    checkpoint_path = adapter or root / "reports/p1p2_integration/source_review/s0_base_model_reference.json"
    expected_sha = winner["checkpoint_lineage"]["checkpoint_sha256"]
    if sha256(checkpoint_path) != expected_sha:
        raise ValueError("Frozen checkpoint SHA-256 mismatch")
    student = read_json(root / "config/experiment_config.json")["student"]
    if checkpoint == "S0":
        reference = read_json(checkpoint_path)
        if (reference["model_id"], reference["revision"], reference["adapter"]) != (
                student["model"], student["revision"], None):
            raise ValueError("S0 reference differs from the pinned Student")
    relative = f"reports/p1p2_integration/final_d_test/{tag}"
    output = artifact_path(root, relative)
    if output != root / relative:
        raise ValueError(f"Redirected final D_test output: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = output.with_name("." + tag + ".pending")
    if output.exists() or output.is_symlink():
        raise FileExistsError(output)
    # Exclusive directory doubles as the run reservation. Failures keep the original
    # evidence and require review, so the final test is never silently retried.
    stage.mkdir(exist_ok=False)
    prediction, summary_path = stage / "predictions.jsonl", stage / "summary.json"
    evaluator(argparse.Namespace(tag=tag, split="test", adapter=str(adapter) if adapter else None,
                                 backend="hf", dtype="bf16", batch_size=1, model=None, revision=None,
                                 limit=None, out=prediction, summary=summary_path))
    summary = read_json(summary_path)
    metrics = summarize_test(read_jsonl(prediction), ids, tag, summary)
    if (summary.get("model"), summary.get("revision"), summary.get("adapter")) != (
            student["model"], student["revision"], str(adapter) if adapter else None):
        raise ValueError("Final test report does not match the pinned Student and adapter")
    if (sha256(selection) != selection_sha or sha256(checkpoint_path) != expected_sha
            or audit_split(root)[1] != split or evaluator_sources(root) != sources):
        raise ValueError("Final test inputs changed during evaluation")
    provenance = {"schema_version": SCHEMA, "method": method, "seed": 13, "checkpoint": checkpoint,
                  "checkpoint_sha256": expected_sha, "selection_sha256": selection_sha,
                  "evaluator_fingerprint_sha256": evaluator_sha, "evaluator_files": sources,
                  "split": split, "student": {"model": student["model"], "revision": student["revision"]},
                  "settings": {"backend": "hf", "dtype": "bf16", "batch_size": 1},
                  "prediction_sha256": sha256(prediction), "summary_sha256": sha256(summary_path), **metrics}
    (stage / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    publish_staged_directory(stage, output)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--audit-only", action="store_true", help="Verify IDs and evaluator bytes without model imports")
    mode.add_argument("--execute", action="store_true", help="Separately approved final D_test only")
    parser.add_argument("--method", choices=METHODS)
    parser.add_argument("--selection", type=Path, help="Frozen FINAL G7 JSON")
    parser.add_argument("--selection-sha256", help="G7 SHA-256 recorded before test access")
    parser.add_argument("--evaluator-sha256", help="Evaluator fingerprint from approved package")
    args = parser.parse_args()
    if args.audit_only:
        ids, split = audit_split(ROOT)
        sources = evaluator_sources(ROOT)
        print(json.dumps({"D_TEST_EXECUTION": "NOT_RUN", "n_test": len(ids), "split": split,
                          "evaluator_fingerprint_sha256": sha256_json(sources), "evaluator_files": sources}, indent=2))
        return
    if not all((args.method, args.selection, args.selection_sha256, args.evaluator_sha256)):
        parser.error("--execute requires --method, --selection and both SHA-256 pins")
    print(run(ROOT, args.method, args.selection, args.selection_sha256, args.evaluator_sha256))


if __name__ == "__main__":
    main()
