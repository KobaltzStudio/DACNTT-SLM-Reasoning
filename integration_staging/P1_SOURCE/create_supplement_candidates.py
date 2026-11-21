import json
import re
import sys
from pathlib import Path


BASE = Path(__file__).resolve().parents[1]


PERCENTAGE_PATTERNS = [
    r"\b\d+(?:\.\d+)?\s*%",
    r"\bpercent\b",
    r"\bpercentage\b",
    r"\bdiscount\b",
    r"\btax\b",
    r"\btax rate\b",
    r"\btip\b",
    r"\bprofit\b",
    r"\bloss\b",
]


FRACTION_PATTERNS = [
    r"\bhalf\b",
    r"\bhalves\b",
    r"\bone[- ]half\b",
    r"\bone[- ]third\b",
    r"\bone[- ]fourth\b",
    r"\bone[- ]fifth\b",
    r"\btwo[- ]thirds\b",
    r"\btwo[- ]fifths\b",
    r"\bthree[- ]fourths\b",
    r"\b\d+\s*/\s*\d+\b",
]


RATIO_PATTERNS = [
    r"\bratio\b",
    r"\bratios\b",
    r"\bproportion\b",
    r"\bproportional\b",
    r"\bfor every\b",
    r"\bto every\b",
    r"\b\d+\s*:\s*\d+\b",
]


def load_jsonl(path: Path):
    if not path.exists():
        raise FileNotFoundError(
            f"Input file not found: {path}"
        )

    records = []

    with path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON at {path}, "
                    f"line {line_number}: {exc}"
                ) from exc

    return records


def get_problem_id(record):
    problem_id = record.get("problem_id")

    if problem_id is None:
        problem_id = record.get("id")

    if problem_id is None:
        raise ValueError(
            "Input record does not contain "
            "'problem_id' or 'id'."
        )

    return str(problem_id)


def get_problem_text(record):
    """
    Support common local GSM8K representations:
      - question
      - problem
      - problem_text
    """

    for field in (
        "question",
        "problem",
        "problem_text",
    ):
        value = record.get(field)

        if value:
            return str(value)

    raise ValueError(
        f"{get_problem_id(record)}: "
        "cannot find problem text. "
        "Expected one of: "
        "question, problem, problem_text."
    )


def find_matches(text, patterns):
    matches = []

    for pattern in patterns:
        found = re.findall(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        if found:
            matches.append(pattern)

    return matches


def main():
    if len(sys.argv) != 3:
        print(
            "Usage:\n"
            "python create_supplement_candidates.py "
            "<gsm8k_train.jsonl> "
            "<supplement_candidates.jsonl>"
        )
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    records = load_jsonl(input_path)

    candidates = []

    signal_counts = {
        "percentage": 0,
        "fraction": 0,
        "ratio": 0,
    }

    for record in records:
        problem_id = get_problem_id(record)
        question = get_problem_text(record)

        text = question.lower()

        percentage_hits = find_matches(
            text,
            PERCENTAGE_PATTERNS,
        )

        fraction_hits = find_matches(
            text,
            FRACTION_PATTERNS,
        )

        ratio_hits = find_matches(
            text,
            RATIO_PATTERNS,
        )

        candidate_types = []

        if percentage_hits:
            candidate_types.append("percentage")
            signal_counts["percentage"] += 1

        if fraction_hits:
            candidate_types.append("fraction")
            signal_counts["fraction"] += 1

        if ratio_hits:
            candidate_types.append("ratio")
            signal_counts["ratio"] += 1

        if not candidate_types:
            continue

        output_record = {
            "problem_id": problem_id,
            "question": question,
            "ground_truth": record.get(
                "ground_truth",
                "",
            ),
            "candidate_types": candidate_types,
            "signals": {
                "percentage": percentage_hits,
                "fraction": fraction_hits,
                "ratio": ratio_hits,
            },
        }

        candidates.append(output_record)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as f:
        for record in candidates:
            f.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                )
                + "\n"
            )

    print(
        f"Input records: {len(records)}"
    )

    print(
        f"Candidate records: {len(candidates)}"
    )

    print(
        "Signal counts:"
    )

    print(
        f"  percentage: "
        f"{signal_counts['percentage']}"
    )

    print(
        f"  fraction: "
        f"{signal_counts['fraction']}"
    )

    print(
        f"  ratio: "
        f"{signal_counts['ratio']}"
    )

    print(
        f"Written to: {output_path}"
    )


if __name__ == "__main__":
    main()