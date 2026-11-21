import json
import sys
from pathlib import Path


BASE = Path(__file__).resolve().parents[1]


def load_jsonl(path: Path):
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
            "Record does not contain "
            "'problem_id' or 'id'."
        )

    return str(problem_id)


def main():
    if len(sys.argv) != 4:
        print(
            "Usage:\n"
            "python remove_existing_annotations.py "
            "<candidates.jsonl> "
            "<existing_annotations.jsonl> "
            "<output.jsonl>"
        )
        sys.exit(1)

    candidates_path = Path(sys.argv[1])
    existing_path = Path(sys.argv[2])
    output_path = Path(sys.argv[3])

    candidates = load_jsonl(
        candidates_path
    )

    existing = load_jsonl(
        existing_path
    )

    existing_ids = {
        get_problem_id(record)
        for record in existing
    }

    filtered = []
    removed = []

    seen_candidate_ids = set()

    for record in candidates:
        problem_id = get_problem_id(record)

        if problem_id in seen_candidate_ids:
            raise ValueError(
                f"Duplicate candidate ID: "
                f"{problem_id}"
            )

        seen_candidate_ids.add(problem_id)

        if problem_id in existing_ids:
            removed.append(problem_id)
        else:
            filtered.append(record)

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as f:
        for record in filtered:
            f.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                )
                + "\n"
            )

    print(
        f"Candidate records before filtering: "
        f"{len(candidates)}"
    )

    print(
        f"Existing annotation IDs: "
        f"{len(existing_ids)}"
    )

    print(
        f"Removed existing records: "
        f"{len(removed)}"
    )

    print(
        f"Remaining supplement candidates: "
        f"{len(filtered)}"
    )

    print(
        f"Written to: {output_path}"
    )

    if removed:
        print()
        print(
            "Removed IDs:"
        )

        for problem_id in sorted(removed):
            print(
                f"  {problem_id}"
            )


if __name__ == "__main__":
    main()