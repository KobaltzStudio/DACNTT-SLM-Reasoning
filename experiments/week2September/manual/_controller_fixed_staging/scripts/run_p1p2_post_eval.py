#!/usr/bin/env python3
"""CLI post-evaluation hook for P1-DEFICIT and P1P2.

This is an adapter around the audited capability_eval.py implementation.
It evaluates completed D_dev predictions only; it does not select data,
compute NLL, train a model, or alter P1/P2 scoring semantics.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace


METHODS = ("P1-DEFICIT", "P1P2", "B2", "B3", "B4", "B5", "SHARED")


def load_evaluator(script_dir: Path):
    evaluator_path = script_dir / "capability_eval.py"
    if not evaluator_path.is_file():
        raise FileNotFoundError(f"Required audited evaluator not found: {evaluator_path}")
    spec = importlib.util.spec_from_file_location("p1p2_capability_eval_adapter", evaluator_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load evaluator module: {evaluator_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    required = ("build_input_hashes", "build_sidecar", "verify_existing_sidecar")
    missing = [name for name in required if not callable(getattr(module, name, None))]
    if missing:
        raise RuntimeError(f"capability_eval.py API mismatch; missing: {missing}")
    return module


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    manual = script_dir.parent
    parser = argparse.ArgumentParser(
        description="Run approved-85 capability evaluation after D_dev prediction completes."
    )
    parser.add_argument("--method", required=True, choices=METHODS)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--round", required=True, type=int, choices=(0, 1, 2, 3))
    parser.add_argument("--prediction", required=True, help="Completed D_dev prediction JSONL")
    parser.add_argument("--checkpoint", required=True, help="Exact checkpoint directory or S0 reference file")
    parser.add_argument("--output-dir", required=True, help="New immutable sidecar directory")
    parser.add_argument("--manual-root", default=str(manual))

    # Optional provenance inputs; pass these for every trained P1/P2 round.
    parser.add_argument("--train-set")
    parser.add_argument("--selection-log")
    parser.add_argument("--train-log")
    parser.add_argument("--checkpoint-log")
    parser.add_argument("--shared-checkpoint-group")

    parser.add_argument("--gold-manifest")
    parser.add_argument("--gold-labels")
    parser.add_argument("--approval-csv")
    parser.add_argument("--dev-ids")
    parser.add_argument("--config")
    args = parser.parse_args()

    if args.method == "SHARED":
        if args.seed != 0 or args.round != 0:
            parser.error("SHARED baseline requires --seed 0 --round 0")
        expected_run_id = "SHARED_seed0_S0"
    else:
        if args.round not in (1, 2, 3):
            parser.error("Trained methods require --round 1, 2, or 3")
        expected_run_id = f"{args.method}_seed{args.seed}_S{args.round}"

    args.run_id = expected_run_id
    root = Path(args.manual_root).resolve()
    defaults = {
        "gold_manifest": root / "data/gold_vfinal/gold_vfinal_manifest.json",
        "gold_labels": root / "data/gold_vfinal/supplement_annotations_vfinal.jsonl",
        "approval_csv": root / "reports/capability/p1_day14_final_2026-11-14/approved/gold_supplement_85_approved_review.csv",
        "dev_ids": root / "splits/d_dev_ids.txt",
        "config": root / "config/experiment_config.json",
    }
    for name, default in defaults.items():
        supplied = getattr(args, name)
        setattr(args, name, str(Path(supplied).resolve()) if supplied else str(default.resolve()))

    args.prediction = str(Path(args.prediction).resolve())
    args.dev_predictions = args.prediction
    args.checkpoint = str(Path(args.checkpoint).resolve())
    args.output_dir = str(Path(args.output_dir).resolve())
    args.out_root = str(Path(args.output_dir).parent)
    return args


def main() -> int:
    args = parse_args()
    root = Path(args.manual_root).resolve()
    output_dir = Path(args.output_dir)
    if output_dir.name != args.run_id:
        raise ValueError(
            f"--output-dir basename must be {args.run_id!r}; received {output_dir.name!r}"
        )

    evaluator = load_evaluator(Path(__file__).resolve().parent)
    input_hashes = evaluator.build_input_hashes(args)

    if output_dir.exists():
        evaluator.verify_existing_sidecar(output_dir, input_hashes)
        print(f"POST_EVAL_HOOK: REUSE_PASS {output_dir}")
        return 0

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{args.run_id}.staging.", dir=output_dir.parent))
    try:
        evaluator.build_sidecar(args, stage, input_hashes)
        if output_dir.exists():
            raise FileExistsError(f"Refusing to overwrite sidecar: {output_dir}")
        os.rename(stage, output_dir)
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise

    print(f"POST_EVAL_HOOK: PASS {output_dir}")
    print(f"METHOD: {args.method}")
    print(f"SEED: {args.seed}")
    print(f"ROUND: {args.round} -> S{args.round}")
    print(f"PREDICTION: {args.prediction}")
    print(f"CHECKPOINT: {args.checkpoint}")
    print("CORRECTNESS: status == valid")
    print("GOLD_SCOPE: approved 85; D_dev prediction coverage: 500")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"POST_EVAL_HOOK: FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
