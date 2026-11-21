import json
from collections import Counter, defaultdict
from pathlib import Path


INPUT = Path(
    "experiments/week2September/raw/teacher_trajectories_50x5.jsonl"
)

OUTPUT = Path(
    "experiments/week2September/results/multi_trajectory_analysis.json"
)


def normalize(value):
    if value is None:
        return None

    return str(value).strip()


def main():

    with INPUT.open("r", encoding="utf-8") as f:
        data = [
            json.loads(line)
            for line in f
            if line.strip()
        ]

    grouped = defaultdict(list)

    for item in data:
        grouped[item["question_id"]].append(item)

    single_correct = 0
    best_of_n_correct = 0
    majority_correct = 0

    question_results = []

    for question_id, trajectories in grouped.items():

        trajectories = sorted(
            trajectories,
            key=lambda x: x["trajectory_id"]
        )

        ground_truth = trajectories[0]["ground_truth"]

        single = trajectories[0]

        if single["correct"]:
            single_correct += 1

        best_of_n = any(
            x["correct"]
            for x in trajectories
        )

        if best_of_n:
            best_of_n_correct += 1

        answers = [
            normalize(x["predicted_answer"])
            for x in trajectories
            if x["predicted_answer"] is not None
        ]

        counts = Counter(answers)

        majority_answer = (
            counts.most_common(1)[0][0]
            if counts
            else None
        )

        majority_is_correct = (
            majority_answer == normalize(ground_truth)
        )

        if majority_is_correct:
            majority_correct += 1

        unique_answers = len(set(answers))

        lengths = [
            len(x["trajectory"].split())
            for x in trajectories
            if x["trajectory"]
        ]

        question_results.append({
            "question_id": question_id,
            "ground_truth": ground_truth,
            "single_shot_correct": single["correct"],
            "best_of_5_correct": best_of_n,
            "majority_correct": majority_is_correct,
            "majority_answer": majority_answer,
            "unique_final_answers": unique_answers,
            "trajectory_lengths": lengths,
        })

    total_questions = len(grouped)

    result = {
        "questions": total_questions,
        "trajectories_per_question": 5,
        "total_trajectories": len(data),

        "single_shot_accuracy":
            single_correct / total_questions,

        "best_of_5_accuracy":
            best_of_n_correct / total_questions,

        "majority_accuracy":
            majority_correct / total_questions,

        "single_shot_correct":
            single_correct,

        "best_of_5_correct":
            best_of_n_correct,

        "majority_correct":
            majority_correct,

        "question_results":
            question_results,
    }

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT.open("w", encoding="utf-8") as f:
        json.dump(
            result,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print("=" * 60)
    print("MULTI-TRAJECTORY ANALYSIS")
    print("=" * 60)
    print(
        f"Questions       : {total_questions}"
    )
    print(
        f"Trajectories    : {len(data)}"
    )
    print(
        f"Single-shot     : "
        f"{single_correct}/{total_questions} "
        f"= {single_correct / total_questions:.2%}"
    )
    print(
        f"Best-of-5       : "
        f"{best_of_n_correct}/{total_questions} "
        f"= {best_of_n_correct / total_questions:.2%}"
    )
    print(
        f"Majority        : "
        f"{majority_correct}/{total_questions} "
        f"= {majority_correct / total_questions:.2%}"
    )
    print(
        f"Output          : {OUTPUT}"
    )
    print("=" * 60)


if __name__ == "__main__":
    main()