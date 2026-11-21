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


def load_jsonl(path):
    with path.open(
        "r",
        encoding="utf-8",
    ) as f:
        return [
            json.loads(line)
            for line in f
            if line.strip()
        ]


def main():

    trajectories = load_jsonl(
        TRAJECTORY_INPUT
    )

    difficulty_data = load_jsonl(
        DIFFICULTY_INPUT
    )

    # Detect difficulty key automatically.
    difficulty_by_id = {}

    for item in difficulty_data:

        question_id = (
            item.get("question_id")
            or item.get("id")
        )

        if question_id is None:
            continue

        difficulty_by_id[question_id] = item

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    matched = 0
    unmatched = 0

    with OUTPUT.open(
        "w",
        encoding="utf-8",
    ) as f:

        for item in trajectories:

            question_id = item.get(
                "question_id"
            )

            difficulty_item = (
                difficulty_by_id.get(
                    question_id
                )
            )

            if difficulty_item is None:
                unmatched += 1

                print(
                    f"[WARNING] No difficulty "
                    f"for {question_id}"
                )

                continue

            # Prefer existing difficulty values
            # from the difficulty analysis.
            if "difficulty" in difficulty_item:
                item["difficulty"] = (
                    difficulty_item["difficulty"]
                )

            if "difficulty_score" in difficulty_item:
                item["difficulty_score"] = (
                    difficulty_item["difficulty_score"]
                )

            matched += 1

            f.write(
                json.dumps(
                    item,
                    ensure_ascii=False,
                )
                + "\n"
            )

    print("=" * 60)
    print("MERGE TRAJECTORY + DIFFICULTY")
    print("=" * 60)
    print(f"Trajectories : {len(trajectories)}")
    print(f"Matched      : {matched}")
    print(f"Unmatched    : {unmatched}")
    print(f"Output       : {OUTPUT}")
    print("=" * 60)


if __name__ == "__main__":
    main()