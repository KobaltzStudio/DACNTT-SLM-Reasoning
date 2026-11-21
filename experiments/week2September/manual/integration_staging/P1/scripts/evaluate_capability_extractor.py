#!/usr/bin/env python3
"""Evaluate trajectory-level capability predictions against problem-level manual labels."""
import argparse
import csv
import json
from pathlib import Path

CAPABILITIES = [
    "addition", "subtraction", "multiplication", "division",
    "percentage", "fraction", "ratio"
]

def load_jsonl(path):
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid JSON at {path}:{line_no}: {exc}") from exc
    return rows

def f1(p, r):
    return 2 * p * r / (p + r) if p + r else 0.0

def metric(tp, fp, fn, tn):
    # With no positive gold labels, positive-class P/R/F1 are not meaningful.
    if tp + fn == 0:
        return {
            "TP": tp, "FP": fp, "FN": fn, "TN": tn,
            "precision": None, "recall": None, "f1": None,
            "status": "N/A_no_positive_gold"
        }
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn)
    return {
        "TP": tp, "FP": fp, "FN": fn, "TN": tn,
        "precision": precision, "recall": recall, "f1": f1(precision, recall),
        "status": "ok"
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("predictions", type=Path)
    parser.add_argument("manual_annotations", type=Path)
    parser.add_argument("report", type=Path)
    parser.add_argument("--csv", type=Path, default=None)
    args = parser.parse_args()

    preds = load_jsonl(args.predictions)
    manual = load_jsonl(args.manual_annotations)
    gold = {r["problem_id"]: set(r["capabilities_manual"]) for r in manual}

    counts = {c: {"TP": 0, "FP": 0, "FN": 0, "TN": 0} for c in CAPABILITIES}
    missing_gold = []
    duplicate_trajectory_ids = set()
    seen_ids = set()
    evaluated = 0

    for row in preds:
        pid = row.get("problem_id")
        tid = row.get("trajectory_id")
        if pid not in gold:
            missing_gold.append(pid)
            continue
        if tid in seen_ids:
            duplicate_trajectory_ids.add(tid)
        seen_ids.add(tid)
        pred = set(row.get("capabilities_predicted", []))
        truth = gold[pid]
        for c in CAPABILITIES:
            p, y = c in pred, c in truth
            if p and y: counts[c]["TP"] += 1
            elif p and not y: counts[c]["FP"] += 1
            elif not p and y: counts[c]["FN"] += 1
            else: counts[c]["TN"] += 1
        evaluated += 1

    per_capability = {
        c: metric(counts[c]["TP"], counts[c]["FP"], counts[c]["FN"], counts[c]["TN"])
        for c in CAPABILITIES
    }
    report = {
        "schema_version": "v1",
        "evaluation_unit": "trajectory",
        "gold_unit": "problem_manual_annotation",
        "interpretation": (
            "Each trajectory is compared with the manual capability labels of its problem_id. "
            "This validates trajectory extraction against problem-level human labels; it is not "
            "trajectory-specific human gold."
        ),
        "predictions_records": len(preds),
        "evaluated_records": evaluated,
        "missing_manual_problem_ids": sorted(set(missing_gold), key=str),
        "duplicate_trajectory_ids": sorted(duplicate_trajectory_ids, key=str),
        "capabilities": per_capability
    }

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if args.csv:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        with args.csv.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["capability", "TP", "FP", "FN", "TN", "precision", "recall", "F1", "status"])
            for c in CAPABILITIES:
                m = per_capability[c]
                w.writerow([c, m["TP"], m["FP"], m["FN"], m["TN"],
                            m["precision"], m["recall"], m["f1"], m["status"]])

    print("Capability extractor evaluation")
    print(f"Predictions: {len(preds)}")
    print(f"Evaluated:   {evaluated}")
    print()
    print(f"{'Capability':<16} {'P':>8} {'R':>8} {'F1':>8} {'TP':>5} {'FP':>5} {'FN':>5}")
    for c in CAPABILITIES:
        m = per_capability[c]
        fmt = lambda x: "N/A" if x is None else f"{x:.4f}"
        print(f"{c:<16} {fmt(m['precision']):>8} {fmt(m['recall']):>8} "
              f"{fmt(m['f1']):>8} {m['TP']:>5} {m['FP']:>5} {m['FN']:>5}")
    print(f"\nCreated: {args.report}")

if __name__ == "__main__":
    main()
