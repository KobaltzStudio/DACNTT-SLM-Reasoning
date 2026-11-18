#!/usr/bin/env python3
"""P1/P2 post-evaluation hook.

Wraps the audited P2 capability evaluator without modifying its source.
Publishes an immutable capability sidecar for SHARED, B2-B5,
P1-DEFICIT, or P1P2.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace


SUPPORTED_METHODS = {
    "B2",
    "B3",
    "B4",
    "B5",
    "P1-DEFICIT",
    "P1P2",
}
SHARED_METHOD = "SHARED"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="P1/P2 immutable post-evaluation capability hook"
    )

    parser.add_argument("--method", required=True)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument(
        "--round",
        required=True,
        type=int,
        choices=[0, 1, 2, 3],
    )
    parser.add_argument("--prediction", required=True)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--out-dir", required=True)

    parser.add_argument(
        "--gold-manifest",
        default="data/gold_vfinal/gold_vfinal_manifest.json",
    )
    parser.add_argument(
        "--gold-labels",
        default="data/gold_vfinal/supplement_annotations_vfinal.jsonl",
    )
    parser.add_argument(
        "--approval-csv",
        default=(
            "data/gold_releases/vFinal_2026-11-16/"
            "gold_supplement_85_approved_review.csv"
        ),
    )
    parser.add_argument("--dev-ids", default="splits/d_dev_ids.txt")
    parser.add_argument(
        "--config",
        default="config/experiment_config.json",
    )

    parser.add_argument("--train-set")
    parser.add_argument("--selection-log")
    parser.add_argument("--train-log")
    parser.add_argument("--checkpoint-log")
    parser.add_argument("--shared-checkpoint-group")

    args = parser.parse_args()

    if args.method == SHARED_METHOD:
        if args.seed != 0 or args.round != 0:
            parser.error("SHARED baseline requires --seed 0 --round 0")
        if any((
            args.train_set,
            args.selection_log,
            args.train_log,
            args.checkpoint_log,
        )):
            parser.error("SHARED S0 must not receive round training artifacts")
    else:
        if args.method not in SUPPORTED_METHODS:
            parser.error(
                f"Unsupported method {args.method!r}. "
                f"Allowed: {sorted(SUPPORTED_METHODS)} and SHARED. "
                "P1-GRAPH is intentionally excluded until graph evidence "
                "passes the project evidence gate."
            )
        if args.round == 0:
            parser.error("S0 is the shared baseline; method-specific runs start at S1")
        missing = [
            name
            for name in (
                "train_set",
                "selection_log",
                "train_log",
                "checkpoint_log",
            )
            if not getattr(args, name)
        ]
        if missing:
            parser.error(
                "S1-S3 require all training lineage inputs: "
                + ", ".join("--" + x.replace("_", "-") for x in missing)
            )

    expected_run_id = (
        "SHARED_seed0_S0"
        if args.method == SHARED_METHOD
        else f"{args.method}_seed{args.seed}_S{args.round}"
    )
    args.run_id = expected_run_id

    return args


def main() -> int:
    args = parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    script_dir = repo_root / "scripts"

    if str(script_dir) not in sys.path:
        sys.path.insert(0, str(script_dir))

    try:
        import capability_eval as evaluator
    except Exception as exc:
        raise RuntimeError(
            "Cannot import scripts/capability_eval.py. "
            "Keep the audited evaluator in the scripts directory."
        ) from exc

    # Resolve every path against the canonical repository root.
    path_fields = (
        "prediction",
        "checkpoint",
        "gold_manifest",
        "gold_labels",
        "approval_csv",
        "dev_ids",
        "config",
        "train_set",
        "selection_log",
        "train_log",
        "checkpoint_log",
    )

    resolved = {}
    for field in path_fields:
        value = getattr(args, field, None)
        if value:
            path = Path(value)
            if not path.is_absolute():
                path = repo_root / path
            resolved[field] = path.resolve()
        else:
            resolved[field] = None

    required_fields = (
        "prediction",
        "checkpoint",
        "gold_manifest",
        "gold_labels",
        "approval_csv",
        "dev_ids",
        "config",
    )
    for field in required_fields:
        path = resolved[field]
        if path is None or not path.exists():
            raise FileNotFoundError(
                f"Required input {field!r} does not exist: {path}"
            )

    for field in (
        "train_set",
        "selection_log",
        "train_log",
        "checkpoint_log",
    ):
        path = resolved[field]
        if args.method != SHARED_METHOD and (
            path is None or not path.is_file()
        ):
            raise FileNotFoundError(
                f"Required S1-S3 lineage file {field!r} is missing: {path}"
            )

    checkpoint = resolved["checkpoint"]
    if not checkpoint.is_file() and not checkpoint.is_dir():
        raise FileNotFoundError(
            f"Checkpoint reference does not exist: {checkpoint}"
        )

    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = repo_root / out_dir
    out_dir = out_dir.resolve()

    if out_dir == repo_root or repo_root not in out_dir.parents:
        raise ValueError(
            f"Output must be a child of the repository root: {out_dir}"
        )

    # The existing evaluator expects these attribute names.
    evaluator_args = SimpleNamespace(
        run_id=args.run_id,
        method=args.method,
        seed=args.seed,
        round=args.round,
        checkpoint=str(checkpoint),
        dev_predictions=str(resolved["prediction"]),
        gold_manifest=str(resolved["gold_manifest"]),
        gold_labels=str(resolved["gold_labels"]),
        approval_csv=str(resolved["approval_csv"]),
        dev_ids=str(resolved["dev_ids"]),
        config=str(resolved["config"]),
        train_set=(
            str(resolved["train_set"])
            if resolved["train_set"] else None
        ),
        selection_log=(
            str(resolved["selection_log"])
            if resolved["selection_log"] else None
        ),
        train_log=(
            str(resolved["train_log"])
            if resolved["train_log"] else None
        ),
        checkpoint_log=(
            str(resolved["checkpoint_log"])
            if resolved["checkpoint_log"] else None
        ),
        shared_checkpoint_group=args.shared_checkpoint_group,
    )

    input_hashes = evaluator.build_input_hashes(evaluator_args)

    if out_dir.exists():
        evaluator.verify_existing_sidecar(out_dir, input_hashes)
        print(f"POST_EVAL_HOOK: REUSED {out_dir}")
        print(f"RUN_ID={args.run_id}")
        print(f"METHOD={args.method}")
        print(f"SEED={args.seed}")
        print(f"ROUND={args.round}")
        return 0

    out_dir.parent.mkdir(parents=True, exist_ok=True)

    stage = Path(tempfile.mkdtemp(
        prefix=f".{out_dir.name}.staging.",
        dir=str(out_dir.parent),
    ))

    try:
        evaluator.build_sidecar(
            evaluator_args,
            stage,
            input_hashes,
        )

        if out_dir.exists():
            raise FileExistsError(
                "Output directory appeared during publication; "
                "refusing to overwrite it: " + str(out_dir)
            )

        os.rename(stage, out_dir)

    except Exception:
        # Preserve the final destination. Only this invocation's staging
        # directory is removed after a failed build.
        shutil.rmtree(stage, ignore_errors=True)
        raise

    print(f"POST_EVAL_HOOK: PASS {out_dir}")
    print(f"RUN_ID={args.run_id}")
    print(f"METHOD={args.method}")
    print(f"SEED={args.seed}")
    print(f"ROUND={args.round}")
    print(f"PREDICTION_SHA256={input_hashes['dev_predictions']}")
    print(f"CHECKPOINT_SHA256={input_hashes['checkpoint']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
