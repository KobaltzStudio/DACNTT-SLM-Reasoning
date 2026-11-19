import json
import sys
from pathlib import Path


# ============================================================
# Configuration
# ============================================================

DEFAULT_QUOTA = {
    "percentage": 30,
    "fraction": 30,
    "ratio": 30,
}


# ============================================================
# Helpers
# ============================================================

def load_jsonl(path):
    if not path.exists():
        raise FileNotFoundError(
            f"Input file not found: {path}"
        )

    records = []

    with path.open(
        "r",
        encoding="utf-8"
    ) as f:

        for line_number, line in enumerate(
            f,
            start=1
        ):

            line = line.strip()

            if not line:
                continue

            try:
                records.append(
                    json.loads(line)
                )

            except json.JSONDecodeError as exc:

                raise ValueError(
                    f"Invalid JSON at {path}, "
                    f"line {line_number}: {exc}"
                ) from exc

    return records


def signal_strength(record, capability):
    """
    Rank explicit signals above weak/general signals.

    This is ONLY for candidate prioritization.
    It does NOT assign the actual capability label.
    """

    signals = record.get(
        "signals",
        {}
    ).get(
        capability,
        []
    )

    if not signals:
        return 0

    score = 0

    for signal in signals:

        signal = str(signal).lower()

        # Strong explicit mathematical indicators
        if capability == "ratio":

            if (
                "ratio" in signal
                or "ratios" in signal
                or r"\d+\s*:\s*\d+" in signal
            ):
                score += 3

            elif (
                "proportion" in signal
                or "proportional" in signal
            ):
                score += 2

            else:
                score += 1

        elif capability == "percentage":

            if (
                r"\d+(?:\.\d+)?\s*%" in signal
                or "percent" in signal
                or "percentage" in signal
            ):
                score += 3

            elif (
                "tax rate" in signal
                or "discount" in signal
                or "tip" in signal
            ):
                score += 2

            else:
                score += 1

        elif capability == "fraction":

            if (
                r"\d+\s*/\s*\d+" in signal
                or "one-third" in signal
                or "one-fourth" in signal
                or "two-thirds" in signal
                or "three-fourths" in signal
            ):
                score += 3

            elif (
                "half" in signal
                or "halves" in signal
                or "one-half" in signal
            ):
                score += 2

            else:
                score += 1

    return score


def candidate_sort_key(record, capability):
    """
    Deterministic ranking.

    Priority:
      1. stronger explicit signal
      2. fewer unrelated candidate types
      3. problem_id
    """

    strength = signal_strength(
        record,
        capability
    )

    candidate_types = record.get(
        "candidate_types",
        []
    )

    unrelated_count = len(
        [
            c
            for c in candidate_types
            if c != capability
        ]
    )

    return (
        -strength,
        unrelated_count,
        record.get(
            "problem_id",
            ""
        ),
    )


# ============================================================
# Main selection
# ============================================================

def main():

    if len(sys.argv) not in (3, 6):

        print(
            "Usage:\n"
            "python select_supplement.py "
            "<input_candidates.jsonl> "
            "<output_supplement.jsonl>\n\n"
            "Optional custom quotas:\n"
            "python select_supplement.py "
            "<input> <output> "
            "<percentage_quota> "
            "<fraction_quota> "
            "<ratio_quota>"
        )

        sys.exit(1)

    input_path = Path(
        sys.argv[1]
    )

    output_path = Path(
        sys.argv[2]
    )

    if len(sys.argv) == 6:

        quota = {
            "percentage": int(
                sys.argv[3]
            ),
            "fraction": int(
                sys.argv[4]
            ),
            "ratio": int(
                sys.argv[5]
            ),
        }

    else:

        quota = DEFAULT_QUOTA.copy()

    records = load_jsonl(
        input_path
    )

    print("=" * 70)
    print("SUPPLEMENT SAMPLING")
    print("=" * 70)

    print()
    print(
        f"Input candidates: {len(records)}"
    )

    print()
    print("Candidate quotas:")

    for capability in (
        "percentage",
        "fraction",
        "ratio",
    ):

        print(
            f"  {capability:<12}: "
            f"{quota[capability]}"
        )

    # --------------------------------------------------------
    # Candidate pools
    # --------------------------------------------------------

    pools = {}

    for capability in (
        "percentage",
        "fraction",
        "ratio",
    ):

        pool = [
            record
            for record in records
            if capability in record.get(
                "candidate_types",
                []
            )
        ]

        pool.sort(
            key=lambda record:
                candidate_sort_key(
                    record,
                    capability
                )
        )

        pools[capability] = pool

        print()
        print(
            f"{capability} candidate pool: "
            f"{len(pool)}"
        )

        if len(pool) < quota[capability]:

            raise RuntimeError(
                f"Not enough {capability} candidates: "
                f"need {quota[capability]}, "
                f"available {len(pool)}."
            )

    # --------------------------------------------------------
    # Greedy union selection
    #
    # First select candidates for the most scarce target:
    # ratio -> fraction -> percentage.
    #
    # If a selected candidate also belongs to another
    # capability pool, it counts toward that pool's quota.
    # --------------------------------------------------------

    selected = {}
    selected_by_capability = {
        "percentage": 0,
        "fraction": 0,
        "ratio": 0,
    }

    # Ratio first because it has the smallest candidate pool.
    selection_order = [
        "ratio",
        "fraction",
        "percentage",
    ]

    for capability in selection_order:

        target = quota[capability]

        for record in pools[capability]:

            problem_id = record[
                "problem_id"
            ]

            if problem_id in selected:
                continue

            # Select candidate.
            selected[
                problem_id
            ] = record

            # Update all candidate-type counts
            # represented by this record.
            for candidate_type in record.get(
                "candidate_types",
                []
            ):

                if candidate_type in selected_by_capability:

                    selected_by_capability[
                        candidate_type
                    ] += 1

            # Stop once this capability has enough
            # selected candidates.
            if (
                selected_by_capability[
                    capability
                ]
                >= target
            ):
                break

    # --------------------------------------------------------
    # Safety fill
    #
    # Because overlap can make the greedy pass leave one
    # capability below quota, continue adding candidates.
    # --------------------------------------------------------

    changed = True

    while changed:

        changed = False

        for capability in selection_order:

            if (
                selected_by_capability[
                    capability
                ]
                >= quota[capability]
            ):
                continue

            for record in pools[capability]:

                problem_id = record[
                    "problem_id"
                ]

                if problem_id in selected:
                    continue

                selected[
                    problem_id
                ] = record

                for candidate_type in record.get(
                    "candidate_types",
                    []
                ):

                    if candidate_type in selected_by_capability:

                        selected_by_capability[
                            candidate_type
                        ] += 1

                changed = True

                break

    # --------------------------------------------------------
    # Final quota check
    # --------------------------------------------------------

    missing_quota = []

    for capability in (
        "percentage",
        "fraction",
        "ratio",
    ):

        count = selected_by_capability[
            capability
        ]

        if count < quota[capability]:

            missing_quota.append(
                (
                    capability,
                    count,
                    quota[capability],
                )
            )

    if missing_quota:

        raise RuntimeError(
            "Could not satisfy candidate quotas: "
            f"{missing_quota}"
        )

    # --------------------------------------------------------
    # Sort deterministically by problem_id
    # --------------------------------------------------------

    selected_records = sorted(
        selected.values(),
        key=lambda record:
            record["problem_id"]
    )

    # --------------------------------------------------------
    # Export
    # --------------------------------------------------------

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with output_path.open(
        "w",
        encoding="utf-8"
    ) as f:

        for record in selected_records:

            f.write(
                json.dumps(
                    record,
                    ensure_ascii=False
                )
                + "\n"
            )

    # --------------------------------------------------------
    # Report
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("SUPPLEMENT SELECTION RESULT")
    print("=" * 70)

    print()
    print(
        f"Selected records: "
        f"{len(selected_records)}"
    )

    print()
    print(
        f"{'Type':<15}"
        f"{'Selected':>12}"
        f"{'Quota':>10}"
    )

    print("-" * 40)

    for capability in (
        "percentage",
        "fraction",
        "ratio",
    ):

        print(
            f"{capability:<15}"
            f"{selected_by_capability[capability]:>12}"
            f"{quota[capability]:>10}"
        )

    print()
    print(
        f"Output: {output_path}"
    )

    print()
    print(
        "IMPORTANT:"
    )

    print(
        "candidate_types are linguistic signals only."
    )

    print(
        "They are NOT manual capability labels."
    )

    print(
        "All selected records must be manually "
        "annotated according to guideline_v2.md."
    )


if __name__ == "__main__":
    main()