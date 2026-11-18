import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator


BASE = Path(__file__).resolve().parents[1]

SCHEMA_FILE = (
    BASE
    / "schemas"
    / "manual_annotation_schema.json"
)


def load_json(path):
    with path.open(
        "r",
        encoding="utf-8"
    ) as f:
        return json.load(f)


def load_jsonl(path):
    records = []

    with path.open(
        "r",
        encoding="utf-8"
    ) as f:
        for line_number, line in enumerate(f, start=1):

            if not line.strip():
                continue

            try:
                records.append(
                    json.loads(line)
                )

            except json.JSONDecodeError as error:
                print(
                    f"INVALID JSONL: {path}"
                )

                print(
                    f" - Line {line_number}: "
                    f"{error.msg}"
                )

                return None

    return records


def validate_record(
    validator,
    record,
    line_number
):

    errors = sorted(
        validator.iter_errors(record),
        key=lambda e: list(e.path)
    )

    if errors:

        print(
            f"INVALID record at line "
            f"{line_number}"
        )

        for error in errors:
            print(
                f" - {error.message}"
            )

        return False

    return True


def validate_jsonl(path):

    schema = load_json(
        SCHEMA_FILE
    )

    records = load_jsonl(path)

    if records is None:
        return False

    validator = Draft202012Validator(
        schema
    )

    all_valid = True

    for index, record in enumerate(
        records,
        start=1
    ):

        valid = validate_record(
            validator,
            record,
            index
        )

        if not valid:
            all_valid = False

    if all_valid:

        print(
            f"VALID: {path}"
        )

        print(
            f"Records validated: "
            f"{len(records)}"
        )

        return True

    return False


def main():

    if len(sys.argv) != 2:

        print(
            "Usage:"
        )

        print(
            "python "
            "validate_annotation.py "
            "<jsonl>"
        )

        sys.exit(1)

    path = Path(
        sys.argv[1]
    )

    if not path.exists():

        print(
            f"File not found: {path}"
        )

        sys.exit(1)

    valid = validate_jsonl(path)

    sys.exit(
        0 if valid else 1
    )


if __name__ == "__main__":
    main()