import csv
import importlib.util
import json
from pathlib import Path

MANUAL = Path("experiments/week2September/manual")

EXTRACTOR_PATH = MANUAL / "scripts/extract_capabilities_rule_based.py"
RULES_PATH = MANUAL / "config/capability_rules_v3.1.json"
NEGATIVE_CASES_PATH = MANUAL / "data/regression/capability_regression_cases_v3_1.jsonl"
RETENTION_PATH = MANUAL / "data/regression/division_retention_13_approved_2026-11-14.csv"

RETENTION_ID = "gsm8k_train_02342"


def load_extractor():
    spec = importlib.util.spec_from_file_location(
        "extractor_smoke_v31",
        EXTRACTOR_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load extractor module.")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    for path in (
        EXTRACTOR_PATH,
        RULES_PATH,
        NEGATIVE_CASES_PATH,
        RETENTION_PATH,
    ):
        if not path.exists():
            raise FileNotFoundError(path)

    extractor = load_extractor()

    rules = json.loads(RULES_PATH.read_text(encoding="utf-8-sig"))
    compiled = extractor.compile_rules(rules)

    checks = []

    # Check N01 and N02: division must be suppressed.
    with NEGATIVE_CASES_PATH.open(
        "r",
        encoding="utf-8-sig",
    ) as f:
        negative_cases = [
            json.loads(line)
            for line in f
            if line.strip()
        ]

    for case in negative_cases:
        predicted, evidence, fired = extractor.extract_capabilities(
            case["question"],
            compiled,
        )

        division_detected = "division" in predicted
        passed = not division_detected
        checks.append(passed)

        print(
            case["test_id"],
            "| division =", division_detected,
            "| predicted =", predicted,
            "| expected division = False",
            "| PASS =", passed,
        )

    # Check retention case using the actual approved CSV question.
    with RETENTION_PATH.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        rows = list(csv.DictReader(f))

    retention_rows = [
        row for row in rows
        if row["problem_id"] == RETENTION_ID
    ]

    if len(retention_rows) != 1:
        raise ValueError(
            f"Expected exactly one {RETENTION_ID}, "
            f"found {len(retention_rows)}"
        )

    retention_question = retention_rows[0]["question"]

    predicted, evidence, fired = extractor.extract_capabilities(
        retention_question,
        compiled,
    )

    retention_pass = "division" in predicted
    checks.append(retention_pass)

    print(
        RETENTION_ID,
        "| division =", "division" in predicted,
        "| predicted =", predicted,
        "| division rules =", fired.get("division", []),
        "| expected division = True",
        "| PASS =", retention_pass,
    )

    if not all(checks):
        raise SystemExit(1)

    print("PASS: N01/N02 suppress division; retention example retains division.")


if __name__ == "__main__":
    main()
