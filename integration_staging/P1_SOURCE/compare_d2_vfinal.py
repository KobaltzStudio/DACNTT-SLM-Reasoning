import csv
import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]

D2_REPORT = (
    BASE / "reports" / "capability" / "d2_regression"
    / "extractor_baseline.json"
)

D3_REPORT = (
    BASE / "reports" / "capability" / "d3_final_regression"
    / "extractor_vfinal_metrics.json"
)

FINAL_DIR = BASE / "reports" / "capability" / "d3_final_regression"

INPUT_FILE = FINAL_DIR / "gold_evaluation_input.jsonl"
PREDICTIONS_FILE = FINAL_DIR / "extractor_predictions.jsonl"
EVIDENCE_FILE = FINAL_DIR / "extractor_evidence.jsonl"

COMPARISON_CSV = FINAL_DIR / "d2_vfinal_comparison.csv"
COMPARISON_JSON = FINAL_DIR / "d2_vfinal_comparison.json"
ERROR_CSV = FINAL_DIR / "error_analysis.csv"

CAPABILITIES = [
    "addition", "subtraction", "multiplication",
    "division", "percentage", "fraction", "ratio",
]


def load_json(path):
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


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
                    f"Invalid JSON: {path}:{line_no}"
                ) from exc
    return rows


def metric_value(report, key):
    if key == "micro_precision":
        return report["micro"]["precision"]
    if key == "micro_recall":
        return report["micro"]["recall"]
    if key == "micro_f1":
        return report["micro"]["f1"]
    if key == "macro_f1":
        return report["macro_f1"]
    if key == "exact_match_rate":
        return report["exact_match_rate"]
    raise KeyError(key)


def index_by_id(rows, label):
    result = {}

    for row in rows:
        problem_id = row["problem_id"]
        if problem_id in result:
            raise ValueError(f"Duplicate {label} ID: {problem_id}")
        result[problem_id] = row

    return result


def main():
    d2 = load_json(D2_REPORT)
    d3 = load_json(D3_REPORT)

    if d2["gold_records"] != 185:
        raise ValueError("D2 baseline does not contain 185 Gold records")

    if d3["gold_records"] != 185 or d3["prediction_records"] != 185:
        raise ValueError("D3 vFinal does not contain 185 records")

    aggregate_keys = [
        "micro_precision",
        "micro_recall",
        "micro_f1",
        "macro_f1",
        "exact_match_rate",
    ]

    comparison_rows = []

    for key in aggregate_keys:
        d2_value = metric_value(d2, key)
        d3_value = metric_value(d3, key)

        delta = (
            d3_value - d2_value
            if d2_value is not None and d3_value is not None
            else None
        )

        comparison_rows.append({
            "level": "aggregate",
            "metric": key,
            "capability": "",
            "d2": d2_value,
            "d3_vfinal": d3_value,
            "delta_vfinal_minus_d2": delta,
        })

    for cap in CAPABILITIES:
        d2_metric = d2["capabilities"][cap]
        d3_metric = d3["capabilities"][cap]

        for metric in [
            "support", "TP", "FP", "FN",
            "precision", "recall", "f1",
        ]:
            d2_value = d2_metric[metric]
            d3_value = d3_metric[metric]

            delta = (
                d3_value - d2_value
                if isinstance(d2_value, (int, float))
                and isinstance(d3_value, (int, float))
                else None
            )

            comparison_rows.append({
                "level": "capability",
                "metric": metric,
                "capability": cap,
                "d2": d2_value,
                "d3_vfinal": d3_value,
                "delta_vfinal_minus_d2": delta,
            })

    with COMPARISON_CSV.open(
        "w", newline="", encoding="utf-8-sig"
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "level", "metric", "capability",
                "d2", "d3_vfinal", "delta_vfinal_minus_d2",
            ],
        )
        writer.writeheader()
        writer.writerows(comparison_rows)

    comparison_json = {
        "comparison": "D2 Gold v2 vs D3 Gold vFinal",
        "interpretation": (
            "The extractor implementation and capability_rules_v2.json "
            "are held constant. Metric differences reflect evaluation "
            "against different Gold annotation versions and must not be "
            "interpreted as extractor improvement."
        ),
        "d2_gold_records": d2["gold_records"],
        "d3_vfinal_gold_records": d3["gold_records"],
        "d3_vfinal_gold_status": d3["gold_status"],
        "aggregate": comparison_rows[:len(aggregate_keys)],
        "per_capability": comparison_rows[len(aggregate_keys):],
    }

    COMPARISON_JSON.write_text(
        json.dumps(comparison_json, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    inputs = load_jsonl(INPUT_FILE)
    predictions = load_jsonl(PREDICTIONS_FILE)
    evidence_rows = load_jsonl(EVIDENCE_FILE)

    input_by_id = index_by_id(inputs, "input")
    prediction_by_id = index_by_id(predictions, "prediction")
    evidence_by_id = index_by_id(evidence_rows, "evidence")

    expected_ids = set(input_by_id)

    if (
        expected_ids != set(prediction_by_id)
        or expected_ids != set(evidence_by_id)
    ):
        raise ValueError("Input/prediction/evidence ID mismatch")

    if len(expected_ids) != 185:
        raise ValueError("Expected 185 unique final problem IDs")

    error_rows = []

    for problem_id, input_row in input_by_id.items():
        gold = set(input_row["gold_capabilities"])
        predicted = set(
            prediction_by_id[problem_id]["predicted_capabilities"]
        )

        false_negatives = sorted(gold - predicted)
        false_positives = sorted(predicted - gold)

        if not false_negatives and not false_positives:
            continue

        evidence = evidence_by_id[problem_id]

        error_rows.append({
            "problem_id": problem_id,
            "question": input_row["question"],
            "gold_capabilities": json.dumps(
                sorted(gold), ensure_ascii=False
            ),
            "predicted_capabilities": json.dumps(
                sorted(predicted), ensure_ascii=False
            ),
            "false_negatives": json.dumps(
                false_negatives, ensure_ascii=False
            ),
            "false_positives": json.dumps(
                false_positives, ensure_ascii=False
            ),
            "exact_match": False,
            "evidence": json.dumps(
                evidence.get("evidence", {}),
                ensure_ascii=False,
            ),
            "rules_fired": json.dumps(
                evidence.get("rules_fired", {}),
                ensure_ascii=False,
            ),
        })

    error_fields = [
        "problem_id", "question", "gold_capabilities",
        "predicted_capabilities", "false_negatives",
        "false_positives", "exact_match", "evidence",
        "rules_fired",
    ]

    with ERROR_CSV.open(
        "w", newline="", encoding="utf-8-sig"
    ) as f:
        writer = csv.DictWriter(f, fieldnames=error_fields)
        writer.writeheader()
        writer.writerows(error_rows)

    print("D2 VS D3 VFINAL COMPARISON")
    print(f"D2 Gold records: {d2['gold_records']}")
    print(f"D3 vFinal Gold records: {d3['gold_records']}")
    print(f"Comparison rows: {len(comparison_rows)}")
    print(f"D3 vFinal error records: {len(error_rows)}")
    print(f"Comparison CSV: {COMPARISON_CSV}")
    print(f"Comparison JSON: {COMPARISON_JSON}")
    print(f"Error analysis CSV: {ERROR_CSV}")
    print("[PASS]")


if __name__ == "__main__":
    main()
