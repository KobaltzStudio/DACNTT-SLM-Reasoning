import json
from pathlib import Path


BASELINE = Path(
    "experiments/week2September/processed/"
    "baseline_with_difficulty_100.jsonl"
)

TRAJECTORIES = Path(
    "experiments/week2September/processed/"
    "teacher_trajectories_reevaluated_50x5.jsonl"
)

OUTPUT = Path(
    "experiments/week2September/processed/"
    "teacher_correct_student_wrong_with_metadata.jsonl"
)


def load_jsonl(path):
    with path.open("r", encoding="utf-8") as f:
        return [
            json.loads(line)
            for line in f
            if line.strip()
        ]


def main():

    baseline = load_jsonl(BASELINE)
    trajectories = load_jsonl(TRAJECTORIES)

    # ---------------------------------------------------------
    # 1. Identify Teacher-correct / Student-wrong questions
    # ---------------------------------------------------------

    eligible = {
        x["id"]: x
        for x in baseline
        if x.get("teacher_correct") is True
        and x.get("student_correct") is False
    }

    # ---------------------------------------------------------
    # 2. Select trajectories belonging to eligible questions
    # ---------------------------------------------------------

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    count = 0
    correct_count = 0
    incorrect_count = 0
    null_count = 0

    with OUTPUT.open(
        "w",
        encoding="utf-8",
    ) as f:

        for trajectory in trajectories:

            question_id = trajectory["question_id"]

            if question_id not in eligible:
                continue

            base = eligible[question_id]

            predicted_answer = trajectory.get(
                "predicted_answer"
            )

            trajectory_correct = trajectory.get(
                "correct",
                False,
            )

            record = {
                "question_id": question_id,

                "trajectory_id":
                    trajectory["trajectory_id"],

                "question":
                    trajectory["question"],

                "trajectory":
                    trajectory.get("trajectory"),

                "predicted_answer":
                    predicted_answer,

                "ground_truth":
                    trajectory["ground_truth"],

                "trajectory_correct":
                    trajectory_correct,

                "teacher_baseline_correct":
                    base["teacher_correct"],

                "student_baseline_correct":
                    base["student_correct"],

                "difficulty":
                    base["difficulty"],

                "difficulty_score":
                    base["difficulty_score"],

                # Preserve trajectory generation metadata
                "model":
                    trajectory.get("model"),

                "temperature":
                    trajectory.get("temperature"),

                "max_tokens":
                    trajectory.get("max_tokens"),

                "elapsed_seconds":
                    trajectory.get("elapsed_seconds"),
            }

            if predicted_answer is None:
                null_count += 1
            elif trajectory_correct:
                correct_count += 1
            else:
                incorrect_count += 1

            f.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                ) + "\n"
            )

            count += 1

    # ---------------------------------------------------------
    # 3. Print summary
    # ---------------------------------------------------------

    print("=" * 60)
    print("TEACHER-CORRECT / STUDENT-WRONG")
    print("=" * 60)

    print(
        f"Eligible questions      : {len(eligible)}"
    )

    print(
        f"Candidate trajectories  : {count}"
    )

    print(
        f"Correct trajectories    : {correct_count}"
    )

    print(
        f"Incorrect trajectories  : {incorrect_count}"
    )

    print(
        f"Null answers            : {null_count}"
    )

    print(
        f"Output                  : {OUTPUT}"
    )

    print("=" * 60)


if __name__ == "__main__":
    main()