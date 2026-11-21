
import argparse
import csv
import importlib.util
import json
from pathlib import Path

def load_extractor(path):
    spec = importlib.util.spec_from_file_location(
        "capability_extractor_retention", path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def parse_labels(value):
    if not value:
        return []
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return parsed
    except (json.JSONDecodeError, TypeError):
        pass
    return [item.strip() for item in value.split(",") if item.strip()]

def is_yes(value):
    return str(value or "").strip().upper() in {"YES", "TRUE", "1"}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--extractor", type=Path, required=True)
    parser.add_argument("--rules", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    extractor = load_extractor(args.extractor)
    rule_data = json.loads(args.rules.read_text(encoding="utf-8-sig"))
    compiled = extractor.compile_rules(rule_data)

    with args.input.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    if len(rows) != 13:
        raise ValueError(f"Expected 13 rows, found {len(rows)}")

    results = []

    for row in rows:
        gold = parse_labels(row["gold_capabilities"])
        predicted, evidence, fired = extractor.extract_capabilities(
            row["question"], compiled
        )

        trace_verified = is_yes(row.get("solution_trace_available"))
        status = "TRACE_VERIFIED" if trace_verified else "PROVISIONAL_NO_TRACE"

        gold_division = "division" in gold
        predicted_division = "division" in predicted

        results.append({
            "problem_id": row["problem_id"],
            "annotation_status": status,
            "solution_trace_available": row.get("solution_trace_available", ""),
            "gold_label_correct": row.get("gold_label_correct", ""),
            "human_approval": row.get("human_approval", ""),
            "gold_capabilities": json.dumps(gold, ensure_ascii=False),
            "predicted_capabilities": json.dumps(predicted, ensure_ascii=False),
            "gold_division": gold_division,
            "predicted_division": predicted_division,
            "division_correct": gold_division == predicted_division,
            "division_evidence": json.dumps(
                evidence.get("division", []), ensure_ascii=False
            ),
            "division_rules_fired": json.dumps(
                fired.get("division", []), ensure_ascii=False
            ),
        })

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)

    for group_name in ("TRACE_VERIFIED", "PROVISIONAL_NO_TRACE", "ALL"):
        group = (
            results if group_name == "ALL"
            else [r for r in results if r["annotation_status"] == group_name]
        )

        tp = sum(r["gold_division"] and r["predicted_division"] for r in group)
        fp = sum(not r["gold_division"] and r["predicted_division"] for r in group)
        fn = sum(r["gold_division"] and not r["predicted_division"] for r in group)
        tn = sum(not r["gold_division"] and not r["predicted_division"] for r in group)

        print(f"\n{group_name}: n={len(group)}")
        print(f"TP={tp}, FP={fp}, FN={fn}, TN={tn}")
        print(f"Correct={tp + tn}/{len(group)}")

    print("\nMISMATCHES:")
    for row in results:
        if not row["division_correct"]:
            print(
                row["problem_id"],
                "| status =", row["annotation_status"],
                "| Gold =", row["gold_division"],
                "| Predicted =", row["predicted_division"],
            )

    print("\nCreated:", args.output)

    # A provisional mismatch is reported, not silently treated as a verified failure.
    verified_mismatches = [
        r for r in results
        if r["annotation_status"] == "TRACE_VERIFIED"
        and not r["division_correct"]
    ]

    if verified_mismatches:
        print("FAIL: mismatch exists in trace-verified records.")
        raise SystemExit(1)

    print("PASS: no division mismatch among trace-verified records.")
    if any(r["annotation_status"] == "PROVISIONAL_NO_TRACE" for r in results):
        print("REVIEW REQUIRED: provisional records are reported separately.")

if __name__ == "__main__":
    main()
