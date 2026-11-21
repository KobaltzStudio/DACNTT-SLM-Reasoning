from pathlib import Path

path = Path(r"C:\KLTN-SLM-Reasoning\experiments\week2September\manual\scripts\evaluate_student_capabilities.py")
source = path.read_text(encoding="utf-8-sig")

anchor = '''def assert_unique_ids(rows: list[dict], source: str) -> None:
'''

helper = '''def calculate_coverage(
    gold_ids: set[str],
    prediction_ids: set[str],
    dev_ids: set[str],
) -> dict:
    outside_dev = sorted(prediction_ids - dev_ids)
    missing_predictions = sorted(gold_ids - prediction_ids)
    predictions_without_gold = sorted(prediction_ids - gold_ids)

    return {
        "prediction_ids_outside_d_dev": outside_dev,
        "missing_prediction_ids": missing_predictions,
        "predictions_without_confirmed_gold": predictions_without_gold,
        "matched_ids": sorted(gold_ids & prediction_ids),
    }


'''

if "def calculate_coverage(" not in source:
    if anchor not in source:
        raise SystemExit("PATCH_FAILED: insertion anchor not found")
    source = source.replace(anchor, helper + anchor, 1)

old = '''    predictions_outside_dev = sorted(prediction_ids - dev_ids)
    if predictions_outside_dev:
        raise ValueError(
            "Prediction IDs outside D_dev: "
            + repr(predictions_outside_dev[:30])
        )
'''

new = '''    coverage_sets = calculate_coverage(
        gold_ids={row["problem_id"] for row in gold_rows},
        prediction_ids=prediction_ids,
        dev_ids=dev_ids,
    )
    predictions_outside_dev = coverage_sets["prediction_ids_outside_d_dev"]
    if predictions_outside_dev:
        raise ValueError(
            "Prediction IDs outside D_dev: "
            + repr(predictions_outside_dev[:30])
        )
'''

if old in source:
    source = source.replace(old, new, 1)
elif "coverage_sets = calculate_coverage(" not in source:
    raise SystemExit("PATCH_FAILED: prediction-scope block not found")

old = '''    gold_ids = {row["problem_id"] for row in gold_rows}
    matched_ids = sorted(gold_ids & prediction_ids)
    missing_prediction_ids = sorted(gold_ids - prediction_ids)
    predictions_without_confirmed_gold = sorted(prediction_ids - gold_ids)
'''

new = '''    gold_ids = {row["problem_id"] for row in gold_rows}
    matched_ids = coverage_sets["matched_ids"]
    missing_prediction_ids = coverage_sets["missing_prediction_ids"]
    predictions_without_confirmed_gold = coverage_sets[
        "predictions_without_confirmed_gold"
    ]
'''

if old in source:
    source = source.replace(old, new, 1)
elif "matched_ids = coverage_sets[\\\"matched_ids\\\"]" not in source:
    raise SystemExit("PATCH_FAILED: coverage calculation block not found")

path.write_text(source, encoding="utf-8", newline="\\n")
print("PATCH_STATUS: PASS")
