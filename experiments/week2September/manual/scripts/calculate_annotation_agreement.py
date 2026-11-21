import argparse
import json
from pathlib import Path


CAPABILITIES = [
    "addition",
    "subtraction",
    "multiplication",
    "division",
    "percentage",
    "fraction",
    "ratio",
]

DIFFICULTIES = [
    "easy",
    "medium",
    "hard",
]


def load_jsonl(path):
    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            f"File not found: {path}"
        )

    records = []

    with path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON at {path}, "
                    f"line {line_number}: {exc}"
                ) from exc

            records.append(record)

    return records


def build_index(records, source_name):
    index = {}

    for record in records:
        problem_id = record.get("problem_id")

        if not problem_id:
            raise ValueError(
                f"{source_name}: record without "
                "problem_id."
            )

        if problem_id in index:
            raise ValueError(
                f"{source_name}: duplicate problem_id "
                f"{problem_id}"
            )

        index[problem_id] = record

    return index


def binary_labels(records_by_id, problem_ids, capability):
    labels = []

    for problem_id in problem_ids:
        record = records_by_id[problem_id]

        capabilities = record.get(
            "capabilities_manual",
            [],
        )

        labels.append(
            1 if capability in capabilities else 0
        )

    return labels


def difficulty_labels(records_by_id, problem_ids):
    return [
        records_by_id[problem_id][
            "difficulty_manual"
        ]
        for problem_id in problem_ids
    ]


def confusion_counts(labels_a, labels_b):
    tp = sum(
        a == 1 and b == 1
        for a, b in zip(labels_a, labels_b)
    )

    tn = sum(
        a == 0 and b == 0
        for a, b in zip(labels_a, labels_b)
    )

    fp = sum(
        a == 0 and b == 1
        for a, b in zip(labels_a, labels_b)
    )

    fn = sum(
        a == 1 and b == 0
        for a, b in zip(labels_a, labels_b)
    )

    return {
        "true_positive": tp,
        "true_negative": tn,
        "false_positive": fp,
        "false_negative": fn,
    }


def cohen_kappa_binary(labels_a, labels_b):
    n = len(labels_a)

    if n == 0:
        return None, "no_data"

    agreement = sum(
        a == b
        for a, b in zip(labels_a, labels_b)
    )

    p_observed = agreement / n

    a_positive = sum(labels_a)
    b_positive = sum(labels_b)

    a_negative = n - a_positive
    b_negative = n - b_positive

    p_expected = (
        (a_positive / n) * (b_positive / n)
        +
        (a_negative / n) * (b_negative / n)
    )

    denominator = 1.0 - p_expected

    if abs(denominator) < 1e-12:
        return None, "degenerate"

    kappa = (
        p_observed - p_expected
    ) / denominator

    return kappa, "ok"


def nominal_kappa(labels_a, labels_b, categories):
    n = len(labels_a)

    if n == 0:
        return None, "no_data"

    observed_agreement = sum(
        a == b
        for a, b in zip(labels_a, labels_b)
    ) / n

    counts_a = {
        category: labels_a.count(category)
        for category in categories
    }

    counts_b = {
        category: labels_b.count(category)
        for category in categories
    }

    expected_agreement = sum(
        (
            counts_a[category] / n
        )
        *
        (
            counts_b[category] / n
        )
        for category in categories
    )

    denominator = (
        1.0 - expected_agreement
    )

    if abs(denominator) < 1e-12:
        return None, "degenerate"

    kappa = (
        observed_agreement
        - expected_agreement
    ) / denominator

    return kappa, "ok"


def find_disagreements(
    a1,
    a2,
    problem_ids,
):
    disagreements = []

    for problem_id in problem_ids:
        r1 = a1[problem_id]
        r2 = a2[problem_id]

        caps_a = set(
            r1.get(
                "capabilities_manual",
                [],
            )
        )

        caps_b = set(
            r2.get(
                "capabilities_manual",
                [],
            )
        )

        capability_disagreements = sorted(
            caps_a.symmetric_difference(
                caps_b
            )
        )

        difficulty_a = r1[
            "difficulty_manual"
        ]

        difficulty_b = r2[
            "difficulty_manual"
        ]

        if (
            capability_disagreements
            or difficulty_a != difficulty_b
        ):
            disagreements.append(
                {
                    "problem_id": problem_id,
                    "capability_disagreements":
                        capability_disagreements,
                    "difficulty_A1":
                        difficulty_a,
                    "difficulty_A2":
                        difficulty_b,
                }
            )

    return disagreements


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Calculate Cohen's kappa between "
            "A1 and A2 manual annotations."
        )
    )

    parser.add_argument(
        "--a1",
        required=True,
        help="Path to A1 annotation JSONL.",
    )

    parser.add_argument(
        "--a2",
        required=True,
        help="Path to A2 annotation JSONL.",
    )

    parser.add_argument(
        "--output",
        required=True,
        help="Output JSON report path.",
    )

    args = parser.parse_args()

    a1_records = load_jsonl(args.a1)
    a2_records = load_jsonl(args.a2)

    a1 = build_index(
        a1_records,
        "A1",
    )

    a2 = build_index(
        a2_records,
        "A2",
    )

    ids_a1 = set(a1)
    ids_a2 = set(a2)

    if ids_a1 != ids_a2:
        missing_in_a2 = sorted(
            ids_a1 - ids_a2
        )

        missing_in_a1 = sorted(
            ids_a2 - ids_a1
        )

        raise ValueError(
            "A1/A2 problem ID sets differ.\n"
            f"Missing in A2: {missing_in_a2}\n"
            f"Missing in A1: {missing_in_a1}"
        )

    problem_ids = sorted(ids_a1)

    capability_results = {}

    for capability in CAPABILITIES:
        labels_a1 = binary_labels(
            a1,
            problem_ids,
            capability,
        )

        labels_a2 = binary_labels(
            a2,
            problem_ids,
            capability,
        )

        kappa, status = cohen_kappa_binary(
            labels_a1,
            labels_a2,
        )

        confusion = confusion_counts(
            labels_a1,
            labels_a2,
        )

        capability_results[capability] = {
            "kappa": kappa,
            "status": status,
            "n": len(problem_ids),
            "a1_positive": sum(labels_a1),
            "a2_positive": sum(labels_a2),
            "agreement_count": sum(
                a == b
                for a, b in zip(
                    labels_a1,
                    labels_a2,
                )
            ),
            "confusion_matrix": confusion,
        }

    difficulty_a1 = difficulty_labels(
        a1,
        problem_ids,
    )

    difficulty_a2 = difficulty_labels(
        a2,
        problem_ids,
    )

    difficulty_kappa, difficulty_status = (
        nominal_kappa(
            difficulty_a1,
            difficulty_a2,
            DIFFICULTIES,
        )
    )

    difficulty_result = {
        "kappa": difficulty_kappa,
        "status": difficulty_status,
        "n": len(problem_ids),
        "agreement_count": sum(
            a == b
            for a, b in zip(
                difficulty_a1,
                difficulty_a2,
            )
        ),
    }

    disagreements = find_disagreements(
        a1,
        a2,
        problem_ids,
    )

    report = {
        "schema_version": "v1",
        "annotation_type": "manual_pilot_agreement",
        "a1_file": str(
            Path(args.a1)
        ),
        "a2_file": str(
            Path(args.a2)
        ),
        "n_records": len(problem_ids),
        "capabilities": capability_results,
        "difficulty": difficulty_result,
        "disagreements": disagreements,
        "disagreement_count": len(
            disagreements
        ),
        "interpretation_rule": {
            "target_kappa": 0.60,
            "note": (
                "Kappa below 0.60 requires inspection "
                "of disagreements and guideline "
                "underspecification before any "
                "annotation revision."
            ),
            "degenerate_note": (
                "If a capability has no prevalence "
                "variation, kappa may be degenerate "
                "and should be reported as N/A rather "
                "than forced."
            ),
        },
    }

    output_path = Path(
        args.output
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            report,
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(
        "Annotation agreement calculation: OK"
    )

    print(
        f"Records: {len(problem_ids)}"
    )

    print()
    print(
        "Capability Cohen's kappa:"
    )

    for capability in CAPABILITIES:
        result = capability_results[
            capability
        ]

        kappa = result["kappa"]
        status = result["status"]

        if kappa is None:
            kappa_text = "N/A"
        else:
            kappa_text = f"{kappa:.4f}"

        print(
            f"  {capability:<15} "
            f"kappa={kappa_text} "
            f"status={status}"
        )

    print()
    print(
        "Difficulty Cohen's kappa:"
    )

    if difficulty_kappa is None:
        difficulty_text = "N/A"
    else:
        difficulty_text = (
            f"{difficulty_kappa:.4f}"
        )

    print(
        f"  kappa={difficulty_text} "
        f"status={difficulty_status}"
    )

    print()
    print(
        f"Disagreement records: "
        f"{len(disagreements)}"
    )

    print(
        f"Report written to: "
        f"{output_path}"
    )


if __name__ == "__main__":
    main()