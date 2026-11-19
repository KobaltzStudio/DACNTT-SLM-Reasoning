
from __future__ import annotations

import json
from pathlib import Path
from collections import Counter


ROOT = Path(__file__).resolve().parents[1]

FILE_V1 = ROOT / "data/supplement/supplement_annotations.jsonl"
FILE_V2 = ROOT / "data/supplement/supplement_annotations_v2.jsonl"
FILE_RAW = ROOT / "data/raw/supplement_annotations.jsonl"
FILE_EVAL = ROOT / "reports/capability/d2_regression/gold_evaluation_input.jsonl"


def load_jsonl(path: Path) -> dict[str, dict]:
    if not path.exists():
        raise FileNotFoundError(path)

    records = {}

    with path.open("r", encoding="utf-8-sig") as f:
        for line_no, line in enumerate(f, start=1):
            if not line.strip():
                continue

            obj = json.loads(line)
            problem_id = str(obj.get("problem_id", "")).strip()

            if not problem_id:
                print(f"WARNING: Missing problem_id at {path}, line {line_no}")
                continue

            if problem_id in records:
                print(f"WARNING: Duplicate ID {problem_id} in {path}")

            records[problem_id] = obj

    return records


def normalize_labels(record: dict, field: str) -> set[str]:
    value = record.get(field, [])

    if not isinstance(value, list):
        return set()

    return {
        str(label).strip()
        for label in value
        if str(label).strip()
    }


def main() -> None:
    v1 = load_jsonl(FILE_V1)
    v2 = load_jsonl(FILE_V2)
    raw = load_jsonl(FILE_RAW)
    evaluation = load_jsonl(FILE_EVAL)

    print("=" * 80)
    print("SUPPLEMENT VERSION COMPARISON")
    print("=" * 80)
    print("V1 records:", len(v1))
    print("V2 records:", len(v2))
    print("Raw records:", len(raw))
    print("Evaluation records:", len(evaluation))

    ids_v1 = set(v1)
    ids_v2 = set(v2)

    print("\nID comparison")
    print("V1 only:", sorted(ids_v1 - ids_v2))
    print("V2 only:", sorted(ids_v2 - ids_v1))
    print("Shared IDs:", len(ids_v1 & ids_v2))

    changed = []

    for problem_id in sorted(ids_v1 & ids_v2):
        r1 = v1[problem_id]
        r2 = v2[problem_id]

        labels_v1 = normalize_labels(r1, "capabilities_manual")
        labels_v2 = normalize_labels(r2, "capabilities_manual")

        if labels_v1 != labels_v2:
            changed.append(problem_id)

            print("\n" + "-" * 80)
            print("LABEL DIFFERENCE:", problem_id)
            print("V1 labels:", sorted(labels_v1))
            print("V2 labels:", sorted(labels_v2))
            print("V1 notes:", r1.get("notes", ""))
            print("V2 notes:", r2.get("notes", ""))
            print("Question:", raw.get(problem_id, {}).get("question", "NOT FOUND"))
            print("Ground truth:", raw.get(problem_id, {}).get("ground_truth", "NOT FOUND"))

        if r1.get("notes", "") != r2.get("notes", ""):
            if problem_id not in changed:
                changed.append(problem_id)

            print("\n" + "-" * 80)
            print("NOTES DIFFERENCE:", problem_id)
            print("V1 notes:", r1.get("notes", ""))
            print("V2 notes:", r2.get("notes", ""))

    print("\n" + "=" * 80)
    print("DIFFERENCE SUMMARY")
    print("=" * 80)
    print("Records with label or notes differences:", len(changed))
    print("Different IDs:", changed)

    # Compare supplement labels against D2 evaluation Gold.
    eval_field = "gold_capabilities"
    eval_differences = []

    for problem_id in sorted(ids_v2 & set(evaluation)):
        supplement_labels = normalize_labels(
            v2[problem_id],
            "capabilities_manual",
        )
        eval_labels = normalize_labels(
            evaluation[problem_id],
            eval_field,
        )

        if supplement_labels != eval_labels:
            eval_differences.append(problem_id)

            print("\n" + "-" * 80)
            print("SUPPLEMENT V2 VS D2 GOLD:", problem_id)
            print("Supplement:", sorted(supplement_labels))
            print("D2 Gold:", sorted(eval_labels))
            print("Supplement notes:", v2[problem_id].get("notes", ""))
            print("Question:", raw.get(problem_id, {}).get("question", "NOT FOUND"))

    print("\n" + "=" * 80)
    print("D2 GOLD COMPARISON SUMMARY")
    print("=" * 80)
    print("Shared supplement/evaluation IDs:", len(ids_v2 & set(evaluation)))
    print("Label differences vs D2 Gold:", len(eval_differences))
    print("Different IDs:", eval_differences)

    # Capability support by source.
    print("\n" + "=" * 80)
    print("CAPABILITY SUPPORT")
    print("=" * 80)

    for name, records, field in [
        ("Supplement V1", v1, "capabilities_manual"),
        ("Supplement V2", v2, "capabilities_manual"),
        ("D2 evaluation", evaluation, "gold_capabilities"),
    ]:
        counter = Counter()

        for record in records.values():
            counter.update(normalize_labels(record, field))

        print(name, dict(counter))


if __name__ == "__main__":
    main()
