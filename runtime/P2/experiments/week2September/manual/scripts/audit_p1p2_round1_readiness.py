#!/usr/bin/env python3
"""Read-only preflight for the existing P1-DEFICIT/P1P2 seed-13 round-1 artifacts.

This script never writes to the project. It validates the two existing round-1
train sets and selection logs against the verified pool, token table, D_pool,
frozen config, state files, and (for P1P2) the S0 NLL file.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from pathlib import Path

TAXONOMY = {
    "addition", "subtraction", "multiplication", "division",
    "percentage", "fraction", "ratio",
}
METHODS = ("P1-DEFICIT", "P1P2")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path):
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def read_jsonl(path: Path):
    rows = []
    with path.open("r", encoding="utf-8-sig") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL {path}:{line_no}: {exc}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"Expected object at {path}:{line_no}")
            rows.append(row)
    return rows


def require_file(path: Path, label: str):
    if not path.is_file():
        raise FileNotFoundError(f"{label} missing: {path}")
    return path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manual", required=True, type=Path)
    args = ap.parse_args()
    manual = args.manual.resolve()

    config_path = require_file(manual / "config/experiment_config.json", "Frozen config")
    pool_path = require_file(manual / "trajectory/pool/pool_v1_verified.jsonl", "Verified pool")
    tokens_path = require_file(manual / "trajectory/pool/pool_v1_tokens.jsonl", "Token table")
    token_summary_path = require_file(tokens_path.with_suffix(".summary.json"), "Token summary")
    d_pool_path = require_file(manual / "splits/d_pool_ids.txt", "D_pool IDs")

    config = read_json(config_path)
    pool_rows = read_jsonl(pool_path)
    token_rows = read_jsonl(tokens_path)
    token_summary = read_json(token_summary_path)

    pool_by_id = {}
    problems = {}
    for i, row in enumerate(pool_rows, 1):
        tid = row.get("trajectory_id")
        pid = row.get("problem_id")
        metadata = row.get("metadata")
        tags = row.get("capabilities")
        if not isinstance(tid, str) or not tid or tid in pool_by_id:
            raise ValueError(f"Invalid/duplicate trajectory_id in pool row {i}: {tid!r}")
        if not isinstance(pid, str) or not pid:
            raise ValueError(f"Invalid problem_id in pool row {i}")
        if not isinstance(metadata, dict) or metadata.get("verification_status") != "valid":
            raise ValueError(f"Pool trajectory is not verified valid: {tid}")
        if not isinstance(tags, list) or not tags or set(tags) - TAXONOMY:
            raise ValueError(f"Invalid capability tags for {tid}: {tags!r}")
        if len(tags) != len(set(tags)):
            raise ValueError(f"Duplicate capability tags for {tid}")
        pool_by_id[tid] = row
        problems[tid] = pid

    d_pool_ids = {
        x.strip() for x in d_pool_path.read_text(encoding="utf-8-sig").splitlines()
        if x.strip()
    }
    if not d_pool_ids:
        raise ValueError("D_pool ID set is empty")
    outside = sorted({r["problem_id"] for r in pool_rows} - d_pool_ids)
    if outside:
        raise ValueError(f"Verified pool includes problems outside D_pool: {outside[:5]}")

    tokens = {}
    token_problems = {}
    for i, row in enumerate(token_rows, 1):
        tid = row.get("trajectory_id")
        pid = row.get("problem_id")
        count = row.get("response_tokens")
        if not isinstance(tid, str) or not tid or tid in tokens:
            raise ValueError(f"Invalid/duplicate token trajectory_id at row {i}: {tid!r}")
        if tid not in problems or problems[tid] != pid:
            raise ValueError(f"Token row does not match verified pool: {tid}")
        if not isinstance(count, int) or isinstance(count, bool) or count <= 0:
            raise ValueError(f"Invalid response_tokens for {tid}: {count!r}")
        tokens[tid] = count
        token_problems[tid] = pid

    if set(tokens) != set(pool_by_id):
        raise ValueError(
            f"Pool/token coverage mismatch: pool={len(pool_by_id)}, tokens={len(tokens)}, "
            f"missing={len(set(pool_by_id)-set(tokens))}, extra={len(set(tokens)-set(pool_by_id))}"
        )
    if token_summary.get("pool_sha256") != sha256(pool_path):
        raise ValueError("Token summary was built from a different verified pool")
    if token_summary.get("n_trajectories") != len(tokens):
        raise ValueError("Token summary n_trajectories mismatch")
    if token_summary.get("response_tokens_sum") != sum(tokens.values()):
        raise ValueError("Token summary response_tokens_sum mismatch")

    print(f"POOL_COUNT={len(pool_by_id)}")
    print(f"POOL_SHA256={sha256(pool_path)}")
    print(f"TOKEN_COUNT={len(tokens)}")
    print(f"TOKEN_SHA256={sha256(tokens_path)}")
    print(f"CONFIG_SHA256={sha256(config_path)}")
    print(f"CONFIG_OFFICIAL_RUNS={config.get('training', {}).get('official_runs')}")
    print(f"CONFIG_LOCAL_RUNS={config.get('training', {}).get('local_runs')}")

    failures = []
    for method in METHODS:
        run_dir = manual / "runs/p1p2_integration" / f"{method}_seed13"
        round_dir = run_dir / "round_001"
        train_path = require_file(round_dir / "train_set.json", f"{method} round-1 train set")
        log_path = require_file(round_dir / "selection_log.jsonl", f"{method} round-1 selection log")
        train_set = read_json(train_path)
        log_rows = read_jsonl(log_path)

        expected_fields = {
            "schema_version": "p1p2.train-set.v1",
            "method": method,
            "training_seed": 13,
            "round": 1,
            "source_checkpoint": "S0",
        }
        for key, expected in expected_fields.items():
            if train_set.get(key) != expected:
                raise ValueError(
                    f"{method} round-1 train_set {key}: expected {expected!r}, "
                    f"got {train_set.get(key)!r}"
                )

        checks = {
            "pool_sha256": sha256(pool_path),
            "tokens_sha256": sha256(tokens_path),
            "tokens_summary_sha256": sha256(token_summary_path),
            "config_sha256": sha256(config_path),
        }
        for key, expected in checks.items():
            if train_set.get(key) != expected:
                raise ValueError(f"{method} train_set {key} mismatch")

        state_path = Path(train_set.get("state_file", ""))
        if not state_path.is_absolute():
            state_path = (manual / state_path).resolve()
        require_file(state_path, f"{method} S0-derived capability state")
        if sha256(state_path) != train_set.get("state_sha256"):
            raise ValueError(f"{method} capability state hash mismatch")
        state = read_json(state_path)
        target = state.get("target", {})
        if (
            state.get("schema_version") != "p1p2.capability-state.v1"
            or target.get("method") != method
            or target.get("seed") != 13
            or target.get("selection_round") != 1
        ):
            raise ValueError(f"{method} capability state target/schema mismatch")

        ids = train_set.get("trajectory_ids")
        if not isinstance(ids, list) or not ids:
            raise ValueError(f"{method} train set has no trajectory_ids")
        if len(ids) != len(set(ids)):
            raise ValueError(f"{method} train set contains duplicate trajectory IDs")
        unknown = sorted(set(ids) - set(pool_by_id))
        if unknown:
            raise ValueError(f"{method} train set contains IDs outside verified pool: {unknown[:5]}")
        selected_problem_ids = [problems[tid] for tid in ids]
        if len(selected_problem_ids) != len(set(selected_problem_ids)):
            raise ValueError(f"{method} train set violates n_cap=1")
        actual_tokens = sum(tokens[tid] for tid in ids)
        if actual_tokens != train_set.get("tokens_used"):
            raise ValueError(f"{method} train_set tokens_used does not match token table")
        budget = config["budget"]["beta_round_tokens"]
        if actual_tokens > budget or train_set.get("beta_round_tokens") != budget:
            raise ValueError(f"{method} train set exceeds/mismatches frozen round budget")
        if train_set.get("n_cap") != 1:
            raise ValueError(f"{method} train set n_cap is not 1")
        if train_set.get("n_selected") != len(ids):
            raise ValueError(f"{method} train_set n_selected mismatch")

        selected_log_ids = {
            row.get("trajectory_id") for row in log_rows if row.get("selected") is True
        }
        if selected_log_ids != set(ids):
            raise ValueError(f"{method} selection log selected IDs differ from train set")
        if len(log_rows) != len(pool_by_id):
            raise ValueError(f"{method} selection log row count != verified pool count")
        for row in log_rows:
            if row.get("method") != method or row.get("seed") != 13 or row.get("round") != 1:
                raise ValueError(f"{method} selection log identity mismatch")
            if row.get("source_checkpoint") != "S0":
                raise ValueError(f"{method} selection log source checkpoint mismatch")
            if row.get("trajectory_id") not in pool_by_id:
                raise ValueError(f"{method} selection log contains trajectory outside pool")

        nll_path_value = train_set.get("nll_file")
        if method == "P1-DEFICIT":
            if nll_path_value is not None or train_set.get("nll_sha256") is not None:
                raise ValueError("P1-DEFICIT must not consume NLL")
            nll_status = "NOT_USED"
        else:
            if not nll_path_value:
                raise ValueError("P1P2 round 1 has no S0 NLL source")
            nll_path = Path(nll_path_value)
            if not nll_path.is_absolute():
                nll_path = (manual / nll_path).resolve()
            require_file(nll_path, "P1P2 S0 NLL")
            if sha256(nll_path) != train_set.get("nll_sha256"):
                raise ValueError("P1P2 S0 NLL hash mismatch")
            nll_summary_path = nll_path.with_suffix(".summary.json")
            nll_summary = read_json(require_file(nll_summary_path, "P1P2 S0 NLL summary"))
            if (
                nll_summary.get("checkpoint") != "S0"
                or nll_summary.get("pool_sha256") != sha256(pool_path)
                or nll_summary.get("n_trajectories") != len(pool_by_id)
            ):
                raise ValueError("P1P2 S0 NLL summary checkpoint/pool/count mismatch")
            nll_rows = read_jsonl(nll_path)
            if len(nll_rows) != len(pool_by_id):
                raise ValueError("P1P2 S0 NLL row count mismatch")
            nll_by_id = {}
            for row in nll_rows:
                tid = row.get("trajectory_id")
                if tid in nll_by_id or tid not in tokens:
                    raise ValueError(f"Duplicate/unknown trajectory in S0 NLL: {tid}")
                if row.get("checkpoint") != "S0" or row.get("n_tokens") != tokens[tid]:
                    raise ValueError(f"P1P2 S0 NLL row checkpoint/token mismatch: {tid}")
                ell = row.get("ell")
                if not isinstance(ell, (int, float)) or isinstance(ell, bool) or not math.isfinite(ell):
                    raise ValueError(f"Invalid P1P2 S0 NLL ell: {tid}")
                nll_by_id[tid] = ell
            if set(nll_by_id) != set(tokens):
                raise ValueError("P1P2 S0 NLL does not cover the verified pool exactly")
            nll_status = f"PASS:{len(nll_by_id)}"

        print(f"\nMETHOD={method}")
        print(f"TRAIN_SET={train_path}")
        print(f"TRAIN_SET_SHA256={sha256(train_path)}")
        print(f"SELECTION_LOG_SHA256={sha256(log_path)}")
        print(f"STATE_PATH={state_path}")
        print(f"STATE_SHA256={sha256(state_path)}")
        print(f"SELECTED_COUNT={len(ids)}")
        print(f"TOKENS_USED={actual_tokens}/{budget}")
        print(f"SELECTION_LOG_ROWS={len(log_rows)}")
        print(f"NLL={nll_status}")
        print("ROUND1_SELECTION_PREFLIGHT=PASS")

        for round_number in (2, 3):
            later = run_dir / f"round_{round_number:03d}"
            model = manual / "models/p1p2_integration" / f"{method}_seed13" / f"student_ckpt_{round_number:03d}"
            print(
                f"ROUND{round_number}_RUN_DIR_EXISTS={later.exists()} "
                f"MODEL_DIR_EXISTS={model.exists()}"
            )

    print("\n=== GPU / PYTORCH PREFLIGHT ===")
    cuda_available = False
    try:
        import torch
        print(f"TORCH_VERSION={torch.__version__}")
        cuda_available = bool(torch.cuda.is_available())
        print(f"CUDA_AVAILABLE={cuda_available}")
        if cuda_available:
            for index in range(torch.cuda.device_count()):
                props = torch.cuda.get_device_properties(index)
                total_gb = props.total_memory / (1024 ** 3)
                print(f"GPU_{index}={props.name}")
                print(f"GPU_{index}_TOTAL_MEMORY_GB={total_gb:.2f}")
        else:
            print("GPU_WARNING=No CUDA device visible to the active Python environment")
    except Exception as exc:
        print(f"TORCH_PREFLIGHT_ERROR={type(exc).__name__}: {exc}")

    print("\nROUND1_ARTIFACT_PREFLIGHT=PASS")
    print("TRAINING_DEVICE_STATUS=" + ("CUDA_VISIBLE_REQUIRES_MEMORY_REVIEW" if cuda_available else "NO_CUDA_DO_NOT_START_FULL_TRAINING"))
    print("AUDIT_MODE=READ_ONLY")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ROUND1_READINESS=FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
