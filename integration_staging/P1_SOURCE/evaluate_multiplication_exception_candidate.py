import copy
import csv
import importlib.util
import json
import re
from pathlib import Path

MANUAL = Path("experiments/week2September/manual")

EXTRACTOR_PATH = (
    MANUAL / "scripts/extract_capabilities_rule_based.py"
)

RULES_PATH = MANUAL / "config/capability_rules_v3.1.json"

APPROVED_PATH = (
    MANUAL
    / "reports/capability/p1_day14_final_2026-11-14/approved/"
    / "priority_error_review_170_approved.csv"
)

OUTPUT_DIR = (
    MANUAL
    / "reports/capability/p1_extractor_v3_1_2026-11-14/"
    / "candidate_analysis/multiplication_exception_candidate"
)

TARGET_ID = "gsm8k_train_00011"

CANDIDATE_NEGATIVE_PATTERN = (
    r"(?s)\b\d+(?:\.\d+)?\s*%\s+of\s+them\b"
    r"(?=.*\b\d+(?:\.\d+)?\s+of\s+them\s+"
    r"(?:are|is|were|was)\b)"
    r"(?=.*\bhow\s+many\b)"
)


def load_extractor():
    spec = importlib.util.spec_from_file_location(
        "multiplication_exception_extractor",
        EXTRACTOR_PATH,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load extractor module.")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


def load_csv(path):
    if not path.exists():
        raise FileNotFoundError(path)

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        return list(csv.DictReader(f))


def parse_labels(value):
    parsed = json.loads(value)

    if not isinstance(parsed, list):
        raise ValueError(f"Expected JSON list, got: {parsed}")

    return set(parsed)


def evaluate(extractor, rules, rows):
    compiled = extractor.compile_rules(rules)
    capabilities = list(rules["rules"].keys())

    predictions = {}
    counts = {
        capability: {
            "tp": 0,
            "fp": 0,
            "fn": 0,
            "tn": 0,
        }
        for capability in capabilities
    }

    exact_matches = 0
    total_tp = 0
    total_fp = 0
    total_fn = 0

    for row in rows:
        problem_id = row["problem_id"]
        question = row["question"]
        gold = parse_labels(row["gold_capabilities"])

        predicted, evidence, rules_fired = (
            extractor.extract_capabilities(
                question,
                compiled,
            )
        )

        predicted = set(predicted)
        predictions[problem_id] = {
            "predicted": sorted(predicted),
            "evidence": evidence,
            "rules_fired": rules_fired,
        }

        if predicted == gold:
            exact_matches += 1

        for capability in capabilities:
            in_gold = capability in gold
            in_prediction = capability in predicted

            if in_gold and in_prediction:
                counts[capability]["tp"] += 1
                total_tp += 1
            elif in_prediction and not in_gold:
                counts[capability]["fp"] += 1
                total_fp += 1
            elif in_gold and not in_prediction:
                counts[capability]["fn"] += 1
                total_fn += 1
            else:
                counts[capability]["tn"] += 1

    precision = (
        total_tp / (total_tp + total_fp)
        if total_tp + total_fp else 0.0
    )

    recall = (
        total_tp / (total_tp + total_fn)
        if total_tp + total_fn else 0.0
    )

    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall else 0.0
    )

    return {
        "predictions": predictions,
        "metrics": {
            "samples": len(rows),
            "exact_match": exact_matches,
            "exact_match_rate": exact_matches / len(rows),
            "micro": {
                "tp": total_tp,
                "fp": total_fp,
                "fn": total_fn,
                "precision": precision,
                "recall": recall,
                "f1": f1,
            },
            "per_capability": counts,
        },
    }


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    extractor = load_extractor()

    original_rules = json.loads(
        RULES_PATH.read_text(encoding="utf-8-sig")
    )

    rows = load_csv(APPROVED_PATH)

    if len(rows) != 170:
        raise ValueError(
            f"Expected 170 approved rows, got {len(rows)}"
        )

    # Baseline: current official v3.1, unchanged.
    baseline = evaluate(
        extractor,
        original_rules,
        rows,
    )

    # Candidate: add one narrow multiplication negative pattern.
    candidate_rules = copy.deepcopy(original_rules)

    re.compile(
        CANDIDATE_NEGATIVE_PATTERN,
        flags=re.IGNORECASE,
    )

    negative_patterns = (
        candidate_rules["rules"]["multiplication"]
        .setdefault("negative_patterns", [])
    )

    if CANDIDATE_NEGATIVE_PATTERN not in negative_patterns:
        negative_patterns.append(CANDIDATE_NEGATIVE_PATTERN)

    candidate = evaluate(
        extractor,
        candidate_rules,
        rows,
    )

    changes = []

    for row in rows:
        problem_id = row["problem_id"]

        before = baseline["predictions"][problem_id]
        after = candidate["predictions"][problem_id]

        if before["predicted"] != after["predicted"]:
            changes.append({
                "problem_id": problem_id,
                "gold_capabilities": row["gold_capabilities"],
                "question": row["question"],
                "baseline_predictions": json.dumps(
                    before["predicted"],
                    ensure_ascii=False,
                ),
                "candidate_predictions": json.dumps(
                    after["predicted"],
                    ensure_ascii=False,
                ),
                "baseline_rules_fired": json.dumps(
                    before["rules_fired"],
                    ensure_ascii=False,
                ),
                "candidate_rules_fired": json.dumps(
                    after["rules_fired"],
                    ensure_ascii=False,
                ),
            })

    metrics = {
        "experiment": "multiplication_exception_candidate",
        "candidate_negative_pattern": CANDIDATE_NEGATIVE_PATTERN,
        "official_config_modified": False,
        "baseline": baseline["metrics"],
        "candidate": candidate["metrics"],
        "changed_rows": len(changes),
        "changed_problem_ids": [
            item["problem_id"] for item in changes
        ],
    }

    metrics_path = OUTPUT_DIR / "candidate_metrics.json"
    changes_path = OUTPUT_DIR / "candidate_changes.csv"

    metrics_path.write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    fieldnames = [
        "problem_id",
        "gold_capabilities",
        "question",
        "baseline_predictions",
        "candidate_predictions",
        "baseline_rules_fired",
        "candidate_rules_fired",
    ]

    with changes_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
        )
        writer.writeheader()
        writer.writerows(changes)

    target = next(
        (
            row for row in rows
            if row["problem_id"] == TARGET_ID
        ),
        None,
    )

    if target is None:
        raise ValueError(f"Target not found: {TARGET_ID}")

    target_before = baseline["predictions"][TARGET_ID]
    target_after = candidate["predictions"][TARGET_ID]

    normalized_target = extractor.normalize_text(
        target["question"]
    )

    pattern_matches_target = bool(
        re.search(
            CANDIDATE_NEGATIVE_PATTERN,
            normalized_target,
            flags=re.IGNORECASE,
        )
    )

    print("=" * 90)
    print("MULTIPLICATION EXCEPTION CANDIDATE EVALUATION")
    print("=" * 90)

    print("\nTARGET:", TARGET_ID)
    print("Negative pattern matches target:", pattern_matches_target)
    print("Baseline prediction:", target_before["predicted"])
    print("Candidate prediction:", target_after["predicted"])

    print("\nBASELINE METRICS:")
    print(json.dumps(
        baseline["metrics"],
        ensure_ascii=False,
        indent=2,
    ))

    print("\nCANDIDATE METRICS:")
    print(json.dumps(
        candidate["metrics"],
        ensure_ascii=False,
        indent=2,
    ))

    print("\nCHANGED ROWS:", len(changes))

    for item in changes:
        print(
            item["problem_id"],
            "| Gold:", item["gold_capabilities"],
            "| Before:", item["baseline_predictions"],
            "| After:", item["candidate_predictions"],
        )

    print("\nOUTPUT FILES:")
    print(metrics_path)
    print(changes_path)

    print("\nOfficial config modified: NO")
    print("Candidate evaluation completed.")


if __name__ == "__main__":
    main()
