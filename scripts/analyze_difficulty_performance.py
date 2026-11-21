import json
from pathlib import Path


INPUT = Path(
    "experiments/week2September/processed/baseline_with_difficulty_100.jsonl"
)

OUTPUT = Path(
    "experiments/week2September/results/difficulty_performance.json"
)


def main():

    with INPUT.open("r", encoding="utf-8") as f:
        data = [
            json.loads(line)
            for line in f
            if line.strip()
        ]

    categories = ["easy", "medium", "hard"]

    results = {}

    for category in categories:

        samples = [
            x for x in data
            if x["difficulty"] == category
        ]

        total = len(samples)

        teacher_correct = sum(
            x["teacher_correct"]
            for x in samples
        )

        student_correct = sum(
            x["student_correct"]
            for x in samples
        )

        results[category] = {
            "samples": total,
            "teacher_correct": teacher_correct,
            "teacher_accuracy":
                teacher_correct / total
                if total else None,
            "student_correct": student_correct,
            "student_accuracy":
                student_correct / total
                if total else None,
        }

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT.open("w", encoding="utf-8") as f:
        json.dump(
            results,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print("=" * 60)
    print("DIFFICULTY PERFORMANCE")
    print("=" * 60)

    for category in categories:

        r = results[category]

        print(
            f"{category.capitalize():8} "
            f"N={r['samples']:3d} | "
            f"Teacher={r['teacher_accuracy']:.2%}"
            if r["teacher_accuracy"] is not None
            else f"{category.capitalize():8} N=0"
        )

        if r["student_accuracy"] is not None:
            print(
                f"{'':8} "
                f"Student={r['student_accuracy']:.2%}"
            )

    print()
    print(f"Output: {OUTPUT}")


if __name__ == "__main__":
    main()