import json
import os
import time

from common_lmstudio import (
    STUDENT_MODEL,
    chat,
    extract_final_answer,
    answers_equal,
)


INPUT_FILE = "outputs/teacher_gsm8k_smoke_test.jsonl"
OUTPUT_FILE = "outputs/teacher_student_comparison.jsonl"

STUDENT_PROMPT_TEMPLATE = """Solve the following math problem.

Give a clear step-by-step solution.

At the end, provide the final numerical answer clearly.

Problem:
{question}
"""


def main():

    print("=" * 60)
    print("TEACHER vs STUDENT BASELINE")
    print("=" * 60)

    if not os.path.exists(INPUT_FILE):
        raise FileNotFoundError(
            f"Input file not found: {INPUT_FILE}"
        )

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8",
    ) as f:
        samples = [
            json.loads(line)
            for line in f
            if line.strip()
        ]

    print(f"Samples: {len(samples)}")
    print(f"Student: {STUDENT_MODEL}")
    print(f"Output: {OUTPUT_FILE}")
    print()

    results = []

    teacher_correct_count = 0
    student_correct_count = 0

    for i, sample in enumerate(samples, start=1):

        sample_id = sample["id"]
        question = sample["question"]

        teacher_answer = sample.get(
            "teacher_answer"
        )

        ground_truth = sample["ground_truth"]

        print("=" * 60)
        print(f"{i}/{len(samples)} - {sample_id}")
        print("=" * 60)

        prompt = STUDENT_PROMPT_TEMPLATE.format(
            question=question
        )

        print("Student generating...")

        start = time.time()

        try:

            student_output = chat(
                model=STUDENT_MODEL,
                prompt=prompt,
                temperature=0.0,
                max_tokens=512,
            )

            elapsed = time.time() - start

            student_answer = extract_final_answer(
                student_output
            )

            teacher_correct = answers_equal(
                teacher_answer,
                ground_truth,
            )

            student_correct = answers_equal(
                student_answer,
                ground_truth,
            )

            if teacher_correct:
                teacher_correct_count += 1

            if student_correct:
                student_correct_count += 1

            result = {
                "id": sample_id,
                "question": question,
                "teacher_answer": teacher_answer,
                "student_answer": student_answer,
                "ground_truth": ground_truth,
                "teacher_correct": teacher_correct,
                "student_correct": student_correct,
                "student_output": student_output,
                "student_model": STUDENT_MODEL,
                "elapsed_seconds": round(elapsed, 3),
            }

            print()
            print("Teacher:", teacher_answer)
            print("Student:", student_answer)
            print("Truth:  ", ground_truth)
            print("Teacher correct:", teacher_correct)
            print("Student correct:", student_correct)
            print(f"Time: {elapsed:.2f}s")

        except Exception as e:

            result = {
                "id": sample_id,
                "question": question,
                "teacher_answer": teacher_answer,
                "student_answer": None,
                "ground_truth": ground_truth,
                "teacher_correct": answers_equal(
                    teacher_answer,
                    ground_truth,
                ),
                "student_correct": False,
                "student_output": None,
                "student_model": STUDENT_MODEL,
                "error": str(e),
            }

            print("ERROR:", e)

        results.append(result)

    os.makedirs(
        os.path.dirname(OUTPUT_FILE),
        exist_ok=True,
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8",
    ) as f:

        for result in results:
            f.write(
                json.dumps(
                    result,
                    ensure_ascii=False,
                )
                + "\n"
            )

    total = len(results)

    teacher_accuracy = (
        teacher_correct_count / total
        if total
        else 0
    )

    student_accuracy = (
        student_correct_count / total
        if total
        else 0
    )

    print()
    print("=" * 60)
    print("BASELINE SUMMARY")
    print("=" * 60)

    print(
        f"Teacher: {teacher_correct_count}/{total} "
        f"= {teacher_accuracy * 100:.2f}%"
    )

    print(
        f"Student: {student_correct_count}/{total} "
        f"= {student_accuracy * 100:.2f}%"
    )

    print(
        f"Accuracy gap: "
        f"{(teacher_accuracy - student_accuracy) * 100:.2f} percentage points"
    )

    print()
    print("Output:", OUTPUT_FILE)


if __name__ == "__main__":
    main()