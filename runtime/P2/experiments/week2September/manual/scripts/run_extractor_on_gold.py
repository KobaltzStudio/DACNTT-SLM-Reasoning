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

RULES_FILE = BASE / "config" / "capability_rules_v2.json"

INPUT_FILE = (
    BASE / "reports" / "capability" / "d2_regression"
    / "gold_evaluation_input.jsonl"
)

OUTPUT_FILE = (
    BASE / "reports" / "capability" / "d2_regression"
    / "extractor_predictions.jsonl"
)

EVIDENCE_FILE = (
    BASE / "reports" / "capability" / "d2_regression"
    / "extractor_evidence.jsonl"
)


def read_jsonl(path):
    with path.open("r", encoding="utf-8") as f:
        return [
            json.loads(line)
            for line in f
            if line.strip()
        ]


def main():
    rules_data = json.loads(
        RULES_FILE.read_text(encoding="utf-8")
    )

    compiled_rules = compile_rules(rules_data)

    records = read_jsonl(INPUT_FILE)

    predictions = []
    evidence_records = []

    seen_ids = set()

    for record in records:
        problem_id = record["problem_id"]
        question = record["question"]

        if problem_id in seen_ids:
            raise ValueError(f"Duplicate ID: {problem_id}")

        seen_ids.add(problem_id)

        predicted, evidence, rules_fired = extract_capabilities(
            question,
            compiled_rules,
        )

        predictions.append({
            "problem_id": problem_id,
            "predicted_capabilities": sorted(set(predicted)),
        })

        evidence_records.append({
            "problem_id": problem_id,
            "predicted_capabilities": sorted(set(predicted)),
            "evidence": evidence,
            "rules_fired": rules_fired,
        })

    if len(predictions) != 185:
        raise ValueError(
            f"Expected 185 predictions, got {len(predictions)}"
        )

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        for row in predictions:
            f.write(
                json.dumps(row, ensure_ascii=False) + "\n"
            )

    with EVIDENCE_FILE.open("w", encoding="utf-8") as f:
        for row in evidence_records:
            f.write(
                json.dumps(row, ensure_ascii=False) + "\n"
            )

    print("PROBLEM-LEVEL EXTRACTOR")
    print(f"Input records: {len(records)}")
    print(f"Prediction records: {len(predictions)}")
    print(f"Unique IDs: {len(seen_ids)}")
    print(f"Predictions: {OUTPUT_FILE}")
    print(f"Evidence: {EVIDENCE_FILE}")
    print("[PASS]")


if __name__ == "__main__":
    main()