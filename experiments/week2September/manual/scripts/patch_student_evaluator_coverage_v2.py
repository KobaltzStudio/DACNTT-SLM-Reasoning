from pathlib import Path

path = Path(
    r"C:\KLTN-SLM-Reasoning\experiments\week2September\manual"
    r"\scripts\evaluate_student_capabilities.py"
)

source = path.read_text(encoding="utf-8-sig")

helper = '''def calculate_coverage(
    gold_ids: set[str],
    prediction_ids: set[str],
    dev_ids: set[str],
) -> dict:
    return {
        "prediction_ids_outside_d_dev": sorted(prediction_ids - dev_ids),
        "missing_prediction_ids": sorted(gold_ids - prediction_ids),
        "predictions_without_confirmed_gold": sorted(prediction_ids - gold_ids),
        "matched_ids": sorted(gold_ids & prediction_ids),
    }


'''

if "def calculate_coverage(" in source:
    print("PATCH_STATUS: ALREADY_PRESENT")
else:
    anchor = "def assert_unique_ids(rows: list[dict], source: str) -> None:\n"

    if anchor not in source:
        raise SystemExit("PATCH_FAILED: assert_unique_ids anchor not found")

    source = source.replace(anchor, helper + anchor, 1)

    # Replace the existing inline coverage calculations.
    old = '''    gold_ids = {row["problem_id"] for row in gold_rows}
    matched_ids = sorted(gold_ids & prediction_ids)
    missing_prediction_ids = sorted(gold_ids - prediction_ids)
    predictions_without_confirmed_gold = sorted(prediction_ids - gold_ids)
'''

    new = '''    gold_ids = {row["problem_id"] for row in gold_rows}
    coverage_sets = calculate_coverage(
        gold_ids=gold_ids,
        prediction_ids=prediction_ids,
        dev_ids=dev_ids,
    )

    matched_ids = coverage_sets["matched_ids"]
    missing_prediction_ids = coverage_sets["missing_prediction_ids"]
    predictions_without_confirmed_gold = coverage_sets[
        "predictions_without_confirmed_gold"
    ]
'''

    if old not in source:
        raise SystemExit("PATCH_FAILED: original coverage block not found")

    source = source.replace(old, new, 1)

    # Keep the original explicit D_dev validation, but use the helper result.
    old_scope = '''    predictions_outside_dev = sorted(prediction_ids - dev_ids)
'''
    new_scope = '''    predictions_outside_dev = coverage_sets["prediction_ids_outside_d_dev"]
'''

    if old_scope not in source:
        raise SystemExit("PATCH_FAILED: original D_dev scope block not found")

    source = source.replace(old_scope, new_scope, 1)

    # Do not pass an invalid newline argument to Path.write_text().
    path.write_text(source, encoding="utf-8")

    # Verify the written file can be parsed and contains the helper.
    import ast
    written = path.read_text(encoding="utf-8")
    ast.parse(written)

    if "def calculate_coverage(" not in written:
        raise SystemExit("PATCH_FAILED: helper missing after write")

    print("PATCH_STATUS: PASS")
    print("PATCHED_FILE:", path)
