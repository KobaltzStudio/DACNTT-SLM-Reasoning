import json
import sys
from pathlib import Path


ALLOWED_CAPABILITIES = {
    "addition",
    "subtraction",
    "multiplication",
    "division",
    "percentage",
    "fraction",
    "ratio",
}


def fail(message):
    print(f"INVALID: {message}")
    raise SystemExit(1)


def main():
    if len(sys.argv) != 2:
        print(
            "Usage: python validate_trajectory.py <trajectory.json>"
        )
        raise SystemExit(2)

    path = Path(sys.argv[1])

    if not path.exists():
        fail(f"File not found: {path}")

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        fail(f"Invalid JSON: {exc}")

    required = {
        "problem_id",
        "teacher_model",
        "trajectory_id",
        "checkpoint",
        "reasoning_trace",
        "answer",
        "capabilities",
        "metadata",
    }

    missing = required - set(data)

    if missing:
        fail(f"Missing fields: {sorted(missing)}")

    if not isinstance(data["capabilities"], list):
        fail("'capabilities' must be a list")

    if not data["capabilities"]:
        fail("'capabilities' must not be empty")

    unknown = (
        set(data["capabilities"])
        - ALLOWED_CAPABILITIES
    )

    if unknown:
        fail(
            f"Unknown capabilities: {sorted(unknown)}"
        )

    metadata = data["metadata"]

    if not isinstance(metadata, dict):
        fail("'metadata' must be an object")

    for field in ("num_steps", "token_length"):
        if field not in metadata:
            fail(
                f"Metadata missing field: {field}"
            )

        if not isinstance(metadata[field], int):
            fail(
                f"Metadata field '{field}' must be integer"
            )

        if metadata[field] < 1:
            fail(
                f"Metadata field '{field}' must be >= 1"
            )

    print(f"VALID: {path}")
    print(f"Problem: {data['problem_id']}")
    print(f"Trajectory: {data['trajectory_id']}")


if __name__ == "__main__":
    main()