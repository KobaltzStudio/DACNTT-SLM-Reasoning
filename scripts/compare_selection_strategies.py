import json
import random
from pathlib import Path


INPUT_FILE = Path(
    "experiments/week2September/processed/teacher_trajectories_with_skills_50x5.jsonl"
)

OUTPUT_FILE = Path(
    "experiments/week2September/results/selection_strategy_comparison.json"
)

TOP_K = 2
RANDOM_SEED = 42


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

    random.seed(RANDOM_SEED)

    records = load_jsonl(
        INPUT_FILE
    )

    candidates = [
        x
        for x in records
        if x.get("correct") is True
    ]

    # Random baseline
    random_selected = random.sample(
        candidates,
        min(TOP_K, len(candidates))
    )

    # Difficulty-only
    difficulty_selected = sorted(
        candidates,
        key=lambda x: x.get(
            "difficulty_score",
            0
        ),
        reverse=True,
    )[:TOP_K]

    result = {
        "top_k": TOP_K,
        "random_seed": RANDOM_SEED,

        "random": [
            {
                "question_id":
                    x["question_id"],
                "trajectory_id":
                    x["trajectory_id"],
            }
            for x in random_selected
        ],

        "difficulty_only": [
            {
                "question_id":
                    x["question_id"],
                "trajectory_id":
                    x["trajectory_id"],
            }
            for x in difficulty_selected
        ],
    }

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            result,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print("=" * 60)
    print("SELECTION STRATEGY COMPARISON")
    print("=" * 60)

    print("Random:")
    for x in random_selected:
        print(
            x["question_id"],
            f"T{x['trajectory_id']}"
        )

    print()

    print("Difficulty:")
    for x in difficulty_selected:
        print(
            x["question_id"],
            f"T{x['trajectory_id']}"
        )

    print()

    print(
        f"Output: {OUTPUT_FILE}"
    )

    print("=" * 60)


if __name__ == "__main__":
    main()