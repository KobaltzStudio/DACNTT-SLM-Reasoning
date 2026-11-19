import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]

INPUT = (
    BASE / "reports/capability/d2_regression"
    / "regression_test_results.json"
)

OUTPUT = (
    BASE / "reports/capability/d2_regression"
    / "regression_failure_analysis.md"
)


def main():
    report = json.loads(INPUT.read_text(encoding="utf-8"))

    failed = [
        row for row in report["results"]
        if row["status"] == "FAIL"
    ]

    lines = [
        "# D2 Regression Failure Analysis",
        "",
        f"Total cases: {report['total']}",
        f"Passed: {report['passed']}",
        f"Failed: {report['failed']}",
        "",
        "## Failed Cases",
        "",
    ]

    for row in failed:
        lines.extend([
            f"### {row['test_id']}",
            "",
            f"Category: {row['category']}",
            "",
            f"Problem: {row['problem']}",
            "",
            f"Expected: {row['expected_capabilities']}",
            "",
            f"Predicted: {row['predicted_capabilities']}",
            "",
            f"Missing: {row['missing']}",
            "",
            f"Unexpected: {row['unexpected']}",
            "",
            "Initial classification: Requires manual review.",
            "",
            "---",
            "",
        ])

    OUTPUT.write_text("\n".join(lines), encoding="utf-8")

    print(f"Failed cases: {len(failed)}")
    print(f"Created: {OUTPUT}")


if __name__ == "__main__":
    main()