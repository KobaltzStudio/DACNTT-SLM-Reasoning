import json
import re
from pathlib import Path


INPUT = Path("outputs/teacher_student_comparison.jsonl")
OUTPUT = Path("outputs/difficulty_analysis.jsonl")


def extract_numbers(text):
    return re.findall(
        r"\b\d+(?:\.\d+)?(?:/\d+)?%?\b",
        text
    )


def count_operations(text):
    patterns = [
        r"\b(?:twice|double|triple|half|third|quarter)\b",
        r"\b(?:more|less|fewer|times)\b",
        r"[+\-*/=]",
        r"\b(?:percent|percentage)\b",
        r"\b(?:total|remaining|average|profit)\b",
    ]

    return sum(
        len(re.findall(pattern, text.lower()))
        for pattern in patterns
    )


def calculate_difficulty(question):
    numbers = extract_numbers(question)

    question_length = len(question.split())
    num_numbers = len(numbers)
    num_operations = count_operations(question)

    has_fraction_or_percentage = bool(
        re.search(
            r"\b\d+\s*/\s*\d+\b|"
            r"\b\d+(?:\.\d+)?\s*%|"
            r"\b(?:half|third|quarter|fraction|percent|percentage)\b",
            question.lower()
        )
    )

    score = 0

    if question_length > 80:
        score += 2
    elif question_length > 45:
        score += 1

    if num_numbers >= 8:
        score += 2
    elif num_numbers >= 5:
        score += 1

    if num_operations >= 5:
        score += 2
    elif num_operations >= 3:
        score += 1

    if has_fraction_or_percentage:
        score += 2

    if score <= 2:
        difficulty = "easy"
    elif score <= 4:
        difficulty = "medium"
    else:
        difficulty = "hard"

    return {
        "question_length": question_length,
        "num_numbers": num_numbers,
        "num_operations": num_operations,
        "has_fraction_or_percentage": has_fraction_or_percentage,
        "difficulty_score": score,
        "difficulty": difficulty,
    }


def main():
    if not INPUT.exists():
        raise FileNotFoundError(
            f"Input file not found: {INPUT.resolve()}"
        )

    with INPUT.open("r", encoding="utf-8") as f:
        data = [
            json.loads(line)
            for line in f
            if line.strip()
        ]

    if not data:
        raise ValueError(f"Input file is empty: {INPUT}")

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with OUTPUT.open("w", encoding="utf-8") as f:
        for item in data:
            features = calculate_difficulty(
                item["question"]
            )

            record = {
                "id": item["id"],
                "question": item["question"],
                "ground_truth": item["ground_truth"],
                "teacher_answer": item["teacher_answer"],
                "student_answer": item["student_answer"],
                "teacher_correct": item["teacher_correct"],
                "student_correct": item["student_correct"],
                **features,
            }

            f.write(
                json.dumps(
                    record,
                    ensure_ascii=False
                ) + "\n"
            )

    print("=" * 60)
    print("DIFFICULTY ANALYSIS")
    print("=" * 60)
    print(f"Samples : {len(data)}")
    print(f"Input   : {INPUT}")
    print(f"Created : {OUTPUT}")
    print("=" * 60)


if __name__ == "__main__":
    main()