import csv
import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    BASE / "reports" / "capability" / "d3_final_regression"
    / "gold_evaluation_input.jsonl"
)

PREDICTIONS_FILE = (
    BASE / "reports" / "capability" / "d3_final_regression"
    / "extractor_predictions.jsonl"
)

OUTPUT_DIR = BASE / "reports" / "capability" / "d3_final_regression"

JSON_REPORT = OUTPUT_DIR / "extractor_vfinal_metrics.json"
CSV_REPORT = OUTPUT_DIR / "capability_metrics.csv"

CAPABILITIES = [
    "addition", "subtraction", "multiplication",
    "division", "percentage", "fraction", "ratio",
]


def load_jsonl(path):
    if not path.exists():
        raise FileNotFoundError(path)

    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON at {path}:{line_no}"
                ) from exc
    return rows


def safe_divide(numerator, denominator):
    return numerator / denominator if denominator else None


def calculate_metrics(tp, fp, fn, tn):
    support = tp + fn

    if support == 0:
        return {
            "support": 0,
            "TP": tp,
            "FP": fp,
            "FN": fn,
            "TN": tn,
            "precision": None,
            "recall": None,
            "f1": None,
            "status": "N/A_no_positive_gold",
        }

    precision = safe_divide(tp, tp + fp)
    recall = safe_divide(tp, tp + fn)

    if precision is None or recall is None:
        f1 = None
    elif precision + recall == 0:
        f1 = 0.0
    else:
        f1 = 2 * precision * recall / (precision + recall)

    return {
        "support": support,
        "TP": tp,
        "FP": fp,
        "FN": fn,
        "TN": tn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "status": "ok",
    }


def main():
    gold_records = load_jsonl(INPUT_FILE)
    prediction_records = load_jsonl(PREDICTIONS_FILE)

    gold = {}
    for row in gold_records:
        problem_id = row["problem_id"]

        if problem_id in gold:
            raise ValueError(f"Duplicate Gold ID: {problem_id}")

        labels = set(row["gold_capabilities"])
        unknown = labels - set(CAPABILITIES)

        if unknown:
            raise ValueError(
                f"Unknown Gold labels for {problem_id}: {sorted(unknown)}"
            )

        gold[problem_id] = labels

    predicted_by_id = {}
    for row in prediction_records:
        problem_id = row["problem_id"]

        if problem_id in predicted_by_id:
            raise ValueError(f"Duplicate prediction ID: {problem_id}")

        labels = set(row["predicted_capabilities"])
        unknown = labels - set(CAPABILITIES)

        if unknown:
            raise ValueError(
                f"Unknown predicted labels for {problem_id}: {sorted(unknown)}"
            )

        predicted_by_id[problem_id] = labels

    gold_ids = set(gold)
    prediction_ids = set(predicted_by_id)

    missing = sorted(gold_ids - prediction_ids)
    extra = sorted(prediction_ids - gold_ids)

    if missing or extra:
        raise ValueError(
            f"Gold/prediction ID mismatch. Missing={missing[:10]}, "
            f"Extra={extra[:10]}"
        )

    if len(gold) != 185:
        raise ValueError(f"Expected 185 Gold records, got {len(gold)}")

    counts = {
        cap: {"TP": 0, "FP": 0, "FN": 0, "TN": 0}
        for cap in CAPABILITIES
    }

    exact_matches = 0

    for problem_id, truth in gold.items():
        predicted = predicted_by_id[problem_id]

        if predicted == truth:
            exact_matches += 1

        for cap in CAPABILITIES:
            p = cap in predicted
            y = cap in truth

            if p and y:
                counts[cap]["TP"] += 1
            elif p and not y:
                counts[cap]["FP"] += 1
            elif not p and y:
                counts[cap]["FN"] += 1
            else:
                counts[cap]["TN"] += 1

    metrics = {
        cap: calculate_metrics(
            counts[cap]["TP"],
            counts[cap]["FP"],
            counts[cap]["FN"],
            counts[cap]["TN"],
        )
        for cap in CAPABILITIES
    }

    total_tp = sum(x["TP"] for x in counts.values())
    total_fp = sum(x["FP"] for x in counts.values())
    total_fn = sum(x["FN"] for x in counts.values())

    micro_precision = safe_divide(total_tp, total_tp + total_fp)
    micro_recall = safe_divide(total_tp, total_tp + total_fn)

    if micro_precision is None or micro_recall is None:
        micro_f1 = None
    elif micro_precision + micro_recall == 0:
        micro_f1 = 0.0
    else:
        micro_f1 = (
            2 * micro_precision * micro_recall
            / (micro_precision + micro_recall)
        )

    valid_f1 = [
        item["f1"] for item in metrics.values()
        if item["f1"] is not None
    ]

    macro_f1 = sum(valid_f1) / len(valid_f1) if valid_f1 else None
    exact_match_rate = exact_matches / len(gold)

    report = {
        "schema_version": "v1",
        "evaluation_unit": "problem",
        "gold_version": "vFinal",
        "gold_status": "project_team_confirmed",
        "human_confirmation_count": 22,
        "rules_file": "config/capability_rules_v2.json",
        "guideline_version": "v3",
        "gold_records": len(gold),
        "prediction_records": len(predicted_by_id),
        "unique_problem_ids": len(gold),
        "exact_matches": exact_matches,
        "exact_match_rate": exact_match_rate,
        "micro": {
            "TP": total_tp,
            "FP": total_fp,
            "FN": total_fn,
            "precision": micro_precision,
            "recall": micro_recall,
            "f1": micro_f1,
        },
        "macro_f1": macro_f1,
        "macro_f1_capabilities_included": len(valid_f1),
        "capabilities": metrics,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    JSON_REPORT.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    with CSV_REPORT.open(
        "w", newline="", encoding="utf-8-sig"
    ) as f:
        writer = csv.writer(f)
        writer.writerow([
            "capability", "support", "TP", "FP", "FN", "TN",
            "precision", "recall", "F1", "status",
        ])

        for cap in CAPABILITIES:
            m = metrics[cap]
            writer.writerow([
                cap, m["support"], m["TP"], m["FP"], m["FN"],
                m["TN"], m["precision"], m["recall"], m["f1"],
                m["status"],
            ])

    def fmt(value):
        return "N/A" if value is None else f"{value:.4f}"

    print("\nD3 FINAL EXTRACTOR EVALUATION - GOLD vFinal")
    print(f"Gold records: {len(gold)}")
    print(f"Prediction records: {len(predicted_by_id)}")
    print(f"Exact matches: {exact_matches}")
    print()
    print(
        f"{'Capability':<16}{'Support':>9}{'TP':>6}"
        f"{'FP':>6}{'FN':>6}{'P':>9}{'R':>9}{'F1':>9}"
    )

    for cap in CAPABILITIES:
        m = metrics[cap]
        print(
            f"{cap:<16}{m['support']:>9}{m['TP']:>6}"
            f"{m['FP']:>6}{m['FN']:>6}"
            f"{fmt(m['precision']):>9}{fmt(m['recall']):>9}"
            f"{fmt(m['f1']):>9}"
        )

    print()
    print(f"Micro Precision: {fmt(micro_precision)}")
    print(f"Micro Recall:    {fmt(micro_recall)}")
    print(f"Micro F1:        {fmt(micro_f1)}")
    print(f"Macro F1:        {fmt(macro_f1)}")
    print(f"Exact Match Rate:{exact_match_rate:.4f}")
    print(f"JSON report: {JSON_REPORT}")
    print(f"CSV report: {CSV_REPORT}")
    print("[PASS]")


if __name__ == "__main__":
    main()
