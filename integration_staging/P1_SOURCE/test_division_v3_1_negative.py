
import argparse
import csv
import importlib.util
import json
from pathlib import Path

def load_extractor(path):
    spec = importlib.util.spec_from_file_location(
        "capability_extractor_negative_v31", path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--extractor", type=Path, required=True)
    parser.add_argument("--rules", type=Path, required=True)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    extractor = load_extractor(args.extractor)
    rule_data = json.loads(args.rules.read_text(encoding="utf-8-sig"))
    compiled = extractor.compile_rules(rule_data)

    cases = []
    with args.cases.open("r", encoding="utf-8-sig") as f:
        for line_number, line in enumerate(f, start=1):
            if line.strip():
                case = json.loads(line)
                case["_line_number"] = line_number
                cases.append(case)

    if len(cases) != 2:
        raise ValueError(f"Expected exactly 2 v3.1 cases, found {len(cases)}")

    results = []

    for case in cases:
        required_fields = {
            "test_id",
            "source_problem_id",
            "question",
            "expected_capabilities",
            "must_not_include",
        }
        missing = required_fields - set(case)
        if missing:
            raise ValueError(
                f"{case.get('test_id', '?')}: missing fields {sorted(missing)}"
            )

        predicted, evidence, fired = extractor.extract_capabilities(
            case["question"], compiled
        )

        expected = set(case["expected_capabilities"])
        forbidden = set(case["must_not_include"])
        predicted_set = set(predicted)

        missing_expected = sorted(expected - predicted_set)
        unexpected = sorted(predicted_set - expected)
        forbidden_found = sorted(forbidden & predicted_set)

        expected_match = expected.issubset(predicted_set)
        forbidden_check = not forbidden_found
        exact_match = predicted_set == expected

        # Strict PASS requires all expected labels, no forbidden labels,
        # and exact equality with the expected set.
        test_pass = expected_match and forbidden_check and exact_match

        results.append({
            "test_id": case["test_id"],
            "source_problem_id": case["source_problem_id"],
            "predicted_capabilities": json.dumps(
                sorted(predicted_set), ensure_ascii=False
            ),
            "expected_capabilities": json.dumps(
                sorted(expected), ensure_ascii=False
            ),
            "missing_expected": json.dumps(missing_expected),
            "unexpected": json.dumps(unexpected),
            "must_not_include": json.dumps(sorted(forbidden)),
            "forbidden_found": json.dumps(forbidden_found),
            "division_detected": "division" in predicted_set,
            "percentage_detected": "percentage" in predicted_set,
            "expected_check": expected_match,
            "forbidden_check": forbidden_check,
            "exact_match": exact_match,
            "rules_fired": json.dumps(fired, ensure_ascii=False),
            "evidence": json.dumps(evidence, ensure_ascii=False),
            "test_pass": test_pass,
        })

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)

    print("v3.1 negative regression")
    print("Cases:", len(results))

    for row in results:
        print(
            f"{row['test_id']}: "
            f"expected={row['expected_capabilities']}, "
            f"predicted={row['predicted_capabilities']}, "
            f"missing={row['missing_expected']}, "
            f"forbidden={row['forbidden_found']}, "
            f"exact_match={row['exact_match']}, "
            f"PASS={row['test_pass']}"
        )

    passed = sum(bool(row["test_pass"]) for row in results)
    print(f"\nPASS: {passed}/{len(results)}")
    print("Created:", args.output)

    if passed != len(results):
        raise SystemExit(1)

    print("PASS: all expected labels matched exactly; forbidden labels absent.")

if __name__ == "__main__":
    main()
