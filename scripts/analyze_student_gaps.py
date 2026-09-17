import json
import re
from collections import Counter
from pathlib import Path


BASELINE_FILE = Path(
    "experiments/week2September/processed/baseline_with_difficulty_100.jsonl"
)

OUTPUT_FILE = Path(
    "experiments/week2September/processed/student_skill_gap.json"
)


SKILL_KEYWORDS = {
    "multiplication": [
        "times",
        "multiply",
        "multiplied",
        "twice",
        "triple",
        "product",
    ],

    "division": [
        "divide",
        "divided",
        "per",
        "each",
        "half",
        "third",
        "quarter",
    ],

    "addition": [
        "total",
        "sum",
        "altogether",
        "combined",
        "add",
        "more",
    ],

    "subtraction": [
        "difference",
        "remaining",
        "left",
        "less",
        "subtract",
        "fewer",
    ],

    "percentage": [
        "percent",
        "%",
        "percentage",
        "increase",
        "decrease",
        "discount",
    ],

    "fraction": [
        "fraction",
        "one-half",
        "one-third",
        "one-fourth",
        "two-thirds",
    ],

    "ratio": [
        "ratio",
        "proportion",
        "times as many",
    ],
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


def infer_skills(question):

    text = question.lower()

    scores = Counter()

    for skill, keywords in SKILL_KEYWORDS.items():

        for keyword in keywords:

            if keyword in text:
                scores[skill] += 1

    return scores


def main():

    data = load_jsonl(BASELINE_FILE)

    wrong_questions = [
        x
        for x in data
        if x["teacher_correct"]
        and not x["student_correct"]
    ]

    skill_counter = Counter()

    question_skills = {}

    for item in wrong_questions:

        scores = infer_skills(
            item["question"]
        )

        question_skills[item["id"]] = dict(
            scores
        )

        for skill, score in scores.items():
            skill_counter[skill] += score

    total = len(wrong_questions)

    if total == 0:
        profile = {}

    else:

        profile = {
            skill: {
                "score": count,
                "normalized_gap":
                    count / total,
            }
            for skill, count
            in skill_counter.most_common()
        }

    result = {
        "num_wrong_teacher_correct":
            total,

        "skill_profile":
            profile,

        "question_skills":
            question_skills,
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
    print("STUDENT SKILL GAP ANALYSIS")
    print("=" * 60)

    print(
        f"Teacher-correct / Student-wrong: "
        f"{total}"
    )

    print()

    for skill, info in profile.items():

        print(
            f"{skill:20s}"
            f"score={info['score']:3d} "
            f"gap={info['normalized_gap']:.3f}"
        )

    print()

    print(
        f"Output: {OUTPUT_FILE}"
    )

    print("=" * 60)


if __name__ == "__main__":
    main()