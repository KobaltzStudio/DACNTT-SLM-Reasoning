#!/usr/bin/env python3
"""Unit tests for the approved rules config/capability_rules_v2.json (Task 4).

Reuses the part A + part B cases from
reports/error_analysis/rule_change_proposal/test_rules_v2_proposed.py.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reports" / "error_analysis" / "rule_change_proposal"))
import test_rules_v2_proposed as proposal
from extract_capabilities_rule_based import compile_rules, extract_capabilities


def main():
    rules = json.loads((ROOT / "config" / "capability_rules_v2.json").read_text(encoding="utf-8"))
    compiled = compile_rules(rules)
    cases = [(t, proposal.PART_B_OVERRIDES.get(t, e)) for t, e in proposal.v1.CASES]
    cases += proposal.PART_A_CASES + proposal.PART_B_CASES
    failures = []
    for text, expected in cases:
        predicted = set(extract_capabilities(text, compiled)[0])
        if predicted != expected:
            failures.append((text, expected, predicted))
    for text in proposal.NEGATIVE_RATIO:
        if "ratio" in extract_capabilities(text, compiled)[0]:
            failures.append((text, "ratio must be absent"))
    for text in proposal.POSITIVE_RATIO:
        if "ratio" not in extract_capabilities(text, compiled)[0]:
            failures.append((text, "ratio must be present"))
    if failures:
        print("FAILED")
        for item in failures:
            print(item)
        raise SystemExit(1)
    total = len(cases) + len(proposal.NEGATIVE_RATIO) + len(proposal.POSITIVE_RATIO)
    print(f"PASS: {total} unit cases (config/capability_rules_v2.json)")


if __name__ == "__main__":
    main()
