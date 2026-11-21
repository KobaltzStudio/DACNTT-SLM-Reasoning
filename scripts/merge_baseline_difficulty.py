import json
from pathlib import Path


BASELINE = Path(
    "experiments/week2September/raw/teacher_student_baseline_100.jsonl"
)

DIFFICULTY = Path(
    "experiments/week2September/processed/difficulty_analysis_100.jsonl"
)

OUTPUT = Path(
    "experiments/week2September/processed/baseline_with_difficulty_100.jsonl"
)


def load_jsonl(path):
    with path.open("r", encoding="utf-8") as f:
        return [
            json.loads(line)
            for line in f
            if line.strip()
        ]


def main():

    if not BASELINE.exists():
        raise FileNotFoundError(BASELINE)

    if not DIFFICULTY.exists():
        raise FileNotFoundError(DIFFICULTY)

    baseline = load_jsonl(BASELINE)
    difficulty = load_jsonl(DIFFICULTY)

    baseline_by_id = {
        item["id"]: item
        for item in baseline
    }

    difficulty_by_id = {
        item["id"]: item
        for item in difficulty
    }

    baseline_ids = set(baseline_by_id)
    difficulty_ids = set(difficulty_by_id)

    if baseline_ids != difficulty_ids:
        missing_in_difficulty = baseline_ids - difficulty_ids
        missing_in_baseline = difficulty_ids - baseline_ids

        raise ValueError(
            f"ID mismatch.\n"
            f"Missing in difficulty: {missing_in_difficulty}\n"
            f"Missing in baseline: {missing_in_baseline}"
        )

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT.open("w", encoding="utf-8") as f:

        for sample_id in baseline_by_id:

            base = baseline_by_id[sample_id]
            diff = difficulty_by_id[sample_id]

            record = {
                "id": sample_id,
                "question": base["question"],
                "ground_truth": base["ground_truth"],
                "teacher_answer": base["teacher_answer"],
                "student_answer": base["student_answer"],
                "teacher_correct": base["teacher_correct"],
                "student_correct": base["student_correct"],

                "question_length": diff["question_length"],
                "num_numbers": diff["num_numbers"],
                "num_operations": diff["num_operations"],
                "has_fraction_or_percentage":
                    diff["has_fraction_or_percentage"],
                "difficulty_score":
                    diff["difficulty_score"],
                "difficulty":
                    diff["difficulty"],
            }

            f.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                ) + "\n"
            )

    print("=" * 60)
    print("BASELINE + DIFFICULTY MERGE")
    print("=" * 60)
    print(f"Baseline samples : {len(baseline)}")
    print(f"Difficulty samples: {len(difficulty)}")
    print(f"Merged samples   : {len(baseline)}")
    print(f"Output           : {OUTPUT}")
    print("=" * 60)


if __name__ == "__main__":
    main()