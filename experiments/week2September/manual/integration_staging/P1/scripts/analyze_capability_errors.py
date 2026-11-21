import argparse
import csv
import json
from pathlib import Path
from collections import Counter

def read_jsonl(path):
    records = []
    with open(path, "r", encoding="utf-8-sig") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}, line {line_no}: {exc}") from exc
    return records

def dump_csv(path, rows, fields):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

def compact(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--predictions", required=True)
    p.add_argument("--annotations", required=True)
    p.add_argument("--raw", required=True)
    p.add_argument("--out-dir", required=True)
    args = p.parse_args()

    predictions = read_jsonl(args.predictions)
    annotations = read_jsonl(args.annotations)
    raw_records = read_jsonl(args.raw)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    ann_by_problem = {}
    for a in annotations:
        pid = a["problem_id"]
        if pid in ann_by_problem:
            raise ValueError(f"Duplicate annotation problem_id: {pid}")
        ann_by_problem[pid] = set(a.get("capabilities_manual", []))

    raw_by_tid = {}
    for r in raw_records:
        tid = r.get("trajectory_id")
        if tid in raw_by_tid:
            raise ValueError(f"Duplicate raw trajectory_id: {tid}")
        raw_by_tid[tid] = r

    pred_ids = [r.get("trajectory_id") for r in predictions]
    if len(pred_ids) != len(set(pred_ids)):
        raise ValueError("Duplicate trajectory_id in prediction file")

    missing_annotations = sorted({
        r.get("problem_id") for r in predictions
        if r.get("problem_id") not in ann_by_problem
    })
    missing_raw = sorted({
        r.get("trajectory_id") for r in predictions
        if r.get("trajectory_id") not in raw_by_tid
    })
    if missing_annotations or missing_raw:
        raise ValueError(
            f"Missing annotations={missing_annotations}; missing raw={missing_raw}"
        )

    capabilities = [
        "addition", "subtraction", "multiplication",
        "division", "percentage", "fraction", "ratio"
    ]

    errors = []
    counts = {c: Counter() for c in capabilities}

    for pred in predictions:
        pid = pred["problem_id"]
        tid = pred["trajectory_id"]
        gold = ann_by_problem[pid]
        predicted = set(pred.get("capabilities_predicted", []))
        raw = raw_by_tid[tid]

        for cap in capabilities:
            is_gold = cap in gold
            is_pred = cap in predicted
            if is_gold == is_pred:
                continue

            kind = "FP" if is_pred else "FN"
            counts[cap][kind] += 1

            errors.append({
                "error_type": kind,
                "capability": cap,
                "problem_id": pid,
                "trajectory_id": tid,
                "gold_has_capability": is_gold,
                "predicted_has_capability": is_pred,
                "gold_capabilities": compact(sorted(gold)),
                "predicted_capabilities": compact(sorted(predicted)),
                "rules_fired": compact(
                    pred.get("rules_fired", {}).get(cap, [])
                ),
                "evidence": compact(
                    pred.get("evidence", {}).get(cap, [])
                ),
                "question": raw.get("question", ""),
                "answer": raw.get("answer", ""),
                "ground_truth": raw.get("ground_truth", ""),
                "verification_status": raw.get("metadata", {}).get(
                    "verification_status", ""
                ),
                "reasoning_trace": raw.get("reasoning_trace", "")
            })

    fields = [
        "error_type", "capability", "problem_id", "trajectory_id",
        "gold_has_capability", "predicted_has_capability",
        "gold_capabilities", "predicted_capabilities",
        "rules_fired", "evidence", "question", "answer",
        "ground_truth", "verification_status", "reasoning_trace"
    ]

    errors.sort(key=lambda x: (
        x["capability"], x["error_type"], x["problem_id"], x["trajectory_id"]
    ))
    dump_csv(out_dir / "capability_error_cases.csv", errors, fields)

    division_fp = [
        r for r in errors
        if r["capability"] == "division" and r["error_type"] == "FP"
    ]
    dump_csv(out_dir / "division_false_positives.csv", division_fp, fields)

    ratio_fp = [
        r for r in errors
        if r["capability"] == "ratio" and r["error_type"] == "FP"
    ]
    dump_csv(out_dir / "ratio_false_positives.csv", ratio_fp, fields)

    summary = []
    for cap in capabilities:
        fp = counts[cap]["FP"]
        fn = counts[cap]["FN"]
        summary.append({
            "capability": cap,
            "FP": fp,
            "FN": fn,
            "total_errors": fp + fn
        })
    dump_csv(
        out_dir / "capability_error_summary.csv",
        summary,
        ["capability", "FP", "FN", "total_errors"]
    )

    print(f"Predictions: {len(predictions)}")
    print(f"Annotations: {len(annotations)}")
    print(f"Raw trajectories: {len(raw_records)}")
    print(f"Error cases: {len(errors)}")
    print(f"Division FP cases: {len(division_fp)}")
    print(f"Ratio FP cases: {len(ratio_fp)}")
    print(f"Output directory: {out_dir}")
    print("\nError summary:")
    for row in summary:
        print(
            f'{row["capability"]:15s} '
            f'FP={row["FP"]:3d} FN={row["FN"]:3d} '
            f'total={row["total_errors"]:3d}'
        )

if __name__ == "__main__":
    main()
