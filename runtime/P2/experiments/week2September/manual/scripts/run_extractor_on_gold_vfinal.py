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
    BASE / "reports" / "capability" / "d3_final_regression"
    / "gold_evaluation_input.jsonl"
)

OUTPUT_DIR = BASE / "reports" / "capability" / "d3_final_regression"

PREDICTIONS_FILE = OUTPUT_DIR / "extractor_predictions.jsonl"
EVIDENCE_FILE = OUTPUT_DIR / "extractor_evidence.jsonl"


def read_jsonl(path):
    if not path.exists():
        raise FileNotFoundError(path)

    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON at {path}:{line_no}"
                ) from exc
    return rows


def write_jsonl(path, rows):
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main():
    if not RULES_FILE.exists():
        raise FileNotFoundError(RULES_FILE)

    records = read_jsonl(INPUT_FILE)

    rules_data = json.loads(RULES_FILE.read_text(encoding="utf-8"))
    compiled_rules = compile_rules(rules_data)

    predictions = []
    evidence_records = []
    seen_ids = set()

    for record in records:
        problem_id = record["problem_id"]

        if problem_id in seen_ids:
            raise ValueError(f"Duplicate ID: {problem_id}")
        seen_ids.add(problem_id)

        predicted, evidence, rules_fired = extract_capabilities(
            record["question"],
            compiled_rules,
        )

        predicted = sorted(set(predicted))

        predictions.append({
            "problem_id": problem_id,
            "predicted_capabilities": predicted,
        })

        evidence_records.append({
            "problem_id": problem_id,
            "predicted_capabilities": predicted,
            "evidence": evidence,
            "rules_fired": rules_fired,
        })

    if len(predictions) != 185:
        raise ValueError(
            f"Expected 185 predictions, got {len(predictions)}"
        )

    if len(predictions) != len(records):
        raise ValueError("Prediction count differs from input count")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    write_jsonl(PREDICTIONS_FILE, predictions)
    write_jsonl(EVIDENCE_FILE, evidence_records)

    print("D3 FINAL PROBLEM-LEVEL EXTRACTOR")
    print(f"Input records: {len(records)}")
    print(f"Prediction records: {len(predictions)}")
    print(f"Unique IDs: {len(seen_ids)}")
    print(f"Rules file: {RULES_FILE}")
    print(f"Predictions: {PREDICTIONS_FILE}")
    print(f"Evidence: {EVIDENCE_FILE}")
    print("[PASS]")


if __name__ == "__main__":
    main()
