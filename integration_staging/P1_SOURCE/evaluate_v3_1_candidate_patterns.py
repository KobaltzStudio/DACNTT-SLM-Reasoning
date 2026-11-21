import argparse
import ast
import copy
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

CANDIDATE_PATTERNS = {
    "multiplication": (
        r"(?<!\w)\d+(?:\.\d+)?\s*%\s+of\b"
    ),
    "subtraction": (
        r"\bwhat\s+percentage\s+of\b[^.!?]*"
        r"\b(?:not|aren't|isn't|wasn't|weren't|doesn't|"
        r"don't|didn't|can't|cannot)\b"
    ),
}


def load_extractor(path):
    spec = importlib.util.spec_from_file_location(
        "candidate_pattern_evaluator",
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

    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return sorted(set(str(x).strip() for x in parsed if str(x).strip()))
    except (json.JSONDecodeError, TypeError):
        pass

    try:
        parsed = ast.literal_eval(value)
        if isinstance(parsed, (list, tuple, set)):
            return sorted(set(str(x).strip() for x in parsed if str(x).strip()))
    except (ValueError, SyntaxError):
        pass

    return sorted(set(x.strip() for x in value.split(",") if x.strip()))


def calculate_metrics(gold_sets, predicted_sets):
    total = len(gold_sets)

    exact = sum(
        gold == predicted
        for gold, predicted in zip(gold_sets, predicted_sets)
    )

    result = {
        "sample_count": total,
        "exact_match_count": exact,
        "exact_match_rate": exact / total if total else 0.0,
        "per_capability": {},
    }

    total_tp = 0
    total_fp = 0
    total_fn = 0

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
            if precision + recall else 0.0
        )

        result["per_capability"][capability] = {
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

    result["micro"] = {
        "tp": total_tp,
        "fp": total_fp,
        "fn": total_fn,
        "precision": micro_precision,
        "recall": micro_recall,
        "f1": micro_f1,
    }

    return result


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--extractor", required=True)
    parser.add_argument("--rules", required=True)
    parser.add_argument("--approved-csv", required=True)
    parser.add_argument("--negative-cases", required=True)
    parser.add_argument("--out-dir", required=True)

    args = parser.parse_args()

    extractor_path = Path(args.extractor)
    rules_path = Path(args.rules)
    approved_path = Path(args.approved_csv)
    negative_path = Path(args.negative_cases)
    out_dir = Path(args.out_dir)

    for path in (
        extractor_path,
        rules_path,
        approved_path,
        negative_path,
    ):
        if not path.exists():
            raise FileNotFoundError(path)

    extractor = load_extractor(extractor_path)

    original_rules = json.loads(
        rules_path.read_text(encoding="utf-8-sig")
    )

    if original_rules.get("schema_version") != "v3.1":
        raise ValueError("Expected schema_version=v3.1")

    # Create an in-memory copy. Never modify the source JSON.
    candidate_rules = copy.deepcopy(original_rules)

    for capability, pattern in CANDIDATE_PATTERNS.items():
        patterns = candidate_rules["rules"][capability].setdefault(
            "patterns",
            [],
        )

        if pattern not in patterns:
            patterns.append(pattern)

    compiled_original = extractor.compile_rules(original_rules)
    compiled_candidate = extractor.compile_rules(candidate_rules)

    with approved_path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        approved_rows = list(csv.DictReader(f))

    if len(approved_rows) != 170:
        raise ValueError(
            f"Expected 170 approved samples, got {len(approved_rows)}"
        )

    with negative_path.open("r", encoding="utf-8-sig") as f:
        negative_cases = [
            json.loads(line)
            for line in f
            if line.strip()
        ]

    gold_sets = []
    original_sets = []
    candidate_sets = []

    change_rows = []
    prediction_rows = []

    for row in approved_rows:
        problem_id = row["problem_id"]
        question = row["question"]

        gold = set(parse_labels(row["gold_capabilities"]))

        original_pred, _, _ = extractor.extract_capabilities(
            question,
            compiled_original,
        )

        candidate_pred, _, fired = extractor.extract_capabilities(
            question,
            compiled_candidate,
        )

        original = set(original_pred)
        candidate = set(candidate_pred)

        gold_sets.append(gold)
        original_sets.append(original)
        candidate_sets.append(candidate)

        added = candidate - original
        removed = original - candidate

        prediction_rows.append({
            "problem_id": problem_id,
            "gold": json.dumps(sorted(gold)),
            "original_v3_1": json.dumps(sorted(original)),
            "candidate_predictions": json.dumps(sorted(candidate)),
            "added": json.dumps(sorted(added)),
            "removed": json.dumps(sorted(removed)),
            "exact_match": gold == candidate,
        })

        if added or removed:
            change_rows.append({
                "problem_id": problem_id,
                "question": question,
                "gold": json.dumps(sorted(gold)),
                "original_v3_1": json.dumps(sorted(original)),
                "candidate_predictions": json.dumps(sorted(candidate)),
                "added": json.dumps(sorted(added)),
                "removed": json.dumps(sorted(removed)),
                "new_false_positive": json.dumps(sorted(added - gold)),
                "fixed_false_negative": json.dumps(sorted(added & gold)),
            })

    original_metrics = calculate_metrics(gold_sets, original_sets)
    candidate_metrics = calculate_metrics(gold_sets, candidate_sets)

    negative_results = []

    for case in negative_cases:
        original_pred, _, _ = extractor.extract_capabilities(
            case["question"],
            compiled_original,
        )

        candidate_pred, _, _ = extractor.extract_capabilities(
            case["question"],
            compiled_candidate,
        )

        expected = set(parse_labels(case["expected_capabilities"]))
        forbidden = set(parse_labels(case["must_not_include"]))
        candidate = set(candidate_pred)

        missing = expected - candidate
        unexpected = candidate - expected
        forbidden_found = candidate & forbidden

        exact = candidate == expected
        passed = not missing and not forbidden_found and not unexpected

        negative_results.append({
            "test_id": case["test_id"],
            "expected": json.dumps(sorted(expected)),
            "original_predictions": json.dumps(sorted(original_pred)),
            "candidate_predictions": json.dumps(sorted(candidate)),
            "missing": json.dumps(sorted(missing)),
            "unexpected": json.dumps(sorted(unexpected)),
            "forbidden_found": json.dumps(sorted(forbidden_found)),
            "exact_match": exact,
            "test_pass": passed,
        })

    out_dir.mkdir(parents=True, exist_ok=True)

    write_csv(
        out_dir / "candidate_predictions_all170.csv",
        prediction_rows,
        [
            "problem_id",
            "gold",
            "original_v3_1",
            "candidate_predictions",
            "added",
            "removed",
            "exact_match",
        ],
    )

    write_csv(
        out_dir / "candidate_changes_170.csv",
        change_rows,
        [
            "problem_id",
            "question",
            "gold",
            "original_v3_1",
            "candidate_predictions",
            "added",
            "removed",
            "new_false_positive",
            "fixed_false_negative",
        ],
    )

    write_csv(
        out_dir / "candidate_negative_regression.csv",
        negative_results,
        [
            "test_id",
            "expected",
            "original_predictions",
            "candidate_predictions",
            "missing",
            "unexpected",
            "forbidden_found",
            "exact_match",
            "test_pass",
        ],
    )

    metrics = {
        "evaluation": "candidate pattern simulation",
        "source_config": str(rules_path),
        "source_config_modified": False,
        "candidate_patterns": CANDIDATE_PATTERNS,
        "original_metrics": original_metrics,
        "candidate_metrics": candidate_metrics,
        "negative_regression": negative_results,
        "interpretation": [
            "Candidate patterns were added only to an in-memory copy.",
            "The official v3.1 JSON was not modified.",
            "The 170 samples are an approved/review set, not an independent test set.",
            "Review new false positives and fixed false negatives before accepting patterns.",
        ],
    }

    metrics_path = out_dir / "candidate_metrics.json"

    metrics_path.write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("=" * 90)
    print("CANDIDATE PATTERN EVALUATION")
    print("=" * 90)

    print("\nCandidate patterns:")
    for capability, pattern in CANDIDATE_PATTERNS.items():
        print(capability, "=>", pattern)

    print("\nOriginal v3.1:")
    print(
        "Exact match:",
        f"{original_metrics['exact_match_count']}/170",
        f"({original_metrics['exact_match_rate']:.4f})",
    )
    print("Micro:", original_metrics["micro"])

    print("\nCandidate:")
    print(
        "Exact match:",
        f"{candidate_metrics['exact_match_count']}/170",
        f"({candidate_metrics['exact_match_rate']:.4f})",
    )
    print("Micro:", candidate_metrics["micro"])

    print("\nPer-capability candidate metrics:")
    for capability, values in candidate_metrics["per_capability"].items():
        print(
            capability,
            f"TP={values['tp']}",
            f"FP={values['fp']}",
            f"FN={values['fn']}",
            f"P={values['precision']:.4f}",
            f"R={values['recall']:.4f}",
            f"F1={values['f1']:.4f}",
        )

    print("\nNegative regression:")
    for result in negative_results:
        print(
            result["test_id"],
            "| predicted =", result["candidate_predictions"],
            "| missing =", result["missing"],
            "| forbidden =", result["forbidden_found"],
            "| exact =", result["exact_match"],
            "| PASS =", result["test_pass"],
        )

    print("\nChanged samples:", len(change_rows))

    new_fp_count = sum(
        bool(parse_labels(row["new_false_positive"]))
        for row in change_rows
    )

    fixed_fn_count = sum(
        bool(parse_labels(row["fixed_false_negative"]))
        for row in change_rows
    )

    print("Rows with new false positives:", new_fp_count)
    print("Rows with fixed false negatives:", fixed_fn_count)

    print("\nCreated:")
    print(out_dir / "candidate_predictions_all170.csv")
    print(out_dir / "candidate_changes_170.csv")
    print(out_dir / "candidate_negative_regression.csv")
    print(metrics_path)

    print("\nOfficial v3.1 config modified: NO")


if __name__ == "__main__":
    main()
