import json
import re
from pathlib import Path


INPUT_FILE = Path(
    "experiments/week2September/raw/teacher_trajectories_50x5.jsonl"
)

OUTPUT_FILE = Path(
    "experiments/week2September/processed/teacher_trajectories_reevaluated_50x5.jsonl"
)


def normalize_number(value):
    if value is None:
        return None

    value = str(value).strip()
    value = value.replace(",", "")
    value = value.replace("$", "")

    try:
        number = float(value)

        if number.is_integer():
            return str(int(number))

        return str(number)

    except ValueError:
        return value


def extract_answer(text):
    if not text:
        return None

    patterns = [
        r"####\s*<?\s*(-?\d+(?:\.\d+)?)\s*>?",
        r"(?:final answer|answer)\s*[:=]?\s*(-?\d+(?:\.\d+)?)",
    ]

    for pattern in patterns:
        matches = re.findall(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        if matches:
            value = matches[-1]

            try:
                number = float(value)

                if number.is_integer():
                    return str(int(number))

                return str(number)

            except ValueError:
                return value

    return None


def answers_equal(a, b):
    return normalize_number(a) == normalize_number(b)


def load_jsonl(path):
    records = []

    with path.open(
        "r",
        encoding="utf-8",
    ) as f:

        for line in f:
            if line.strip():
                records.append(json.loads(line))

    return records


def main():

    records = load_jsonl(INPUT_FILE)

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    correct_count = 0
    null_count = 0

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
    ) as f:

        for record in records:

            trajectory = record.get(
                "trajectory"
            )

            ground_truth = record.get(
                "ground_truth"
            )

            predicted_answer = extract_answer(
                trajectory
            )

            correct = answers_equal(
                predicted_answer,
                ground_truth,
            )

            new_record = dict(record)

            new_record[
                "predicted_answer"
            ] = predicted_answer

            new_record[
                "correct"
            ] = correct

            f.write(
                json.dumps(
                    new_record,
                    ensure_ascii=False,
                ) + "\n"
            )

            if predicted_answer is None:
                null_count += 1

            if correct:
                correct_count += 1

    print("=" * 60)
    print("RE-EVALUATE TEACHER TRAJECTORIES")
    print("=" * 60)
    print(f"Input records : {len(records)}")
    print(f"Correct       : {correct_count}")
    print(f"Incorrect     : {len(records) - correct_count}")
    print(f"Answer null   : {null_count}")
    print(f"Output        : {OUTPUT_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    main()