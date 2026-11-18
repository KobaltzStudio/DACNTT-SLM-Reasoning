#!/usr/bin/env python3

import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    BASE / "reports/capability/d2_regression"
    / "gold_evaluation_input.jsonl"
)

PREDICTION_FILE = (
    BASE / "reports/capability/d2_regression"
    / "extractor_predictions.jsonl"
)

EVIDENCE_FILE = (
    BASE / "reports/capability/d2_regression"
    / "extractor_evidence.jsonl"
)

OUTPUT_JSONL = (
    BASE / "reports/capability/d2_regression"
    / "baseline_error_analysis.jsonl"
)

OUTPUT_MD = (
    BASE / "reports/capability/d2_regression"
    / "baseline_error_analysis.md"
)


def read_jsonl(path):
    with path.open("r", encoding="utf-8") as f:
        return [
            json.loads(line)
            for line in f
            if line.strip()
        ]


def main():
    gold_rows = read_jsonl(INPUT_FILE)
    prediction_rows = read_jsonl(PREDICTION_FILE)
    evidence_rows = read_jsonl(EVIDENCE_FILE)

    gold_by_id = {
        row["problem_id"]: row
        for row in gold_rows
    }

    prediction_by_id = {
        row["problem_id"]: row
        for row in prediction_rows
    }

    evidence_by_id = {
        row["problem_id"]: row
        for row in evidence_rows
    }

    if len(gold_by_id) != len(gold_rows):
        raise ValueError("Duplicate Gold IDs")

    if len(prediction_by_id) != len(prediction_rows):
        raise ValueError("Duplicate prediction IDs")

    if set(gold_by_id) != set(prediction_by_id):
        raise ValueError("Gold/prediction IDs do not match")

    errors = []
    capability_counts = {}

    for problem_id, gold_row in gold_by_id.items():
        truth = set(gold_row["gold_capabilities"])
        predicted = set(
            prediction_by_id[problem_id]["predicted_capabilities"]
        )

        missing = sorted(truth - predicted)
        unexpected = sorted(predicted - truth)

        if not missing and not unexpected:
            continue

        evidence = evidence_by_id.get(problem_id, {})

        row = {
            "problem_id": problem_id,
            "question": gold_row["question"],
            "gold_capabilities": sorted(truth),
            "predicted_capabilities": sorted(predicted),
            "missing_capabilities": missing,
            "unexpected_capabilities": unexpected,
            "evidence": evidence.get("evidence", {}),
            "rules_fired": evidence.get("rules_fired", {}),
        }

        errors.append(row)

        for capability in missing:
            entry = capability_counts.setdefault(
                capability,
                {"FN": 0, "FP": 0},
            )
            entry["FN"] += 1

        for capability in unexpected:
            entry = capability_counts.setdefault(
                capability,
                {"FN": 0, "FP": 0},
            )
            entry["FP"] += 1

    OUTPUT_JSONL.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_JSONL.open("w", encoding="utf-8") as f:
        for row in errors:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    lines = [
        "# D2 Problem-level Baseline Error Analysis",
        "",
        f"- Gold problems: {len(gold_by_id)}",
        f"- Problems with at least one mismatch: {len(errors)}",
        f"- Exact-match problems: {len(gold_by_id) - len(errors)}",
        "",
        "## Errors by Capability",
        "",
        "| Capability | False Negatives | False Positives |",
        "|---|---:|---:|",
    ]

    for capability in [
        "addition",
        "subtraction",
        "multiplication",
        "division",
        "percentage",
        "fraction",
        "ratio",
    ]:
        counts = capability_counts.get(
            capability,
            {"FN": 0, "FP": 0},
        )

        lines.append(
            f"| {capability} | {counts['FN']} | {counts['FP']} |"
        )

    lines.extend([
        "",
        "## Problem-level Mismatches",
        "",
        "Each record is compared using the complete capability set.",
        "",
    ])

    for row in errors:
        lines.extend([
            f"### {row['problem_id']}",
            "",
            f"Question: {row['question']}",
            "",
            f"Gold: {row['gold_capabilities']}",
            "",
            f"Predicted: {row['predicted_capabilities']}",
            "",
            f"Missing: {row['missing_capabilities']}",
            "",
            f"Unexpected: {row['unexpected_capabilities']}",
            "",
            f"Evidence: `{json.dumps(row['evidence'], ensure_ascii=False)}`",
            "",
            f"Rules fired: `{json.dumps(row['rules_fired'], ensure_ascii=False)}`",
            "",
            "---",
            "",
        ])

    OUTPUT_MD.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    print("D2 BASELINE ERROR ANALYSIS")
    print(f"Gold problems: {len(gold_by_id)}")
    print(f"Problems with mismatch: {len(errors)}")
    print(f"Exact-match problems: {len(gold_by_id) - len(errors)}")
    print()
    print("Errors by capability:")

    for capability, counts in capability_counts.items():
        print(
            f"{capability:<16}"
            f"FN={counts['FN']:<4}"
            f"FP={counts['FP']:<4}"
        )

    print(f"\nJSONL: {OUTPUT_JSONL}")
    print(f"Markdown: {OUTPUT_MD}")
    print("[PASS]")


if __name__ == "__main__":
    main()