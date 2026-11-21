import json
import time
from pathlib import Path

from openai import OpenAI


BASE_URL = "http://localhost:1234/v1"
MODEL = "qwen2.5-3b-instruct"

INPUT_FILE = Path(
    "experiments/week2September/processed/trajectory_questions_50.jsonl"
)

OUTPUT_FILE = Path(
    "experiments/week2September/raw/teacher_trajectories_50x5.jsonl"
)

NUM_TRAJECTORIES = 5
TEMPERATURE = 0.7
MAX_TOKENS = 512
REQUEST_TIMEOUT = 120


SYSTEM_PROMPT = """
You are a mathematical reasoning teacher.

Solve the given GSM8K problem carefully.

Requirements:
1. Show the reasoning step by step.
2. Perform all necessary calculations.
3. Do not skip important intermediate steps.
4. At the end, provide the final numerical answer.
5. End your response with:

#### <number>

Do not put additional text after the final answer.
""".strip()


def extract_answer(text):
    import re

    if not text:
        return None

    patterns = [
        # #### 12
        r"####\s*<?\s*(-?\d+(?:\.\d+)?)\s*>?",

        # #### <12>
        r"####\s*<\s*(-?\d+(?:\.\d+)?)\s*>",

        # final answer: 12
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


def answers_equal(a, b):

    return (
        normalize_number(a)
        == normalize_number(b)
    )


def load_existing():

    if not OUTPUT_FILE.exists():
        return {}

    existing = {}

    with OUTPUT_FILE.open(
        "r",
        encoding="utf-8",
    ) as f:

        for line in f:

            if not line.strip():
                continue

            record = json.loads(line)

            key = (
                record["question_id"],
                record["trajectory_id"],
            )

            existing[key] = record

    return existing


def main():

    with INPUT_FILE.open(
        "r",
        encoding="utf-8",
    ) as f:

        questions = [
            json.loads(line)
            for line in f
            if line.strip()
        ]

    client = OpenAI(
        base_url=BASE_URL,
        api_key="lm-studio",
        timeout=REQUEST_TIMEOUT,
    )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    existing = load_existing()

    total = len(questions) * NUM_TRAJECTORIES

    completed = 0

    print("=" * 60)
    print("TEACHER MULTI-TRAJECTORY GENERATION")
    print("=" * 60)
    print(f"Questions    : {len(questions)}")
    print(f"Trajectories : {NUM_TRAJECTORIES}")
    print(f"Total        : {total}")
    print(f"Temperature  : {TEMPERATURE}")
    print(f"Model        : {MODEL}")
    print(f"Output       : {OUTPUT_FILE}")
    print("=" * 60)

    for q_index, question_data in enumerate(
        questions,
        start=1,
    ):

        question_id = question_data["id"]
        question = question_data["question"]
        ground_truth = question_data["ground_truth"]

        for trajectory_id in range(
            NUM_TRAJECTORIES
        ):

            key = (
                question_id,
                trajectory_id,
            )

            if key in existing:

                completed += 1

                print(
                    f"[{completed}/{total}] "
                    f"{question_id} "
                    f"T{trajectory_id} SKIP"
                )

                continue

            print(
                f"[{completed + 1}/{total}] "
                f"{question_id} "
                f"T{trajectory_id}"
            )

            start = time.perf_counter()

            try:

                response = (
                    client.chat.completions.create(
                        model=MODEL,
                        messages=[
                            {
                                "role": "system",
                                "content": SYSTEM_PROMPT,
                            },
                            {
                                "role": "user",
                                "content":
                                    "Solve this GSM8K problem.\n\n"
                                    + question,
                            },
                        ],
                        temperature=TEMPERATURE,
                        max_tokens=MAX_TOKENS,
                    )
                )

                elapsed = (
                    time.perf_counter()
                    - start
                )

                trajectory = (
                    response
                    .choices[0]
                    .message
                    .content
                    or ""
                )

                predicted_answer = (
                    extract_answer(trajectory)
                )

                correct = answers_equal(
                    predicted_answer,
                    ground_truth,
                )

                record = {
                    "question_id": question_id,
                    "trajectory_id": trajectory_id,
                    "question": question,
                    "trajectory": trajectory,
                    "predicted_answer":
                        predicted_answer,
                    "ground_truth":
                        ground_truth,
                    "correct": correct,
                    "difficulty":
                        question_data["difficulty"],
                    "difficulty_score":
                        question_data["difficulty_score"],
                    "model": MODEL,
                    "temperature": TEMPERATURE,
                    "max_tokens": MAX_TOKENS,
                    "elapsed_seconds":
                        round(elapsed, 3),
                }

                if response.usage:

                    record["prompt_tokens"] = (
                        response.usage.prompt_tokens
                    )

                    record["completion_tokens"] = (
                        response.usage.completion_tokens
                    )

                    record["total_tokens"] = (
                        response.usage.total_tokens
                    )

                with OUTPUT_FILE.open(
                    "a",
                    encoding="utf-8",
                ) as f:

                    f.write(
                        json.dumps(
                            record,
                            ensure_ascii=False,
                        )
                        + "\n"
                    )

                completed += 1

                print(
                    f"    Answer: {predicted_answer}"
                )

                print(
                    f"    Correct: {correct}"
                )

            except Exception as e:

                print(
                    f"    ERROR: {e}"
                )

                error_record = {
                    "question_id": question_id,
                    "trajectory_id": trajectory_id,
                    "question": question,
                    "trajectory": None,
                    "predicted_answer": None,
                    "ground_truth": ground_truth,
                    "correct": False,
                    "difficulty":
                        question_data["difficulty"],
                    "difficulty_score":
                        question_data["difficulty_score"],
                    "model": MODEL,
                    "temperature": TEMPERATURE,
                    "error": str(e),
                }

                with OUTPUT_FILE.open(
                    "a",
                    encoding="utf-8",
                ) as f:

                    f.write(
                        json.dumps(
                            error_record,
                            ensure_ascii=False,
                        )
                        + "\n"
                    )

                completed += 1

    print()
    print("=" * 60)
    print("GENERATION COMPLETED")
    print(f"Records: {completed}/{total}")
    print("=" * 60)


if __name__ == "__main__":
    main()