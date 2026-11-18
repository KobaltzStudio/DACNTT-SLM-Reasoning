import json
import sys
from pathlib import Path


VALID_CAPABILITIES = {
    "addition",
    "subtraction",
    "multiplication",
    "division",
    "percentage",
    "fraction",
    "ratio",
}

VALID_DIFFICULTIES = {
    "easy",
    "medium",
    "hard",
}


def load_jsonl(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    records = []

    with path.open("r", encoding="utf-8-sig") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON in {path} at line "
                    f"{line_number}: {exc}"
                ) from exc

            if not isinstance(record, dict):
                raise ValueError(
                    f"{path}, line {line_number}: "
                    "each JSONL record must be an object"
                )

            records.append(record)

    return records


def validate_annotation_file(path: Path, expected_annotator: str):
    records = load_jsonl(path)

    if not records:
        raise ValueError(f"{path}: annotation file is empty")

    ids = []

    for index, record in enumerate(records, start=1):
        required_fields = {
            "problem_id",
            "capabilities_manual",
            "difficulty_manual",
            "annotator_id",
            "schema_version",
        }

        missing = required_fields - set(record)

        if missing:
            raise ValueError(
                f"{path}, record {index}: "
                f"missing fields: {sorted(missing)}"
            )

        problem_id = record["problem_id"]

        if not isinstance(problem_id, str) or not problem_id.strip():
            raise ValueError(
                f"{path}, record {index}: invalid problem_id"
            )

        ids.append(problem_id)

        if record["annotator_id"] != expected_annotator:
            raise ValueError(
                f"{path}, {problem_id}: "
                f"annotator_id={record['annotator_id']!r}, "
                f"expected {expected_annotator!r}"
            )

        if record["schema_version"] != "v1":
            raise ValueError(
                f"{path}, {problem_id}: unsupported "
                f"schema_version={record['schema_version']!r}"
            )

        capabilities = record["capabilities_manual"]

        if not isinstance(capabilities, list) or not capabilities:
            raise ValueError(
                f"{path}, {problem_id}: "
                "capabilities_manual must be a non-empty list"
            )

        if not all(isinstance(x, str) for x in capabilities):
            raise ValueError(
                f"{path}, {problem_id}: capability values must be strings"
            )

        if len(capabilities) != len(set(capabilities)):
            raise ValueError(
                f"{path}, {problem_id}: duplicate capability labels"
            )

        unknown = set(capabilities) - VALID_CAPABILITIES

        if unknown:
            raise ValueError(
                f"{path}, {problem_id}: "
                f"unknown capabilities: {sorted(unknown)}"
            )

        difficulty = record["difficulty_manual"]

        if difficulty not in VALID_DIFFICULTIES:
            raise ValueError(
                f"{path}, {problem_id}: "
                f"invalid difficulty={difficulty!r}"
            )

    duplicates = sorted(
        problem_id
        for problem_id in set(ids)
        if ids.count(problem_id) > 1
    )

    if duplicates:
        raise ValueError(
            f"{path}: duplicate problem IDs: {duplicates}"
        )

    return records


def main():
    if len(sys.argv) != 3:
        print(
            "Usage:\n"
            "python check_annotation_alignment.py "
            "<A1.jsonl> <A2.jsonl>"
        )
        sys.exit(1)

    a1_path = Path(sys.argv[1])
    a2_path = Path(sys.argv[2])

    a1 = validate_annotation_file(a1_path, "A1")
    a2 = validate_annotation_file(a2_path, "A2")

    ids_a1 = [record["problem_id"] for record in a1]
    ids_a2 = [record["problem_id"] for record in a2]

    set_a1 = set(ids_a1)
    set_a2 = set(ids_a2)

    missing_in_a2 = sorted(set_a1 - set_a2)
    missing_in_a1 = sorted(set_a2 - set_a1)

    if len(a1) != len(a2):
        raise ValueError(
            "A1/A2 record count mismatch.\n"
            f"A1 records: {len(a1)}\n"
            f"A2 records: {len(a2)}"
        )

    if missing_in_a2 or missing_in_a1:
        raise ValueError(
            "Problem ID mismatch.\n"
            f"Missing in A2: {missing_in_a2}\n"
            f"Missing in A1: {missing_in_a1}"
        )

    if ids_a1 != ids_a2:
        print(
            "WARNING: A1 and A2 contain the same IDs "
            "but in different order."
        )

    print("A1/A2 alignment: OK")
    print(f"A1 records: {len(a1)}")
    print(f"A2 records: {len(a2)}")
    print("Problem ID sets: identical")
    print("Annotator IDs: A1 / A2")
    print("Capabilities: valid")
    print("Difficulty labels: valid")


if __name__ == "__main__":
    main()
