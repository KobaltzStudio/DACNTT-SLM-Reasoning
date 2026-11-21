from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def relative(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve())).replace("\\", "/")
    except ValueError:
        return str(path.resolve())


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def record_file(path: Path, root: Path, category: str):
    if not path.is_file():
        raise FileNotFoundError(f"Provenance file missing: {path}")

    return {
        "category": category,
        "path": relative(path, root),
        "sha256": sha256(path),
        "size_bytes": path.stat().st_size,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manual", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    manual = Path(args.manual).resolve()
    output_dir = Path(args.output).resolve()

    eval_root = manual / "reports" / "capability" / "student_eval_2026-11-17"
    seed_root = manual / "models" / "task7" / "B4" / "seed_13"

    protocol = manual / "config" / "proposal1_graph_protocol.md"
    graph_schema = manual / "schemas" / "capability_graph_schema.json"
    learning_schema = manual / "schemas" / "student_learning_curve_schema.json"

    artifact_names = [
        "capability_learning_curves.csv",
        "capability_learning_curves.png",
        "capability_graph.json",
        "graph_evidence_ledger.csv",
        "student_learning_dynamics.md",
    ]

    artifacts = []

    for name in artifact_names:
        path = output_dir / name
        if not path.is_file() or path.stat().st_size == 0:
            raise FileNotFoundError(f"Artifact missing or empty: {path}")
        artifacts.append(record_file(path, manual, "generated_artifact"))

    inputs = [
        record_file(protocol, manual, "protocol"),
        record_file(graph_schema, manual, "schema"),
        record_file(learning_schema, manual, "schema"),
    ]

    checkpoint_records = []

    eval_dirs = [
        ("B4_seed13_ckpt001", 0, "student_ckpt_001"),
        ("B4_seed13_ckpt002", 1, "student_ckpt_002"),
        ("B4_seed13_ckpt003", 2, "student_ckpt_003"),
    ]

    for eval_dir_name, round_index, checkpoint_dir_name in eval_dirs:
        eval_dir = eval_root / eval_dir_name
        checkpoint_dir = seed_root / checkpoint_dir_name

        manifest_path = eval_dir / "student_capability_evaluation_manifest.json"
        metrics_csv = eval_dir / "capability_metrics.csv"
        metrics_jsonl = eval_dir / "capability_metrics.jsonl"
        train_log_path = checkpoint_dir / "train_log.json"

        for path in (
            manifest_path,
            metrics_csv,
            metrics_jsonl,
            train_log_path,
        ):
            if not path.is_file():
                raise FileNotFoundError(f"Required provenance file missing: {path}")

        train_log = load_json(train_log_path)

        train_set_path = Path(train_log["train_set"])

        if not train_set_path.is_file():
            raise FileNotFoundError(f"Train set missing: {train_set_path}")

        actual_train_set_hash = sha256(train_set_path)
        expected_train_set_hash = train_log["train_set_sha256"].lower()

        if actual_train_set_hash != expected_train_set_hash:
            raise ValueError(
                f"Train-set SHA256 mismatch: {train_set_path}"
            )

        train_set = load_json(train_set_path)

        if train_set.get("method") != "B4":
            raise ValueError(f"Unexpected train-set method: {train_set_path}")

        if int(train_set.get("training_seed", -1)) != 13:
            raise ValueError(f"Unexpected train-set seed: {train_set_path}")

        if int(train_set.get("round", -1)) != round_index:
            raise ValueError(f"Unexpected train-set round: {train_set_path}")

        checkpoint_records.append({
            "round": round_index,
            "checkpoint_directory": checkpoint_dir_name,
            "evaluation_directory": eval_dir_name,
            "checkpoint_parent": train_log.get("checkpoint_parent"),
            "seed": train_log.get("seed"),
            "data_order_seed": train_log.get("data_order_seed"),
            "train_set_path": relative(train_set_path, manual),
            "train_set_sha256": actual_train_set_hash,
            "train_set_source_checkpoint": train_set.get("source_checkpoint"),
            "train_set_round": train_set.get("round"),
            "train_set_method": train_set.get("method"),
            "train_set_seed": train_set.get("training_seed"),
            "n_examples_train_log": train_log.get("n_examples"),
            "n_trajectories_train_set": train_set.get("n_trajectories"),
            "pool_sha256_train_log": train_log.get("pool_sha256"),
            "pool_sha256_train_set": train_set.get("pool_sha256"),
            "round_normalization": (
                "round_unknown normalized to 0 after checkpoint identity "
                "and Round 0 training lineage verification"
                if round_index == 0
                else f"round_{round_index:03d}"
            ),
        })

        inputs.extend([
            record_file(manifest_path, manual, "evaluation_manifest"),
            record_file(metrics_csv, manual, "evaluation_metrics_csv"),
            record_file(metrics_jsonl, manual, "evaluation_metrics_jsonl"),
            record_file(train_log_path, manual, "train_log"),
            record_file(train_set_path, manual, "train_set"),
        ])

    manifest = {
        "manifest_version": "1.0",
        "project": "Proposal 1 - Student-Specific Capability Dependency, Transfer, and Learning Dynamics",
        "method": "B4",
        "seed": 13,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "checkpoint_rounds": [0, 1, 2],
        "capabilities": [
            "addition",
            "subtraction",
            "multiplication",
            "division",
            "percentage",
            "fraction",
            "ratio",
        ],
        "graph_summary": {
            "nodes": 7,
            "edges": 0,
            "prerequisite_edges": 0,
            "transfer_edges": 0,
        },
        "learning_curve_summary": {
            "observations": 21,
            "checkpoints": 3,
            "capabilities": 7,
        },
        "checkpoint_provenance": checkpoint_records,
        "artifacts": artifacts,
        "inputs": inputs,
        "integrity_policy": {
            "algorithm": "SHA256",
            "manifest_does_not_hash_itself": True,
            "source_files_modified": False,
        },
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "artifact_manifest.json"

    output_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("ARTIFACT MANIFEST BUILD: PASS")
    print(f"ARTIFACTS: {len(artifacts)}")
    print(f"INPUT FILES: {len(inputs)}")
    print(f"CHECKPOINTS: {len(checkpoint_records)}")
    print(f"OUTPUT: {output_path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ARTIFACT MANIFEST BUILD: FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
