#!/usr/bin/env python3
"""Run the complete Task-4 extractor/evaluation pipeline on batch_100."""
import argparse, json, subprocess, sys
from pathlib import Path


def run(cmd):
    print("+", " ".join(map(str, cmd)))
    subprocess.run(cmd, check=True)


def count_jsonl(path):
    return sum(1 for line in path.open("r", encoding="utf-8") if line.strip())


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument("--raw", type=Path, default=None)
    p.add_argument("--manual", type=Path, default=None)
    args = p.parse_args()

    root = args.repo
    raw = args.raw or root / "trajectory" / "pool" / "batch_100_teacher_raw.jsonl"
    manual = args.manual or root / "data" / "batch_100" / "batch_100_annotations.jsonl"
    prepared = root / "trajectory" / "pool" / "batch_100_teacher_verified.jsonl"
    predictions = root / "trajectory" / "pool" / "batch_100_capability_predictions.jsonl"
    report = root / "reports" / "capability_extractor_batch100_report.json"
    csv = root / "reports" / "capability_extractor_batch100_report.csv"

    prepare = root / "scripts" / "prepare_task4_trajectory_input.py"
    extract = root / "scripts" / "extract_capabilities_rule_based.py"
    evaluate = root / "scripts" / "evaluate_capability_extractor.py"

    if not raw.exists():
        raise FileNotFoundError(f"Missing Teacher trajectory file: {raw}")
    if not manual.exists():
        raise FileNotFoundError(f"Missing manual gold: {manual}")

    run([sys.executable, str(prepare), str(raw), str(prepared)])
    run([sys.executable, str(extract), str(prepared), str(predictions)])
    run([sys.executable, str(evaluate), str(predictions), str(manual), str(report), "--csv", str(csv)])

    n_raw = count_jsonl(raw)
    n_pred = count_jsonl(predictions)
    print(f"Raw trajectories: {n_raw}")
    print(f"Evaluated trajectories: {n_pred}")
    print(f"Report JSON: {report}")
    print(f"Report CSV:  {csv}")


if __name__ == "__main__":
    main()
