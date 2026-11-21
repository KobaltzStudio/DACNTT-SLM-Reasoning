import json
from pathlib import Path


INPUT = Path("outputs/teacher_student_comparison.jsonl")
SUMMARY = Path("notes/baseline_comparison.md")


def main():
    # ---------------------------------------------------------
    # 1. Check input
    # ---------------------------------------------------------
    if not INPUT.exists():
        raise FileNotFoundError(
            f"Input file not found: {INPUT.resolve()}"
        )

    # ---------------------------------------------------------
    # 2. Load JSONL
    # ---------------------------------------------------------
    with INPUT.open("r", encoding="utf-8") as f:
        data = [
            json.loads(line)
            for line in f
            if line.strip()
        ]

    if not data:
        raise ValueError(f"Input file is empty: {INPUT}")

    # ---------------------------------------------------------
    # 3. Calculate accuracy
    # ---------------------------------------------------------
    total = len(data)

    teacher_correct = sum(
        bool(x["teacher_correct"])
        for x in data
    )

    student_correct = sum(
        bool(x["student_correct"])
        for x in data
    )

    teacher_acc = teacher_correct / total
    student_acc = student_correct / total
    gap = teacher_acc - student_acc

    # ---------------------------------------------------------
    # 4. Create notes directory
    # ---------------------------------------------------------
    SUMMARY.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    # ---------------------------------------------------------
    # 5. Create Markdown report
    # ---------------------------------------------------------
    lines = [
        "# Teacher-Student Baseline Comparison",
        "",
        "## Overall Results",
        "",
        f"- Total samples: {total}",
        f"- Teacher: {teacher_correct}/{total} = {teacher_acc:.2%}",
        f"- Student: {student_correct}/{total} = {student_acc:.2%}",
        f"- Accuracy gap: {gap:.2%}",
        "",
        "## Error Analysis",
        "",
    ]

    for x in data:
        teacher_ok = bool(x["teacher_correct"])
        student_ok = bool(x["student_correct"])

        if teacher_ok != student_ok:
            if teacher_ok and not student_ok:
                status = "Teacher correct, Student wrong"
            else:
                status = "Teacher wrong, Student correct"

            lines.extend([
                f"### {x['id']}",
                "",
                f"- Status: {status}",
                f"- Ground truth: `{x['ground_truth']}`",
                f"- Teacher: `{x['teacher_answer']}`",
                f"- Student: `{x['student_answer']}`",
                "",
            ])

    # ---------------------------------------------------------
    # 6. Save Markdown report
    # ---------------------------------------------------------
    with SUMMARY.open("w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    # ---------------------------------------------------------
    # 7. Console output
    # ---------------------------------------------------------
    print("=" * 60)
    print("BASELINE SUMMARY")
    print("=" * 60)
    print(f"Samples       : {total}")
    print(f"Teacher       : {teacher_correct}/{total} = {teacher_acc:.2%}")
    print(f"Student       : {student_correct}/{total} = {student_acc:.2%}")
    print(f"Accuracy gap  : {gap:.2%}")
    print()
    print(f"Input         : {INPUT}")
    print(f"Created       : {SUMMARY}")
    print("=" * 60)


if __name__ == "__main__":
    main()