import json
import re
from pathlib import Path


INPUT = Path(
    "experiments/week2September/raw/teacher_trajectories_50x5.jsonl"
)

OUTPUT = Path(
    "experiments/week2September/processed/teacher_trajectories_with_metadata_50x5.jsonl"
)


def count_steps(trajectory):
    """
    Count explicit reasoning steps.

    Supports formats such as:
        Step 1
        step 1
        1.
        2.
        ### Step 1
        **Step 1**
    """

    patterns = [
        # Step 1 / step 1 / STEP 1
        r"\b(?:Step|step)\s*\d+\b",

        # Numbered list at beginning of a line:
        # 1.
        # 2.
        # 3)
        r"(?m)^\s*\d+[\.\)]\s+",
    ]

    matches = set()

    for pattern in patterns:
        for match in re.finditer(pattern, trajectory):
            matches.add(match.group(0))

    # The patterns above can count the same conceptual step twice
    # when "Step 1" is preceded by a numbered list.
    #
    # Therefore count line-level step markers first.
    line_step_matches = re.findall(
        r"(?m)^\s*(?:#{1,6}\s*)?(?:\*\*)?"
        r"(?:Step|step)\s*\d+"
        r"(?:\*\*)?",
        trajectory
    )

    numbered_step_matches = re.findall(
        r"(?m)^\s*\d+[\.\)]\s+\S+",
        trajectory
    )

    # If explicit "Step N" exists, use those.
    if line_step_matches:
        return len(line_step_matches)

    # Otherwise use numbered list items.
    return len(numbered_step_matches)


def count_numbers(trajectory):
    """
    Count numeric expressions appearing in the trajectory.

    Examples:
        20
        15
        2/3 -> counts 2 and 3
        10.5
        300
    """

    return len(
        re.findall(
            r"\b\d+(?:\.\d+)?\b",
            trajectory
        )
    )


def process_record(item):
    trajectory = item.get("trajectory", "")

    item["trajectory_length"] = len(
        trajectory.split()
    )

    item["number_of_steps"] = count_steps(
        trajectory
    )

    item["number_of_numbers"] = count_numbers(
        trajectory
    )

    return item


def main():

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    count = 0

    with INPUT.open(
        "r",
        encoding="utf-8"
    ) as infile, OUTPUT.open(
        "w",
        encoding="utf-8"
    ) as outfile:

        for line in infile:

            if not line.strip():
                continue

            item = json.loads(line)

            item = process_record(item)

            outfile.write(
                json.dumps(
                    item,
                    ensure_ascii=False
                ) + "\n"
            )

            count += 1

    print("=" * 60)
    print("TRACE-LEVEL STRUCTURAL METADATA")
    print("=" * 60)

    print(f"Input       : {INPUT}")
    print(f"Output      : {OUTPUT}")
    print(f"Trajectories: {count}")

    print("=" * 60)


if __name__ == "__main__":
    main()