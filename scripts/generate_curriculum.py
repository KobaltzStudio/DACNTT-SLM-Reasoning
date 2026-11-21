import json
from collections import defaultdict
from pathlib import Path


INPUT_FILE = Path(
    "experiments/week2September/processed/teacher_trajectories_metadata_50x5.jsonl"
)

OUTPUT_FILE = Path(
    "experiments/week2September/processed/curriculum.jsonl"
)


CATEGORY_ORDER = {
    "easy": 0,
    "medium": 1,
    "hard": 2,
}


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

    records = load_jsonl(
        INPUT_FILE
    )

    questions = {}

    for record in records:

        question_id = record[
            "question_id"
        ]

        if question_id not in questions:

            questions[question_id] = {
                "question_id":
                    question_id,
                "question":
                    record["question"],
                "difficulty":
                    record["difficulty"],
                "difficulty_score":
                    record["difficulty_score"],
                "trajectory_ids": [],
            }

        questions[
            question_id
        ]["trajectory_ids"].append(
            record["trajectory_id"]
        )

    curriculum = sorted(
        questions.values(),
        key=lambda x: (
            CATEGORY_ORDER.get(
                x["difficulty"],
                99,
            ),
            x["difficulty_score"],
            x["question_id"],
        ),
    )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
    ) as f:

        for index, item in enumerate(
            curriculum
        ):

            category = item[
                "difficulty"
            ]

            stage = (
                CATEGORY_ORDER.get(
                    category,
                    99,
                ) + 1
            )

            output = {
                "curriculum_order":
                    index + 1,

                "curriculum_stage":
                    stage,

                "difficulty_category":
                    category,

                "difficulty_score":
                    item[
                        "difficulty_score"
                    ],

                "question_id":
                    item["question_id"],

                "question":
                    item["question"],

                "trajectory_ids":
                    sorted(
                        item[
                            "trajectory_ids"
                        ]
                    ),
            }

            f.write(
                json.dumps(
                    output,
                    ensure_ascii=False,
                ) + "\n"
            )

    print("=" * 60)
    print("AUTOMATIC CURRICULUM")
    print("=" * 60)

    print(
        f"Questions: {len(curriculum)}"
    )

    for category in [
        "easy",
        "medium",
        "hard",
    ]:

        count = sum(
            x["difficulty_category"]
            == category
            for x in curriculum
        )

        print(
            f"{category:10s}: {count}"
        )

    print()

    print(
        f"Output: {OUTPUT_FILE}"
    )

    print("=" * 60)


if __name__ == "__main__":
    main()