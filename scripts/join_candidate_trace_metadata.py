import json
from pathlib import Path


CANDIDATE_INPUT = Path(
    "experiments/week2September/processed/"
    "teacher_correct_student_wrong_trajectories.jsonl"
)

METADATA_INPUT = Path(
    "experiments/week2September/processed/"
    "teacher_trajectories_metadata_50x5.jsonl"
)

OUTPUT = Path(
    "experiments/week2September/processed/"
    "teacher_correct_student_wrong_with_metadata.jsonl"
)


def load_metadata():

    metadata_map = {}

    with METADATA_INPUT.open(
        "r",
        encoding="utf-8"
    ) as f:

        for line in f:

            if not line.strip():
                continue

            item = json.loads(line)

            key = (
                item["question_id"],
                item["trajectory_id"]
            )

            metadata_map[key] = item

    return metadata_map


def main():

    metadata_map = load_metadata()

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    total = 0
    matched = 0
    unmatched = []

    with CANDIDATE_INPUT.open(
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

            key = (
                item["question_id"],
                item["trajectory_id"]
            )

            metadata = metadata_map.get(key)

            if metadata is None:

                unmatched.append(key)

            else:

                item["trajectory_length"] = (
                    metadata.get(
                        "trajectory_length"
                    )
                )

                item["number_of_steps"] = (
                    metadata.get(
                        "number_of_steps"
                    )
                )

                item["number_of_numbers"] = (
                    metadata.get(
                        "number_of_numbers"
                    )
                )

                matched += 1

            outfile.write(
                json.dumps(
                    item,
                    ensure_ascii=False
                ) + "\n"
            )

            total += 1

    print("=" * 60)
    print("JOIN CANDIDATE TRAJECTORIES + TRACE METADATA")
    print("=" * 60)

    print(f"Candidate records : {total}")
    print(f"Matched           : {matched}")
    print(f"Unmatched         : {len(unmatched)}")
    print(f"Output            : {OUTPUT}")

    if unmatched:

        print("\nUnmatched records:")

        for question_id, trajectory_id in unmatched:

            print(
                f"  {question_id} / trajectory {trajectory_id}"
            )

    print("=" * 60)


if __name__ == "__main__":
    main()