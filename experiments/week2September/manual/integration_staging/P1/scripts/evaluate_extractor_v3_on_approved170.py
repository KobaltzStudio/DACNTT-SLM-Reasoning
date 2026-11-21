#!/usr/bin/env python3
"""Evaluate extractor rules v2/v3 against the approved 170-record development review.

This is a development-set comparison, NOT an independent test evaluation.
Uses the problem question text because the approved CSV does not contain full
Teacher trajectories. Do not compare these numbers directly with trajectory-
level D2 results without stating this input-source difference.
"""
import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

CAPABILITIES = [
    "addition", "subtraction", "multiplication", "division",
    "percentage", "fraction", "ratio"
]

def parse_labels(value):
    if value is None or not str(value).strip():
        return set()
    value = str(value).strip()
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return set(parsed)
    except json.JSONDecodeError:
        pass
    return {x.strip() for x in value.split(",") if x.strip()}

def load_rules(path, extractor):
    data = json.loads(path.read_text(encoding="utf-8"))
    return extractor.compile_rules(data)

def score(rows, pred_field):
    tp = Counter()
    fp = Counter()
    fn = Counter()
    exact = 0
    for row in rows:
        gold = set(row["_gold"])
        pred = set(row[pred_field])
        exact += (gold == pred)
        for c in CAPABILITIES:
            if c in gold and c in pred: tp[c] += 1
            elif c in pred and c not in gold: fp[c] += 1
            elif c in gold and c not in pred: fn[c] += 1
    TP, FP, FN = sum(tp.values()), sum(fp.values()), sum(fn.values())
    precision = TP / (TP + FP) if TP + FP else 0.0
    recall = TP / (TP + FN) if TP + FN else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "records": len(rows), "exact_match": exact,
        "exact_match_rate": exact / len(rows) if rows else 0.0,
        "micro_TP": TP, "micro_FP": FP, "micro_FN": FN,
        "micro_precision": precision, "micro_recall": recall, "micro_f1": f1,
        "per_capability": {
            c: {"TP": tp[c], "FP": fp[c], "FN": fn[c],
                "precision": tp[c] / (tp[c] + fp[c]) if tp[c] + fp[c] else 0.0,
                "recall": tp[c] / (tp[c] + fn[c]) if tp[c] + fn[c] else 0.0}
            for c in CAPABILITIES
        }
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--approved-csv", required=True, type=Path)
    ap.add_argument("--rules-v2", required=True, type=Path)
    ap.add_argument("--rules-v3", required=True, type=Path)
    ap.add_argument("--extractor", required=True, type=Path)
    ap.add_argument("--d2-jsonl", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    args = ap.parse_args()

    sys.path.insert(0, str(args.extractor.parent))
    import extract_capabilities_rule_based as extractor

    with args.approved_csv.open("r", encoding="utf-8-sig", newline="") as f:
        source_rows = list(csv.DictReader(f))
    if len(source_rows) != 170:
        raise SystemExit(f"Expected 170 approved rows, found {len(source_rows)}")
    ids = [r["problem_id"] for r in source_rows]
    if len(set(ids)) != len(ids):
        raise SystemExit("Duplicate problem_id in approved CSV")

    compiled_v2 = load_rules(args.rules_v2, extractor)
    compiled_v3 = load_rules(args.rules_v3, extractor)
    rows = []
    for source in source_rows:
        question = source.get("question", "")
        gold = parse_labels(source.get("gold_capabilities", ""))
        p2, e2, f2 = extractor.extract_capabilities(question, compiled_v2)
        p3, e3, f3 = extractor.extract_capabilities(question, compiled_v3)
        rows.append({
            **source, "_gold": gold,
            "v2_predictions": sorted(p2), "v3_predictions": sorted(p3),
            "v2_evidence": json.dumps(e2, ensure_ascii=False),
            "v3_evidence": json.dumps(e3, ensure_ascii=False),
            "v2_rules_fired": json.dumps(f2, ensure_ascii=False),
            "v3_rules_fired": json.dumps(f3, ensure_ascii=False),
        })

    metrics = {
        "evaluation": "approved 170 development records; question-only input",
        "warning": "Not an independent test set; Gold review notes state source worked traces are unavailable for these records.",
        "v2": score(rows, "v2_predictions"),
        "v3": score(rows, "v3_predictions"),
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "metrics_v2_vs_v3_approved170.json").write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    fields = list(source_rows[0].keys()) + [
        "v2_predictions", "v3_predictions", "v2_evidence", "v3_evidence",
        "v2_rules_fired", "v3_rules_fired", "changed_capabilities",
        "v2_false_negatives", "v2_false_positives",
        "v3_false_negatives", "v3_false_positives"
    ]
    changed = []
    all_results = []
    for row in rows:
        gold = row["_gold"]
        p2, p3 = set(row["v2_predictions"]), set(row["v3_predictions"])
        out = {k: row.get(k, "") for k in fields if k in row}
        out.update({
            "changed_capabilities": json.dumps({
                "added_in_v3": sorted(p3-p2), "removed_in_v3": sorted(p2-p3)
            }),
            "v2_false_negatives": json.dumps(sorted(gold-p2)),
            "v2_false_positives": json.dumps(sorted(p2-gold)),
            "v3_false_negatives": json.dumps(sorted(gold-p3)),
            "v3_false_positives": json.dumps(sorted(p3-gold)),
        })
        all_results.append(out)
        if p2 != p3:
            changed.append(out)

    for name, data in [
        ("predictions_v2_v3_all170.csv", all_results),
        ("prediction_changes_review.csv", changed),
    ]:
        with (args.out_dir / name).open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(data)

    d2 = []
    with args.d2_jsonl.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                d2.append(json.loads(line))
    d2_ids = {str(x.get("problem_id") or x.get("question_id") or x.get("test_id")) for x in d2}
    approved_ids = set(ids)
    overlap = sorted(approved_ids & d2_ids)
    independence = {
        "approved170_unique_ids": len(approved_ids),
        "d2_records": len(d2),
        "d2_unique_ids": len(d2_ids),
        "id_overlap_count": len(overlap),
        "overlap_ids": overlap,
        "id_disjoint": len(overlap) == 0,
        "warning": "ID disjointness alone does not prove independence. Also inspect how D2 cases were authored and whether they were derived from or tuned against the 170 records."
    }
    (args.out_dir / "d2_independence_check.json").write_text(
        json.dumps(independence, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print("APPROVED 170 DEVELOPMENT-SET EVALUATION (question-only)")
    for version in ("v2", "v3"):
        m = metrics[version]
        print(f"{version}: exact={m['exact_match']}/170 ({m['exact_match_rate']:.4f}), "
              f"TP={m['micro_TP']} FP={m['micro_FP']} FN={m['micro_FN']}, "
              f"P={m['micro_precision']:.4f} R={m['micro_recall']:.4f} F1={m['micro_f1']:.4f}")
    print(f"Changed prediction rows: {len(changed)}/170")
    print(f"D2/approved ID overlap: {len(overlap)}")
    if overlap:
        print("OVERLAP:", ", ".join(overlap))
    print("Outputs:", args.out_dir)

if __name__ == "__main__":
    main()
