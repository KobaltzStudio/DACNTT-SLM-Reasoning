#!/usr/bin/env python3

import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(BASE / "scripts"))

from extract_capabilities_rule_based import (
    compile_rules,
    extract_capabilities,
)

RULES_FILE = BASE / "config" / "capability_rules_v3.json"

CASES_FILE = (
    BASE / "data" / "regression"
    / "capability_regression_cases_v1.jsonl"
)

RESULT_FILE = (
    BASE / "reports" / "capability" / "d2_regression"
    / "regression_test_results_v3.json"
)

CAPABILITIES = {
    "addition",
    "subtraction",
    "multiplication",
    "division",
    "percentage",
    "fraction",
    "ratio",
}


def load_jsonl(path):
    with path.open("r", encoding="utf-8") as f:
        return [
            json.loads(line)
            for line in f
            if line.strip()
        ]


RULE_DATA = json.loads(
    RULES_FILE.read_text(encoding="utf-8")
)

COMPILED_RULES = compile_rules(RULE_DATA)


def predict_capabilities(problem: str) -> set[str]:
    predictions, evidence, rules_fired = extract_capabilities(
        problem,
        COMPILED_RULES,
    )

    predicted = set(predictions)

    unknown = predicted - CAPABILITIES
    if unknown:
        raise ValueError(
            f"Extractor returned unknown labels: {unknown}"
        )

    return predicted


def main():
    cases = load_jsonl(CASES_FILE)

    results = []
    passed = 0

    for case in cases:
        expected = set(case["expected_capabilities"])
        forbidden = set(case["must_not_include"])

        predicted = predict_capabilities(case["problem"])

        exact_match = predicted == expected
        forbidden_clear = not (predicted & forbidden)

        success = exact_match and forbidden_clear

        if success:
            passed += 1

        results.append({
            "test_id": case["test_id"],
            "category": case["category"],
            "problem": case["problem"],
            "expected_capabilities": sorted(expected),
            "predicted_capabilities": sorted(predicted),
            "must_not_include": sorted(forbidden),
            "exact_match": exact_match,
            "forbidden_clear": forbidden_clear,
            "status": "PASS" if success else "FAIL",
            "missing": sorted(expected - predicted),
            "unexpected": sorted(predicted - expected),
        })

    failed = len(results) - passed

    RESULT_FILE.parent.mkdir(parents=True, exist_ok=True)

    report = {
        "schema_version": "v1",
        "evaluation": "D2 capability regression",
        "rules_version": "v3",
        "guideline_version": "v3",
        "total": len(results),
        "passed": passed,
        "failed": failed,
        "results": results,
    }

    RESULT_FILE.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("\nD2 CAPABILITY REGRESSION RESULTS")
    print(f"Total: {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    for row in results:
        if row["status"] == "FAIL":
            print(
                f"\n[{row['test_id']}] FAIL"
                f"\n  Expected: {row['expected_capabilities']}"
                f"\n  Predicted: {row['predicted_capabilities']}"
                f"\n  Missing: {row['missing']}"
                f"\n  Unexpected: {row['unexpected']}"
            )

    print(f"\nResults saved: {RESULT_FILE}")

    if failed:
        raise SystemExit(1)

    print("[PASS] All D2 regression cases passed")


if __name__ == "__main__":
    main()