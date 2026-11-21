#!/usr/bin/env python3
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from extract_capabilities_rule_based import compile_rules, extract_capabilities

RULES = json.loads((SCRIPT_DIR.parent / "config" / "capability_rules_v1.json").read_text(encoding="utf-8"))
COMPILED = compile_rules(RULES)

CASES = [
    ("6 x 8 = 48. Then 48 / 4 = 12.", {"multiplication", "division"}),
    ("25% of 80 is 20.", {"percentage"}),
    ("One-third of 48 is 16.", {"fraction"}),
    ("The ratio of boys to girls is 2:5.", {"ratio"}),
    ("The total is 15 + 20 = 35.", {"addition"}),
    ("100 - 35 = 65 remain.", {"subtraction"}),
    ("There are twice as many apples.", {"multiplication"}),
    ("The ratio is not needed; we simply divide 100 by 5.", {"division"}),
    ("The fraction 1/2 is mentioned, so 20 / 2 = 10.", {"fraction", "division"}),
    ("48 / 3 = 16.", {"division"}),
    ("A 50 percent discount is applied.", {"percentage"}),
    (r"\[ 24 \times 2 = 48 \]", {"multiplication"}),
    (r"\( \frac{48}{3} = 16 \)", {"division"}),
    (r"\[ \frac{\$300}{\$25} = 12 \]", {"division"}),
    (r"\[ \frac{2}{3} \cdot 30 = 20 \]", {"fraction", "division", "multiplication"}),
    (r"\[ \frac{24 \times 2}{3} = 16 \]", {"multiplication", "division"}),
    (r"\[ \dfrac{\frac{60}{4}}{5} = 3 \]", {"division"}),
    (r"\[ 100 \div 4 = 25 \]", {"division"}),
    (r"\[ 20\% \text{ of } 80 = 16 \]", {"percentage"}),
    (r"\[ \boxed{1{,}200} \]", set()),
    (r"\[ \left( 10 + 5 \right) \times 2 = 30 \]", {"addition", "multiplication"}),
    (r"\[ 26 \text{ points/game} \times 15 \text{ games} = 390 \]", {"multiplication"}),
]
NEGATIVE_RATIO = [
    "Kyle found twice as many, so 48.",
    "24 / 3 = 8.",
    "There are 3 times as many books.",
    r"Split it by 3: \[ \frac{12}{3} = 4 \]",
    "Step 3: 12 apples remain.",
    r"Divide the balance by \(5\) : \[ 44 / 5 = 8 \]",
]

def run():
    failures = []
    for text, expected in CASES:
        predicted, _, _ = extract_capabilities(text, COMPILED)
        if set(predicted) != expected:
            failures.append((text, expected, set(predicted)))
    for text in NEGATIVE_RATIO:
        predicted, _, _ = extract_capabilities(text, COMPILED)
        if "ratio" in predicted:
            failures.append((text, "ratio must be absent", predicted))
    if failures:
        print("FAILED")
        for item in failures:
            print(item)
        raise SystemExit(1)
    print(f"PASS: {len(CASES) + len(NEGATIVE_RATIO)} unit cases")
if __name__ == "__main__":
    run()
