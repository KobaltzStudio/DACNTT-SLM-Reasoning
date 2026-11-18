import argparse
import ast
import csv
import importlib.util
import json
from pathlib import Path

CAPABILITIES = [
    "addition",
    "subtraction",
    "multiplication",
    "division",
    "percentage",
    "fraction",
    "ratio",
]


def load_extractor(path):
    spec = importlib.util.spec_from_file_location(
        "capability_extractor_eval_v31",
        path,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load extractor: {path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_labels(value):
    if value is None:
        return []

    if isinstance(value, list):
        return sorted(set(str(x).strip() for x in value if str(x).strip()))

    value = str(value).strip()

    if not value:
        return []

    # JSON list, e.g. ["multiplication", "percentage"]
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return sorted(set(str(x).strip() for x in parsed if str(x).strip()))
    except (json.JSONDecodeError, TypeError):
        pass

    # Python list representation, e.g. ['multiplication', 'percentage']
    try:
        parsed = ast.literal_eval(value)
        if isinstance(parsed, (list, tuple, set)):
            return sorted(set(str(x).strip() for x in parsed if str(x).strip()))
    except (ValueError, SyntaxError):
        pass

    # Fallback: comma-separated labels.
    return sorted(set(x.strip() for x in value.split(",") if x.strip()))


def calculate_metrics(gold_sets, predicted_sets):
    total = len(gold_sets)

    exact_matches = sum(
        gold == predicted
        for gold, predicted in zip(gold_sets, predicted_sets)
    )

    per_capability = {}

    total_tp = 0
    total_fp = 0
    total_fn = 0

    macro_precision = []
    macro_recall = []
    macro_f1 = []

    for capability in CAPABILITIES:
        tp = sum(
            capability in gold and capability in predicted
            for gold, predicted in zip(gold_sets, predicted_sets)
        )

        fp = sum(
            capability not in gold and capability in predicted
            for gold, predicted in zip(gold_sets, predicted_sets)
        )

        fn = sum(
            capability in gold and capability not in predicted
            for gold, predicted in zip(gold_sets, predicted_sets)
        )

        tn = total - tp - fp - fn

        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if precision + recall
            else 0.0
        )

        per_capability[capability] = {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "tn": tn,
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }

        total_tp += tp
        total_fp += fp
        total_fn += fn

        macro_precision.append(precision)
        macro_recall.append(recall)
        macro_f1.append(f1)

    micro_precision = (
        total_tp / (total_tp + total_fp)
        if total_tp + total_fp else 0.0
    )

    micro_recall = (
        total_tp / (total_tp + total_fn)
        if total_tp + total_fn else 0.0
    )

    micro_f1 = (
        2 * micro_precision * micro_recall
        / (micro_precision + micro_recall)
        if micro_precision + micro_recall else 0.0
    )

    return {
        "sample_count": total,
        "exact_match_count": exact_matches,
        "exact_match_rate": exact_matches / total if total else 0.0,
        "micro": {
            "tp": total_tp,
            "fp": total_fp,
            "fn": total_fn,
            "precision": micro_precision,
            "recall": micro_recall,
            "f1": micro_f1,
        },
        "macro": {
            "precision": (
                sum(macro_precision) / len(macro_precision)
                if macro_precision else 0.0
            ),
            "recall": (
                sum(macro_recall) / len(macro_recall)
                if macro_recall else 0.0
            ),
            "f1": (
                sum(macro_f1) / len(macro_f1)
                if macro_f1 else 0.0
            ),
        },
        "per_capability": per_capability,
    }


def write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--extractor", required=True)
    parser.add_argument("--rules-v3", required=True)
    parser.add_argument("--rules-v3-1", required=True)
    parser.add_argument("--approved-csv", required=True)
    parser.add_argument("--v3-predictions", required=True)
    parser.add_argument("--out-dir", required=True)

    args = parser.parse_args()

    extractor_path = Path(args.extractor)
    rules_v3_path = Path(args.rules_v3)
    rules_v31_path = Path(args.rules_v3_1)
    approved_path = Path(args.approved_csv)
    baseline_path = Path(args.v3_predictions)
    out_dir = Path(args.out_dir)

    for path in (
        extractor_path,
        rules_v3_path,
        rules_v31_path,
        approved_path,
        baseline_path,
    ):
        if not path.exists():
            raise FileNotFoundError(path)

    extractor = load_extractor(extractor_path)

    rules_v3 = json.loads(rules_v3_path.read_text(encoding="utf-8-sig"))
    rules_v31 = json.loads(rules_v31_path.read_text(encoding="utf-8-sig"))

    if rules_v3.get("schema_version") != "v3":
        raise ValueError("The baseline rules file is not schema v3.")

    if rules_v31.get("schema_version") != "v3.1":
        raise ValueError("The candidate rules file is not schema v3.1.")

    compiled_v3 = extractor.compile_rules(rules_v3)
    compiled_v31 = extractor.compile_rules(rules_v31)

    with approved_path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        approved_rows = list(csv.DictReader(f))

    with baseline_path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        baseline_rows = list(csv.DictReader(f))

    if len(approved_rows) != 170:
        raise ValueError(
            f"Expected 170 approved rows, found {len(approved_rows)}"
        )

    baseline_by_id = {
        row["problem_id"]: row
        for row in baseline_rows
    }

    if len(baseline_by_id) != len(baseline_rows):
        raise ValueError("Duplicate problem_id in v3 baseline predictions.")

    required_approved = {
        "problem_id",
        "question",
        "gold_capabilities",
    }

    missing_columns = required_approved - set(approved_rows[0].keys())

    if missing_columns:
        raise ValueError(
            f"Approved CSV missing columns: {sorted(missing_columns)}"
        )

    if not baseline_rows:
        raise ValueError("v3 baseline prediction CSV is empty.")

    if "v3_predictions" not in baseline_rows[0]:
        raise ValueError(
            "Baseline CSV does not contain the v3_predictions column."
        )

    prediction_rows = []
    gold_sets = []
    v31_sets = []
    v3_sets = []

    false_negative_rows = []
    false_positive_rows = []
    change_rows = []

    for row in approved_rows:
        problem_id = row["problem_id"]
        question = row["question"]

        gold = set(parse_labels(row["gold_capabilities"]))

        unknown_gold = gold - set(CAPABILITIES)
        if unknown_gold:
            raise ValueError(
                f"{problem_id}: unknown Gold labels: {sorted(unknown_gold)}"
            )

        predicted, evidence, fired = extractor.extract_capabilities(
            question,
            compiled_v31,
        )

        predicted_v31 = set(predicted)

        unknown_predicted = predicted_v31 - set(CAPABILITIES)
        if unknown_predicted:
            raise ValueError(
                f"{problem_id}: unknown predictions: {sorted(unknown_predicted)}"
            )

        baseline = baseline_by_id.get(problem_id)

        if baseline is None:
            raise ValueError(
                f"Missing v3 baseline prediction for {problem_id}"
            )

        predicted_v3 = set(parse_labels(baseline["v3_predictions"]))

        gold_sets.append(gold)
        v31_sets.append(predicted_v31)
        v3_sets.append(predicted_v3)

        missing = gold - predicted_v31
        unexpected = predicted_v31 - gold

        prediction_rows.append({
            "problem_id": problem_id,
            "gold_capabilities": json.dumps(sorted(gold)),
            "v3_predictions": json.dumps(sorted(predicted_v3)),
            "v3_1_predictions": json.dumps(sorted(predicted_v31)),
            "missing_expected": json.dumps(sorted(missing)),
            "unexpected_predictions": json.dumps(sorted(unexpected)),
            "exact_match": gold == predicted_v31,
        })

        if missing:
            false_negative_rows.append({
                "problem_id": problem_id,
                "question": question,
                "gold_capabilities": json.dumps(sorted(gold)),
                "v3_1_predictions": json.dumps(sorted(predicted_v31)),
                "missing_capabilities": json.dumps(sorted(missing)),
            })

        if unexpected:
            false_positive_rows.append({
                "problem_id": problem_id,
                "question": question,
                "gold_capabilities": json.dumps(sorted(gold)),
                "v3_1_predictions": json.dumps(sorted(predicted_v31)),
                "unexpected_capabilities": json.dumps(sorted(unexpected)),
            })

        if predicted_v3 != predicted_v31:
            change_rows.append({
                "problem_id": problem_id,
                "gold_capabilities": json.dumps(sorted(gold)),
                "v3_predictions": json.dumps(sorted(predicted_v3)),
                "v3_1_predictions": json.dumps(sorted(predicted_v31)),
                "added_in_v3_1": json.dumps(
                    sorted(predicted_v31 - predicted_v3)
                ),
                "removed_in_v3_1": json.dumps(
                    sorted(predicted_v3 - predicted_v31)
                ),
            })

    metrics_v31 = calculate_metrics(gold_sets, v31_sets)
    metrics_v3 = calculate_metrics(gold_sets, v3_sets)

    metrics = {
        "evaluation_name": "v3.1 interim approved170 evaluation",
        "rules_version": "v3.1",
        "dataset": str(approved_path),
        "baseline_predictions": str(baseline_path),
        "sample_count": len(approved_rows),
        "v3_metrics": metrics_v3,
        "v3_1_metrics": metrics_v31,
        "interpretation": [
            "The 170 samples are an approved/review set, not an independent test set.",
            "The extractor uses question text; it does not inspect Teacher solution traces.",
            "Gold annotation uncertainty must be considered separately.",
            "This is an interim evaluation while N01/N02 strict regression remains unresolved.",
        ],
    }

    out_dir.mkdir(parents=True, exist_ok=True)

    write_csv(
        out_dir / "predictions_v3_1_all170.csv",
        prediction_rows,
        [
            "problem_id",
            "gold_capabilities",
            "v3_predictions",
            "v3_1_predictions",
            "missing_expected",
            "unexpected_predictions",
            "exact_match",
        ],
    )

    write_csv(
        out_dir / "false_negatives_v3_1.csv",
        false_negative_rows,
        [
            "problem_id",
            "question",
            "gold_capabilities",
            "v3_1_predictions",
            "missing_capabilities",
        ],
    )

    write_csv(
        out_dir / "false_positives_v3_1.csv",
        false_positive_rows,
        [
            "problem_id",
            "question",
            "gold_capabilities",
            "v3_1_predictions",
            "unexpected_capabilities",
        ],
    )

    write_csv(
        out_dir / "prediction_changes_v3_vs_v3_1.csv",
        change_rows,
        [
            "problem_id",
            "gold_capabilities",
            "v3_predictions",
            "v3_1_predictions",
            "added_in_v3_1",
            "removed_in_v3_1",
        ],
    )

    metrics_path = out_dir / "metrics_v3_1_approved170.json"
    metrics_path.write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("Evaluation completed.")
    print("Samples:", len(approved_rows))
    print(
        "v3 exact match:",
        f"{metrics_v3['exact_match_count']}/{metrics_v3['sample_count']}",
        f"({metrics_v3['exact_match_rate']:.4f})",
    )
    print(
        "v3.1 exact match:",
        f"{metrics_v31['exact_match_count']}/{metrics_v31['sample_count']}",
        f"({metrics_v31['exact_match_rate']:.4f})",
    )

    print("\nv3.1 micro:")
    for key, value in metrics_v31["micro"].items():
        print(f"  {key}: {value}")

    print("\nv3.1 per capability:")
    for capability, values in metrics_v31["per_capability"].items():
        print(
            f"  {capability}: "
            f"TP={values['tp']} FP={values['fp']} "
            f"FN={values['fn']} TN={values['tn']} "
            f"P={values['precision']:.4f} "
            f"R={values['recall']:.4f} "
            f"F1={values['f1']:.4f}"
        )

    print("\nFalse negatives:", len(false_negative_rows))
    print("False positives:", len(false_positive_rows))
    print("Prediction changes:", len(change_rows))

    print("\nCreated:")
    print(out_dir / "predictions_v3_1_all170.csv")
    print(metrics_path)
    print(out_dir / "false_negatives_v3_1.csv")
    print(out_dir / "false_positives_v3_1.csv")
    print(out_dir / "prediction_changes_v3_vs_v3_1.csv")


if __name__ == "__main__":
    main()
