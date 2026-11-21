import argparse
import json
from pathlib import Path


CAPABILITIES = {
    "addition",
    "subtraction",
    "multiplication",
    "division",
    "percentage",
    "fraction",
    "ratio",
}


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def validate(data):

    required = {
        "student_id",
        "status",
        "checkpoints",
        "capabilities",
    }

    missing = required - set(data)

    if missing:
        raise ValueError(
            f"Missing required fields: {sorted(missing)}"
        )

    if data["status"] not in {
        "synthetic",
        "empirical",
    }:
        raise ValueError(
            f"Invalid status: {data['status']}"
        )

    checkpoint_ids = [
        checkpoint["checkpoint_id"]
        for checkpoint in data["checkpoints"]
    ]

    if len(checkpoint_ids) != len(set(checkpoint_ids)):
        raise ValueError(
            "Duplicate checkpoint_id detected."
        )

    capability_names = []

    for capability_data in data["capabilities"]:

        capability = capability_data["capability"]

        if capability not in CAPABILITIES:
            raise ValueError(
                f"Invalid capability: {capability}"
            )

        capability_names.append(
            capability
        )

        observation_ids = [
            observation["checkpoint_id"]
            for observation in capability_data[
                "observations"
            ]
        ]

        if observation_ids != checkpoint_ids:
            raise ValueError(
                f"Checkpoint mismatch for capability: "
                f"{capability}"
            )

        for observation in capability_data[
            "observations"
        ]:

            mastery = observation["mastery"]

            if not 0 <= mastery <= 1:
                raise ValueError(
                    f"Mastery out of range for "
                    f"{capability}: {mastery}"
                )

            if observation.get(
                "delta"
            ) is not None:

                delta = observation["delta"]

                if not -1 <= delta <= 1:
                    raise ValueError(
                        f"Delta out of range for "
                        f"{capability}: {delta}"
                    )

    if len(capability_names) != len(
        set(capability_names)
    ):
        raise ValueError(
            "Duplicate capability detected."
        )


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "input",
        type=Path
    )

    args = parser.parse_args()

    data = load_json(args.input)

    validate(data)

    print(
        f"VALID: {args.input}"
    )

    print(
        f"Checkpoints validated: "
        f"{len(data['checkpoints'])}"
    )

    print(
        f"Capabilities validated: "
        f"{len(data['capabilities'])}"
    )


if __name__ == "__main__":
    main()