import json
import re
import time
from pathlib import Path

from datasets import load_dataset
from openai import OpenAI


# ============================================================
# Configuration
# ============================================================

BASE_URL = "http://localhost:1234/v1"
MODEL = "qwen2.5-3b-instruct"

DATASET_NAME = "openai/gsm8k"
DATASET_CONFIG = "main"

NUM_SAMPLES = 100

OUTPUT_FILE = Path(
    "outputs/teacher_gsm8k_smoke_test.jsonl"
)

MAX_TOKENS = 512
TEMPERATURE = 0.0

REQUEST_TIMEOUT = 120

# Fixed seed makes the 20-sample selection reproducible.
RANDOM_SEED = 42


# ============================================================
# Prompt
# ============================================================

SYSTEM_PROMPT = """
You are a mathematical reasoning teacher.

Solve the given GSM8K problem carefully and step by step.

Requirements:
1. Show the reasoning clearly.
2. Perform every required calculation.
3. Do not skip intermediate steps.
4. At the end, provide the final numerical answer.
5. Use this exact format for the final answer:

#### <number>

Do not put additional text after the final answer.
""".strip()


# ============================================================
# Answer extraction
# ============================================================

def normalize_number(value):
    """
    Normalize simple numerical answers.

    Examples:
        "18"       -> "18"
        "18.0"     -> "18"
        "$18"      -> "18"
        "1,234"    -> "1234"
    """

    if value is None:
        return None

    value = value.strip()
    value = value.replace(",", "")
    value = value.replace("$", "")
    value = value.strip()

    try:
        number = float(value)

        if number.is_integer():
            return str(int(number))

        return str(number)

    except ValueError:
        return value


def extract_gsm8k_answer(answer_text):
    """
    Extract final answer from a GSM8K answer.

    Priority:
    1. #### <answer>
    2. Last numerical value in the text
    """

    if not answer_text:
        return None

    # GSM8K standard format:
    #
    # #### 18
    #
    matches = re.findall(
        r"####\s*(-?\d+(?:\.\d+)?)",
        answer_text,
    )

    if matches:
        return normalize_number(matches[-1])

    # Fallback if Teacher does not follow #### format.
    numbers = re.findall(
        r"-?\d+(?:\.\d+)?",
        answer_text,
    )

    if numbers:
        return normalize_number(numbers[-1])

    return None


# ============================================================
# Ground-truth extraction
# ============================================================

def extract_ground_truth(answer_text):
    """
    Extract the final answer from the original GSM8K answer.
    """

    return extract_gsm8k_answer(answer_text)


# ============================================================
# Dataset
# ============================================================

def load_gsm8k():

    print("\nLoading GSM8K...")

    dataset = load_dataset(
        DATASET_NAME,
        DATASET_CONFIG,
    )

    print("GSM8K loaded.")

    print(
        f"Train samples: {len(dataset['train'])}"
    )

    print(
        f"Test samples:  {len(dataset['test'])}"
    )

    return dataset


# ============================================================
# Resume support
# ============================================================

def load_existing_results():

    if not OUTPUT_FILE.exists():
        return {}

    existing = {}

    with OUTPUT_FILE.open(
        "r",
        encoding="utf-8",
    ) as f:

        for line in f:

            line = line.strip()

            if not line:
                continue

            try:
                record = json.loads(line)

                existing[record["id"]] = record

            except Exception:
                continue

    return existing


# ============================================================
# Main
# ============================================================

def main():

    print("=" * 70)
    print("TEACHER GSM8K DATA GENERATION")
    print("=" * 70)

    print(f"\nServer:       {BASE_URL}")
    print(f"Model:        {MODEL}")
    print(f"Samples:      {NUM_SAMPLES}")
    print(f"Temperature:  {TEMPERATURE}")
    print(f"Max tokens:   {MAX_TOKENS}")
    print(f"Output:       {OUTPUT_FILE}")

    # --------------------------------------------------------
    # Create output directory
    # --------------------------------------------------------

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # --------------------------------------------------------
    # Connect to LM Studio
    # --------------------------------------------------------

    print("\nChecking LM Studio server...")

    client = OpenAI(
        base_url=BASE_URL,
        api_key="lm-studio",
        timeout=REQUEST_TIMEOUT,
    )

    try:

        models = client.models.list()

        available_models = [
            model.id
            for model in models.data
        ]

        print("Server: OK")

        print("Available models:")

        for model_id in available_models:
            print(f"  - {model_id}")

        if MODEL not in available_models:

            print(
                f"\nWARNING: Requested model "
                f"'{MODEL}' was not found exactly."
            )

            print(
                "LM Studio may still accept the request "
                "if the model alias is different."
            )

    except Exception as e:

        print("\nERROR: Cannot connect to LM Studio.")
        print(f"Details: {e}")

        print(
            "\nMake sure LM Studio Local Server "
            "is running on port 1234."
        )

        return

    # --------------------------------------------------------
    # Load dataset
    # --------------------------------------------------------

    dataset = load_gsm8k()

    train = dataset["train"]

    # --------------------------------------------------------
    # Select reproducible samples
    # --------------------------------------------------------

    print(
        f"\nSelecting {NUM_SAMPLES} samples "
        f"from GSM8K train..."
    )

    if NUM_SAMPLES > len(train):

        raise ValueError(
            "NUM_SAMPLES is larger than "
            "the available training set."
        )

    selected = train.shuffle(
        seed=RANDOM_SEED
    ).select(
        range(NUM_SAMPLES)
    )

    print(
        f"Selected {len(selected)} samples."
    )

    # --------------------------------------------------------
    # Load existing records
    # --------------------------------------------------------

    existing = load_existing_results()

    if existing:

        print(
            f"\nResume mode: "
            f"{len(existing)} existing records found."
        )

    # --------------------------------------------------------
    # Generate Teacher data
    # --------------------------------------------------------

    generated_count = 0
    skipped_count = 0
    correct_count = 0

    for index, sample in enumerate(
        selected
    ):

        record_id = (
            f"gsm8k_train_{index:05d}"
        )

        # ----------------------------------------------------
        # Resume
        # ----------------------------------------------------

        if record_id in existing:

            record = existing[record_id]

            print(
                f"\n[{index + 1}/{NUM_SAMPLES}] "
                f"{record_id} already exists — SKIP"
            )

            if record.get("correct") is True:
                correct_count += 1

            skipped_count += 1

            continue

        question = sample["question"]
        original_answer = sample["answer"]

        ground_truth = extract_ground_truth(
            original_answer
        )

        print("\n" + "=" * 70)
        print(
            f"[{index + 1}/{NUM_SAMPLES}] "
            f"{record_id}"
        )
        print("=" * 70)

        print("\nQuestion:")
        print(question)

        print(
            f"\nGround truth: {ground_truth}"
        )

        user_prompt = (
            "Solve this GSM8K problem.\n\n"
            + question
        )

        # ----------------------------------------------------
        # Generate
        # ----------------------------------------------------

        success = False

        for attempt in range(1, 4):

            try:

                print(
                    f"\nGenerating "
                    f"(attempt {attempt}/3)..."
                )

                start_time = time.perf_counter()

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
                                "content": user_prompt,
                            },
                        ],
                        temperature=TEMPERATURE,
                        max_tokens=MAX_TOKENS,
                    )
                )

                elapsed = (
                    time.perf_counter()
                    - start_time
                )

                output = (
                    response
                    .choices[0]
                    .message
                    .content
                    or ""
                )

                teacher_answer = (
                    extract_gsm8k_answer(
                        output
                    )
                )

                correct = (
                    teacher_answer is not None
                    and ground_truth is not None
                    and teacher_answer
                    == ground_truth
                )

                record = {
                    "id": record_id,
                    "dataset": "gsm8k",
                    "split": "train",
                    "index": index,
                    "question": question,
                    "teacher_reasoning": output,
                    "teacher_answer": teacher_answer,
                    "ground_truth": ground_truth,
                    "correct": correct,
                    "model": MODEL,
                    "temperature": TEMPERATURE,
                    "max_tokens": MAX_TOKENS,
                    "elapsed_seconds": round(
                        elapsed,
                        3,
                    ),
                }

                # ------------------------------------------------
                # Token usage
                # ------------------------------------------------

                if response.usage:

                    record["prompt_tokens"] = (
                        response
                        .usage
                        .prompt_tokens
                    )

                    record["completion_tokens"] = (
                        response
                        .usage
                        .completion_tokens
                    )

                    record["total_tokens"] = (
                        response
                        .usage
                        .total_tokens
                    )

                # ------------------------------------------------
                # Save immediately
                # ------------------------------------------------

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

                print(
                    "\nTeacher answer:",
                    teacher_answer,
                )

                print(
                    "Ground truth: ",
                    ground_truth,
                )

                print(
                    "Correct:      ",
                    correct,
                )

                print(
                    "Time:         ",
                    f"{elapsed:.3f}s",
                )

                generated_count += 1

                if correct:
                    correct_count += 1

                success = True

                break

            except Exception as e:

                print(
                    f"\nERROR on attempt "
                    f"{attempt}:"
                )

                print(e)

                if attempt < 3:

                    print(
                        "Retrying in 3 seconds..."
                    )

                    time.sleep(3)

        # ----------------------------------------------------
        # Failed after 3 attempts
        # ----------------------------------------------------

        if not success:

            error_record = {
                "id": record_id,
                "dataset": "gsm8k",
                "split": "train",
                "index": index,
                "question": question,
                "teacher_reasoning": None,
                "teacher_answer": None,
                "ground_truth": ground_truth,
                "correct": False,
                "model": MODEL,
                "error": "Generation failed after 3 attempts.",
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

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("TEACHER GSM8K GENERATION SUMMARY")
    print("=" * 70)

    print(
        f"Requested samples:  {NUM_SAMPLES}"
    )

    print(
        f"Newly generated:    {generated_count}"
    )

    print(
        f"Skipped/resumed:    {skipped_count}"
    )

    print(
        f"Correct:             {correct_count}"
    )

    print(
        f"Output file:        {OUTPUT_FILE}"
    )

    print("\nGeneration completed.")


if __name__ == "__main__":
    main()