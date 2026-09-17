import requests


LM_STUDIO_BASE_URL = "http://localhost:1234/v1"
CHAT_ENDPOINT = f"{LM_STUDIO_BASE_URL}/chat/completions"

TEACHER_MODEL = "qwen2.5-3b-instruct"
STUDENT_MODEL = "qwen2.5-1.5b-instruct"


def chat(
    model,
    prompt,
    temperature=0.0,
    max_tokens=512,
    timeout=180,
):
    """
    Send a chat completion request to LM Studio.
    """

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    response = requests.post(
        CHAT_ENDPOINT,
        json=payload,
        timeout=timeout,
    )

    response.raise_for_status()

    data = response.json()

    return data["choices"][0]["message"]["content"]


def extract_final_answer(text):
    """
    Try to extract the final numerical answer from model output.

    Supports:
    #### 42
    \\boxed{42}
    Final Answer: 42
    Answer: 42
    """

    import re

    # GSM8K style: #### 42
    matches = re.findall(
        r"####\s*(-?\d+(?:\.\d+)?)",
        text,
    )

    if matches:
        return matches[-1]

    # LaTeX boxed answer
    matches = re.findall(
        r"\\boxed\{(-?\d+(?:\.\d+)?)\}",
        text,
    )

    if matches:
        return matches[-1]

    # Final Answer / Answer
    matches = re.findall(
        r"(?:Final Answer|Answer)\s*[:=]\s*\$?\s*(-?\d+(?:\.\d+)?)",
        text,
        flags=re.IGNORECASE,
    )

    if matches:
        return matches[-1]

    # Fallback:
    # take the last number appearing in the response
    numbers = re.findall(
        r"-?\d+(?:\.\d+)?",
        text,
    )

    if numbers:
        return numbers[-1]

    return None


def normalize_answer(answer):
    """
    Normalize numerical answers for comparison.
    """

    if answer is None:
        return None

    answer = str(answer).strip()

    # Remove common currency symbol
    answer = answer.replace("$", "")
    answer = answer.replace(",", "")

    try:
        value = float(answer)

        if value.is_integer():
            return str(int(value))

        return str(value)

    except ValueError:
        return answer.lower()


def answers_equal(predicted, ground_truth):
    return (
        normalize_answer(predicted)
        == normalize_answer(ground_truth)
    )