#!/usr/bin/env python3
"""Unit tests for the PROPOSED rule change (not approved, not applied).

Usage:
  python3 test_rules_v2_proposed.py partA
  python3 test_rules_v2_proposed.py partAB

Reuses the v1 cases from scripts/test_capability_extractor.py. Regression cases come from
reports/error_analysis/manual_adjudication.csv.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from extract_capabilities_rule_based import compile_rules, extract_capabilities
import test_capability_extractor as v1

# Part B only, guideline_v2 Rule 3: a fraction used as a multiplier is fraction, not division.
PART_B_OVERRIDES = {
    r"\[ \frac{2}{3} \cdot 30 = 20 \]": {"fraction", "multiplication"},
}

PART_A_CASES = [
    # FALSE_LEXICAL_TRIGGER: 'per' is a rate unit (gsm8k_train_00021, 00084, 00099).
    ("Tickets cost 10.00 per ticket, so 2 x 10.00 = 20.00", {"multiplication"}),
    ("Anna gets 14 pieces of candy per house.", set()),
    # Real division written with units must still be detected after 'per' is removed.
    ("average = 210 points / 5 games = 42 points/game", {"division"}),
    ("504 ounces / 84 ounces/bottle = 6 bottles", {"division"}),
    ("short students = (2 times 400) / 5 = 800 / 5 = 160", {"multiplication", "division"}),
    ("we divide 429 by 3 to get 143", {"division"}),
]
PART_B_CASES = [
    # FALSE_LEXICAL_TRIGGER: fraction/percentage multiplier (00016, 00030, 00035, 00049).
    ("number of short students = 2 / 5 times 400 = 160", {"fraction", "multiplication"}),
    ("albino deer: 92 times 1 / 4 = 23", {"fraction", "multiplication"}),
    ("10% of 40 = 10 / 100 times 40 = 4", {"percentage", "multiplication"}),
    ("number of times = (1/2) * 4 = 2", {"fraction", "multiplication"}),
    ("monthly payment = 480,000 / 240 = 2,000", {"division"}),
    ("(480,000) / (240 months) = 2,000", {"division"}),
]

NEGATIVE_RATIO = v1.NEGATIVE_RATIO + [
    # gsm8k_train_00087: share wording, not ratio reasoning (guideline_v2 Rule 6).
    "we calculate the proportion of oysters with pearls in a single dive: 16 / 4 = 4",
]
POSITIVE_RATIO = [
    "The ratio of boys to girls is 2:5.",
    "x is proportional to y.",
    "Set up a proportion: 4 / 5 = 60 / x.",
]


def run(part):
    rules = json.loads((HERE / f"capability_rules_v2_proposed_{part}.json").read_text(encoding="utf-8"))
    compiled = compile_rules(rules)
    overrides = PART_B_OVERRIDES if part == "partAB" else {}
    cases = [(t, overrides.get(t, e)) for t, e in v1.CASES] + PART_A_CASES
    if part == "partAB":
        cases += PART_B_CASES
    failures = []
    for text, expected in cases:
        predicted, _, _ = extract_capabilities(text, compiled)
        if set(predicted) != expected:
            failures.append((text, expected, set(predicted)))
    for text in NEGATIVE_RATIO:
        if "ratio" in extract_capabilities(text, compiled)[0]:
            failures.append((text, "ratio must be absent"))
    for text in POSITIVE_RATIO:
        if "ratio" not in extract_capabilities(text, compiled)[0]:
            failures.append((text, "ratio must be present"))
    if failures:
        print("FAILED")
        for item in failures:
            print(item)
        raise SystemExit(1)
    print(f"PASS: {len(cases) + len(NEGATIVE_RATIO) + len(POSITIVE_RATIO)} unit cases ({part})")


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("partA", "partAB"):
        raise SystemExit("Usage: test_rules_v2_proposed.py partA|partAB")
    run(sys.argv[1])
