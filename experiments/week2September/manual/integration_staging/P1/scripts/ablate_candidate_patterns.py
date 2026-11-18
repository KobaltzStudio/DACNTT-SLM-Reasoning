import copy
import csv
import importlib.util
import json
from pathlib import Path

MANUAL = Path("experiments/week2September/manual")

EXTRACTOR_PATH = MANUAL / "scripts/extract_capabilities_rule_based.py"
RULES_PATH = MANUAL / "config/capability_rules_v3.1.json"
APPROVED_PATH = (
    MANUAL
    / "reports/capability/p1_day14_final_2026-11-14/approved/"
    / "priority_error_review_170_approved.csv"
)

PATTERNS = {
    "multiplication": r"(?<!\w)\d+(?:\.\d+)?\s*%\s+of\b",
    "subtraction": (
        r"\bwhat\s+percentage\s+of\b[^.!?]*"
        r"\b(?:not|aren't|isn't|wasn't|weren't|doesn't|"
        r"don't|didn't|can't|cannot)\b"
    ),
}


def load_extractor():
    spec = importlib.util.spec_from_file_location(
        "candidate_ablation",
        EXTRACTOR_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load extractor.")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def evaluate(extractor, rules, rows):
    compiled = extractor.compile_rules(rules)

    changed = []
    added_fp = []
    fixed_fn = []

    for row in rows:
        gold = set(json.loads(row["gold_capabilities"]))

        predicted, _, _ = extractor.extract_capabilities(
            row["question"],
            compiled,
        )

        predicted = set(predicted)

        missing = gold - predicted
        unexpected = predicted - gold

        if missing or unexpected:
            changed.append(row["problem_id"])

        if unexpected:
            added_fp.append({
                "problem_id": row["problem_id"],
                "unexpected": sorted(unexpected),
            })

        if missing:
            fixed_fn.append({
                "problem_id": row["problem_id"],
                "missing": sorted(missing),
            })

    return {
        "changed": changed,
        "false_positive_rows": added_fp,
        "false_negative_rows": fixed_fn,
    }


def main():
    extractor = load_extractor()

    original = json.loads(
        RULES_PATH.read_text(encoding="utf-8-sig")
    )

    with APPROVED_PATH.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        rows = list(csv.DictReader(f))

    if len(rows) != 170:
        raise ValueError(f"Expected 170 rows, got {len(rows)}")

    experiments = {
        "original_v3_1": [],
        "multiplication_only": ["multiplication"],
        "subtraction_only": ["subtraction"],
        "both_patterns": ["multiplication", "subtraction"],
    }

    for name, selected in experiments.items():
        rules = copy.deepcopy(original)

        for capability in selected:
            rules["rules"][capability]["patterns"].append(
                PATTERNS[capability]
            )

        result = evaluate(extractor, rules, rows)

        print("\n" + "=" * 90)
        print(name)
        print("=" * 90)

        print("Changed rows:", len(result["changed"]))
        print("Rows with false positives:", len(result["false_positive_rows"]))
        print("Rows with false negatives:", len(result["false_negative_rows"]))

        print("False positive details:")
        for item in result["false_positive_rows"]:
            print(item)

    print("\nAblation completed. Original config was not modified.")


if __name__ == "__main__":
    main()
