import json
from collections import Counter
from pathlib import Path


INPUT_FILE = Path(
    "experiments/week2September/processed/teacher_trajectories_metadata_50x5.jsonl"
)

OUTPUT_FILE = Path(
    "experiments/week2September/processed/teacher_trajectories_with_skills_50x5.jsonl"
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


def infer_skills(text):

    text = text.lower()

    scores = Counter()

    for skill, keywords in SKILL_KEYWORDS.items():

        for keyword in keywords:

            if keyword in text:
                scores[skill] += 1

    return dict(scores)


def main():

    records = []

    with INPUT_FILE.open(
        "r",
        encoding="utf-8",
    ) as f:

        for line in f:

            if line.strip():
                records.append(
                    json.loads(line)
                )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
    ) as f:

        for record in records:

            text = (
                record["question"]
                + "\n"
                + record["trajectory"]
            )

            skills = infer_skills(text)

            record["skills"] = skills

            record["skill_set"] = list(
                skills.keys()
            )

            f.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                ) + "\n"
            )

    print("=" * 60)
    print("TRAJECTORY SKILL ANALYSIS")
    print("=" * 60)
    print(f"Records: {len(records)}")
    print(f"Output : {OUTPUT_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    main()