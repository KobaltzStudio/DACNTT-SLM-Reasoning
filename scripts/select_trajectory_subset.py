import json
import random
from pathlib import Path


INPUT = Path(
    "experiments/week2September/processed/baseline_with_difficulty_100.jsonl"
)

OUTPUT = Path(
    "experiments/week2September/processed/trajectory_questions_50.jsonl"
)

SEED = 42
NUM_SAMPLES = 50


def main():

    with INPUT.open("r", encoding="utf-8") as f:
        data = [
            json.loads(line)
            for line in f
            if line.strip()
        ]

    if NUM_SAMPLES > len(data):
        raise ValueError(
            "Requested subset is larger than dataset."
        )

    rng = random.Random(SEED)

    selected = rng.sample(
        data,
        NUM_SAMPLES,
    )

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT.open("w", encoding="utf-8") as f:

        for item in selected:

            record = {
                "id": item["id"],
                "question": item["question"],
                "ground_truth": item["ground_truth"],
                "teacher_correct": item["teacher_correct"],
                "student_correct": item["student_correct"],
                "difficulty": item["difficulty"],
                "difficulty_score": item["difficulty_score"],
            }

            f.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                ) + "\n"
            )

    print("=" * 60)
    print("TRAJECTORY SUBSET")
    print("=" * 60)
    print(f"Original : {len(data)}")
    print(f"Selected : {len(selected)}")
    print(f"Seed     : {SEED}")
    print(f"Output   : {OUTPUT}")
    print("=" * 60)


if __name__ == "__main__":
    main()