import json
from pathlib import Path
from collections import Counter


INPUT = Path("outputs/teacher_student_comparison.jsonl")
OUTPUT = Path("outputs/rationale_selection_day06.jsonl")


def classify_case(item):
    teacher_correct = bool(item["teacher_correct"])
    student_correct = bool(item["student_correct"])

    if teacher_correct and not student_correct:
        return "teacher_correct_student_wrong"

    if not teacher_correct and student_correct:
        return "teacher_wrong_student_correct"

    if teacher_correct and student_correct:
        return "both_correct"

    return "both_wrong"


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
        raise ValueError(
            f"Input file is empty: {INPUT}"
        )

    # ---------------------------------------------------------
    # 3. Classify all cases
    # ---------------------------------------------------------
    case_distribution = Counter()

    for item in data:
        case_type = classify_case(item)
        case_distribution[case_type] += 1

    # ---------------------------------------------------------
    # 4. Select rationale cases
    # ---------------------------------------------------------
    selected = []

    for item in data:
        case_type = classify_case(item)

        # Ưu tiên tuyệt đối:
        # Teacher đúng / Student sai
        if case_type == "teacher_correct_student_wrong":
            priority = 1

            selected.append({
                "id": item["id"],
                "priority": priority,
                "case_type": case_type,
                "question": item["question"],
                "ground_truth": item["ground_truth"],
                "teacher_answer": item["teacher_answer"],
                "student_answer": item["student_answer"],
                "student_output": item.get(
                    "student_output",
                    ""
                ),
                "teacher_model": item.get(
                    "teacher_model"
                ),
                "student_model": item.get(
                    "student_model"
                ),
            })

    # ---------------------------------------------------------
    # 5. Write selected rationale cases
    # ---------------------------------------------------------
    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with OUTPUT.open("w", encoding="utf-8") as f:
        for item in selected:
            f.write(
                json.dumps(
                    item,
                    ensure_ascii=False
                ) + "\n"
            )

    # ---------------------------------------------------------
    # 6. Console report
    # ---------------------------------------------------------
    total = len(data)

    print("=" * 60)
    print("RATIONALE SELECTION")
    print("=" * 60)

    print(f"Input          : {INPUT}")
    print(f"Total samples  : {total}")
    print(f"Selected cases : {len(selected)}")
    print()

    print("CASE DISTRIBUTION")
    print("-" * 60)

    case_types = [
        "teacher_correct_student_wrong",
        "teacher_wrong_student_correct",
        "both_correct",
        "both_wrong",
    ]

    for case_type in case_types:
        count = case_distribution.get(
            case_type,
            0
        )

        percentage = (
            count / total * 100
            if total > 0
            else 0
        )

        print(
            f"{case_type:<35} "
            f"{count:>3} "
            f"({percentage:>6.2f}%)"
        )

    print()
    print(f"Created        : {OUTPUT}")
    print("=" * 60)


if __name__ == "__main__":
    main()