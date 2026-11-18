"""
Candidate unified answer extraction/verification (Task 5, open decisions #27 and #27b).

Status: PROPOSED, not frozen. See task5_decisions.md.

Rule:
  1. Split the model output into REASONING / ANSWER with the same regex as
     scripts/generate_teacher_trajectories_batch.py:split_response (prompt v1 format).
  2. Final number = LAST number in the ANSWER text (as generate_teacher_trajectories_batch.py),
     after removing ',', '$', '%'.
  3. Canonicalize with Decimal.normalize() (as regenerate_failed_trajectories_reviewed.py),
     so "36.00" == "36".
  4. Correct iff both final numbers exist and are equal.

Evidence: on trajectory/pool/batch_100_teacher_raw_recovered_v2.jsonl this rule reproduces the stored
verification_status exactly (480 valid / 20 invalid_answer). The two existing functions each disagree
on some records (generate: 1, regenerate: 5). Check with scripts/test_answer_utils.py.
"""

import re
from decimal import Decimal, InvalidOperation


NUMBER_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")

RESPONSE_RE = re.compile(
    r"REASONING\s*:\s*(.*?)\s*ANSWER\s*:\s*(.*?)\s*$",
    re.IGNORECASE | re.DOTALL,
)


def split_response(text):
    """Return (reasoning, answer, status); status is 'parsed' or 'invalid_format'."""
    text = (text or "").strip()
    m = RESPONSE_RE.search(text)
    if not m:
        return text, "", "invalid_format"
    reasoning, answer = m.group(1).strip(), m.group(2).strip()
    if not reasoning or not answer:
        return reasoning, answer, "invalid_format"
    return reasoning, answer, "parsed"


def final_number(value):
    """Canonical string of the last number in value, or None."""
    text = str(value or "").replace(",", "").replace("$", "").replace("%", "")
    numbers = NUMBER_RE.findall(text)
    if not numbers:
        return None
    try:
        return format(Decimal(numbers[-1]).normalize(), "f")
    except InvalidOperation:
        return None


def answers_match(answer, ground_truth):
    a, g = final_number(answer), final_number(ground_truth)
    return a is not None and a == g


def verify_answer(answer, ground_truth):
    """Same status labels as the existing pool."""
    if not answer:
        return "invalid_format"
    return "valid" if answers_match(answer, ground_truth) else "invalid_answer"


def evaluate_output(raw_output, ground_truth):
    """For Student evaluation: parse prompt-v1 output, then verify."""
    _, answer, status = split_response(raw_output)
    if status != "parsed":
        return "invalid_format"
    return verify_answer(answer, ground_truth)
