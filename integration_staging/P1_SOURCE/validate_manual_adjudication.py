#!/usr/bin/env python3
"""Validate reports/error_analysis/manual_adjudication.csv (README.txt Task 4, step 4.6)."""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HEADER = ["problem_id", "capability", "trajectory_ids_reviewed", "gold_capabilities_before",
          "trigger_type", "trace_evidence", "adjudication", "decision", "rationale", "review_status"]
REQUIRED = ["problem_id", "capability", "trajectory_ids_reviewed", "adjudication", "decision",
            "rationale", "review_status"]
ADJUDICATIONS = {"FALSE_LEXICAL_TRIGGER", "TRUE_CAPABILITY_OMITTED_FROM_GOLD", "DEFINITION_AMBIGUITY"}
DECISIONS = {"KEEP_GOLD", "PROPOSE_GOLD_UPDATE", "PROPOSE_RULE_CHANGE", "NEEDS_DISCUSSION"}
STATUSES = {"reviewed", "needs_discussion", "pending"}
TRIGGERS = {"lexical_keyword", "numeric_operator", "semantic_reasoning", "mixed"}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--adjudication", type=Path, default=ROOT / "reports" / "error_analysis" / "manual_adjudication.csv")
    p.add_argument("--cases", type=Path, default=ROOT / "reports" / "error_analysis" / "adjudication_review_cases.csv")
    p.add_argument("--trajectories", type=Path, default=ROOT / "trajectory" / "pool" / "batch_100_teacher_verified.jsonl")
    args = p.parse_args()

    with args.adjudication.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames
        rows = list(reader)
    with args.cases.open(encoding="utf-8-sig", newline="") as f:
        cases = {(r["problem_id"], r["capability"]) for r in csv.DictReader(f)}
    known_tids = {json.loads(l)["trajectory_id"] for l in args.trajectories.open(encoding="utf-8") if l.strip()}

    errors = []
    if header != HEADER:
        errors.append(f"header mismatch: {header}")
    pairs = Counter((r["problem_id"], r["capability"]) for r in rows)
    errors += [f"duplicate pair {k}" for k, v in pairs.items() if v > 1]
    errors += [f"missing case {k}" for k in sorted(cases - set(pairs))]
    errors += [f"unexpected case {k}" for k in sorted(set(pairs) - cases)]
    for i, r in enumerate(rows, 2):
        tag = f"line {i} {r['problem_id']}/{r['capability']}"
        errors += [f"{tag}: empty {k}" for k in REQUIRED if not r[k].strip()]
        if r["adjudication"] not in ADJUDICATIONS: errors.append(f"{tag}: invalid adjudication {r['adjudication']}")
        if r["decision"] not in DECISIONS: errors.append(f"{tag}: invalid decision {r['decision']}")
        if r["review_status"] not in STATUSES: errors.append(f"{tag}: invalid review_status {r['review_status']}")
        if r["trigger_type"] not in TRIGGERS: errors.append(f"{tag}: invalid trigger_type {r['trigger_type']}")
        if (r["decision"] == "NEEDS_DISCUSSION") != (r["review_status"] == "needs_discussion"):
            errors.append(f"{tag}: NEEDS_DISCUSSION decision and needs_discussion status must go together")
        for tid in filter(None, r["trajectory_ids_reviewed"].split(";")):
            if tid not in known_tids or not tid.startswith(r["problem_id"]):
                errors.append(f"{tag}: unknown trajectory {tid}")

    status = Counter(r["review_status"] for r in rows)
    print(f"Rows: {len(rows)} (expected {len(cases)})")
    print("Status:", dict(status))
    print("Adjudication:", dict(Counter(r["adjudication"] for r in rows)))
    print("Decision:", dict(Counter(r["decision"] for r in rows)))
    if status["pending"]:
        errors.append(f"{status['pending']} rows still pending")
    if errors:
        print("FAILED")
        for e in errors:
            print(" -", e)
        raise SystemExit(1)
    print("PASS")


if __name__ == "__main__":
    main()
