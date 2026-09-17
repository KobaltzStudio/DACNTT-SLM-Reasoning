import json
from pathlib import Path


TRAJECTORY_INPUT = Path(
    "experiments/week2September/processed/"
    "teacher_trajectories_with_metadata_50x5.jsonl"
)

DIFFICULTY_INPUT = Path(
    "experiments/week2September/processed/"
    "difficulty_analysis_100.jsonl"
)

OUTPUT = Path(
    "experiments/week2September/processed/"
    "teacher_trajectories_metadata_50x5.jsonl"
)


def load_difficulty():

    difficulty_map = {}

    with DIFFICULTY_INPUT.open(
        "r",
        encoding="utf-8"
    ) as f:

        for line in f:

            if not line.strip():
                continue

            item = json.loads(line)

            question_id = item["id"]

            difficulty_map[question_id] = {
                "difficulty": item.get("difficulty"),
                "difficulty_score": item.get(
                    "difficulty_score"
                ),
            }

    return difficulty_map


def main():

    difficulty_map = load_difficulty()

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    total = 0
    matched = 0
    unmatched = []

    with TRAJECTORY_INPUT.open(
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

            question_id = item["question_id"]

            difficulty_info = difficulty_map.get(
                question_id
            )

            if difficulty_info is None:

                unmatched.append(
                    question_id
                )

            else:

                item["difficulty"] = (
                    difficulty_info["difficulty"]
                )

                item["difficulty_score"] = (
                    difficulty_info["difficulty_score"]
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
    print("JOIN TRACE METADATA + DIFFICULTY")
    print("=" * 60)

    print(f"Trajectory records : {total}")
    print(f"Matched            : {matched}")
    print(f"Unmatched          : {len(unmatched)}")
    print(f"Output             : {OUTPUT}")

    if unmatched:

        print("\nUnmatched question IDs:")

        for question_id in sorted(
            set(unmatched)
        ):
            print(
                f"  {question_id}"
            )

    print("=" * 60)


if __name__ == "__main__":
    main()