import json
import re
import time
from pathlib import Path

from openai import OpenAI


# ============================================================
# Configuration
# ============================================================

BASE_URL = "http://localhost:1234/v1"
MODEL = "qwen2.5-3b-instruct"

OUTPUT_FILE = Path("outputs/teacher_smoke_test.jsonl")


# ============================================================
# Test cases
# ============================================================

TESTS = [
    {
        "test_id": "T01",
        "category": "simple_addition",
        "prompt": """
John has 12 apples.
He buys 7 more apples.

How many apples does John have now?

Solve the problem step by step.
Show the calculation.
Provide the final answer clearly.
""",
        "ground_truth": "19",
    },
    {
        "test_id": "T02",
        "category": "multi_step_arithmetic",
        "prompt": """
A shop has 25 books.
It receives 18 more books.
Then it sells 12 books.

How many books are left?

Solve the problem step by step.
Show the calculation.
Provide the final answer clearly.
""",
        "ground_truth": "31",
    },
    {
        "test_id": "T03",
        "category": "multiplication_subtraction",
        "prompt": """
There are 6 boxes.
Each box contains 8 pencils.
A teacher gives away 13 pencils.

How many pencils remain?

Solve the problem step by step.
Show the calculation.
Provide the final answer clearly.
""",
        "ground_truth": "35",
    },
    {
        "test_id": "T04",
        "category": "money",
        "prompt": """
Tom has $20.
He buys 3 notebooks for $4 each.
How much money does Tom have left?

Solve the problem step by step.
Show the calculation.
Provide the final answer clearly.
""",
        "ground_truth": "8",
    },
    {
        "test_id": "T05",
        "category": "vietnamese_reasoning",
        "prompt": """
Lan có 15 quyển vở.
Lan mua thêm 8 quyển vở.
Sau đó Lan cho bạn 6 quyển.

Hỏi Lan còn lại bao nhiêu quyển vở?

Hãy giải bài toán từng bước.
Hiển thị phép tính.
Cuối cùng đưa ra đáp án rõ ràng.
""",
        "ground_truth": "17",
    },
]


# ============================================================
# Answer extraction
# ============================================================

def extract_answer(text):
    """
    Try to extract the final numerical answer from the model output.

    Priority:
    1. Explicit 'final answer' patterns
    2. Last standalone number
    """

    # Examples:
    # Final Answer: 19
    # Final answer is 19
    # Đáp án: 17
    patterns = [
        r"final\s+answer\s*(?:is|:)?\s*\$?(-?\d+(?:\.\d+)?)",
        r"answer\s*(?:is|:)?\s*\$?(-?\d+(?:\.\d+)?)",
        r"đáp\s*án\s*(?:là|:)?\s*\$?(-?\d+(?:\.\d+)?)",
        r"kết\s*quả\s*(?:là|:)?\s*\$?(-?\d+(?:\.\d+)?)",
    ]

    text_lower = text.lower()

    for pattern in patterns:
        matches = re.findall(pattern, text_lower)

        if matches:
            return matches[-1]

    # Fallback: take the last number in the response.
    numbers = re.findall(r"-?\d+(?:\.\d+)?", text)

    if numbers:
        return numbers[-1]

    return None


# ============================================================
# Main
# ============================================================

def main():

    print("=" * 60)
    print("TEACHER SMOKE TEST")
    print("=" * 60)

    print(f"\nServer: {BASE_URL}")
    print(f"Model:  {MODEL}")
    print(f"Tests:  {len(TESTS)}")
    print(f"Output: {OUTPUT_FILE}")

    # --------------------------------------------------------
    # Create client
    # --------------------------------------------------------

    client = OpenAI(
        base_url=BASE_URL,
        api_key="lm-studio",
    )

    # --------------------------------------------------------
    # Check server
    # --------------------------------------------------------

    print("\nChecking LM Studio server...")

    try:
        models = client.models.list()
        available_models = [m.id for m in models.data]

        print("Server: OK")
        print("Available models:")

        for model_id in available_models:
            print(f"  - {model_id}")

    except Exception as e:
        print("\nERROR: Cannot connect to LM Studio.")
        print(f"Details: {e}")
        print("\nMake sure:")
        print("1. LM Studio is running.")
        print("2. Qwen2.5-3B-Instruct is loaded.")
        print("3. Local Server is started.")
        print("4. Server is listening on http://localhost:1234")
        return

    # --------------------------------------------------------
    # Prepare output directory
    # --------------------------------------------------------

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Start fresh for this smoke test.
    if OUTPUT_FILE.exists():
        OUTPUT_FILE.unlink()

    # --------------------------------------------------------
    # Run tests
    # --------------------------------------------------------

    results = []

    for i, test in enumerate(TESTS, start=1):

        print("\n" + "=" * 60)
        print(f"{test['test_id']} — {test['category']}")
        print("=" * 60)

        print("Ground truth:", test["ground_truth"])
        print("Generating...")

        start_time = time.perf_counter()

        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": test["prompt"],
                    }
                ],
                temperature=0.0,
                max_tokens=512,
            )

            elapsed = time.perf_counter() - start_time

            output = response.choices[0].message.content or ""

            predicted_answer = extract_answer(output)

            correct = (
                predicted_answer is not None
                and predicted_answer == test["ground_truth"]
            )

            result = {
                "test_id": test["test_id"],
                "category": test["category"],
                "model": MODEL,
                "prompt": test["prompt"].strip(),
                "output": output,
                "ground_truth": test["ground_truth"],
                "predicted_answer": predicted_answer,
                "correct": correct,
                "elapsed_seconds": round(elapsed, 3),
            }

            # Add token information if available.
            if response.usage:
                result["prompt_tokens"] = response.usage.prompt_tokens
                result["completion_tokens"] = response.usage.completion_tokens
                result["total_tokens"] = response.usage.total_tokens

            results.append(result)

            # Save immediately.
            with OUTPUT_FILE.open(
                "a",
                encoding="utf-8",
            ) as f:

                f.write(
                    json.dumps(
                        result,
                        ensure_ascii=False,
                    )
                    + "\n"
                )

            print("\nTeacher output:")
            print(output)

            print("\nPredicted answer:", predicted_answer)
            print("Ground truth:    ", test["ground_truth"])
            print("Correct:         ", correct)
            print("Time:            ", f"{elapsed:.3f}s")

        except Exception as e:

            print("\nERROR during generation:")
            print(e)

            result = {
                "test_id": test["test_id"],
                "category": test["category"],
                "model": MODEL,
                "prompt": test["prompt"].strip(),
                "output": None,
                "ground_truth": test["ground_truth"],
                "predicted_answer": None,
                "correct": False,
                "error": str(e),
            }

            results.append(result)

            with OUTPUT_FILE.open(
                "a",
                encoding="utf-8",
            ) as f:

                f.write(
                    json.dumps(
                        result,
                        ensure_ascii=False,
                    )
                    + "\n"
                )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    valid_results = [
        r for r in results
        if "error" not in r
    ]

    correct_count = sum(
        r["correct"]
        for r in valid_results
    )

    total_count = len(valid_results)

    accuracy = (
        correct_count / total_count
        if total_count > 0
        else 0.0
    )

    print("\n" + "=" * 60)
    print("TEACHER SMOKE TEST SUMMARY")
    print("=" * 60)

    print(f"Tests completed: {total_count}/{len(TESTS)}")
    print(f"Correct:         {correct_count}")
    print(f"Accuracy:        {accuracy:.2%}")
    print(f"Output file:     {OUTPUT_FILE}")

    print("\nPer-test result:")

    for result in results:

        status = (
            "CORRECT"
            if result["correct"]
            else "WRONG"
        )

        print(
            f"{result['test_id']}: "
            f"{status} "
            f"(predicted={result['predicted_answer']}, "
            f"truth={result['ground_truth']})"
        )

    print("\nSmoke test completed.")


if __name__ == "__main__":
    main()