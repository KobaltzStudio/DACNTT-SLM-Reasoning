import csv
import json
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
D3_DIR = BASE / "reports" / "capability" / "d3_regression"

INPUT = D3_DIR / "error_analysis.csv"
SUMMARY_CSV = D3_DIR / "error_analysis_by_capability.csv"
PRIORITY_CSV = D3_DIR / "priority_error_review.csv"
SUMMARY_MD = D3_DIR / "error_analysis_summary.md"

CAPABILITIES = [
    "addition",
    "subtraction",
    "multiplication",
    "division",
    "percentage",
    "fraction",
    "ratio",
]

PRIORITY_CAPABILITIES = {
    "division",
    "addition",
    "multiplication",
}


def parse_json_list(value, field, problem_id):
    try:
        result = json.loads(value or "[]")
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON in {field} for {problem_id}"
        ) from exc

    if not isinstance(result, list):
        raise ValueError(
            f"{field} is not a JSON list for {problem_id}"
        )
    return result


def main():
    if not INPUT.exists():
        raise FileNotFoundError(INPUT)

    with INPUT.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    fn_counts = Counter()
    fp_counts = Counter()
    priority_rows = []

    for row in rows:
        problem_id = row["problem_id"]

        fn = parse_json_list(
            row.get("false_negatives", ""),
            "false_negatives",
            problem_id,
        )
        fp = parse_json_list(
            row.get("false_positives", ""),
            "false_positives",
            problem_id,
        )

        fn_counts.update(fn)
        fp_counts.update(fp)

        priority_fn = sorted(set(fn) & PRIORITY_CAPABILITIES)

        if priority_fn:
            priority_rows.append({
                "problem_id": problem_id,
                "priority_false_negatives": json.dumps(
                    priority_fn, ensure_ascii=False
                ),
                "all_false_negatives": json.dumps(
                    fn, ensure_ascii=False
                ),
                "false_positives": json.dumps(
                    fp, ensure_ascii=False
                ),
                "gold_capabilities": row.get("gold_capabilities", ""),
                "predicted_capabilities": row.get(
                    "predicted_capabilities", ""
                ),
                "question": row.get("question", ""),
                "evidence": row.get("evidence", ""),
                "rules_fired": row.get("rules_fired", ""),
            })

    summary_rows = []
    for capability in CAPABILITIES:
        summary_rows.append({
            "capability": capability,
            "FN": fn_counts[capability],
            "FP": fp_counts[capability],
        })

    with SUMMARY_CSV.open(
        "w", encoding="utf-8-sig", newline=""
    ) as f:
        writer = csv.DictWriter(
            f, fieldnames=["capability", "FN", "FP"]
        )
        writer.writeheader()
        writer.writerows(summary_rows)

    priority_fields = [
        "problem_id",
        "priority_false_negatives",
        "all_false_negatives",
        "false_positives",
        "gold_capabilities",
        "predicted_capabilities",
        "question",
        "evidence",
        "rules_fired",
    ]

    with PRIORITY_CSV.open(
        "w", encoding="utf-8-sig", newline=""
    ) as f:
        writer = csv.DictWriter(
            f, fieldnames=priority_fields
        )
        writer.writeheader()
        writer.writerows(priority_rows)

    lines = [
        "# D3 Error Analysis Summary",
        "",
        f"- Error records: {len(rows)}",
        f"- Priority records with FN in addition/multiplication/division: {len(priority_rows)}",
        "",
        "| Capability | FN | FP |",
        "|---|---:|---:|",
    ]

    for row in summary_rows:
        lines.append(
            f"| {row['capability']} | {row['FN']} | {row['FP']} |"
        )

    lines.extend([
        "",
        "## Interpretation guide",
        "",
        "- FN means a capability required by Gold was not predicted.",
        "- FP means a capability was predicted but is absent from Gold.",
        "- High FN may indicate missing lexical patterns, overly strict rules, "
        "or a mismatch between surface words and problem-level reasoning.",
        "- FP may indicate an overly broad trigger or an annotation disagreement.",
        "- Neither FN nor FP alone proves which side is wrong; inspect the question, "
        "Gold labels, evidence, and fired rules together.",
        "",
        "## Review priority",
        "",
        "Review division, addition, and multiplication FN cases first. "
        "Do not change rules until the Gold label and mathematical requirement "
        "have been checked against Guideline v3.",
        "",
    ])

    SUMMARY_MD.write_text("\n".join(lines), encoding="utf-8")

    print("D3 ERROR ANALYSIS SUMMARY")
    print(f"Input error records: {len(rows)}")
    print(f"Priority records: {len(priority_rows)}")
    print(f"Summary CSV: {SUMMARY_CSV}")
    print(f"Priority CSV: {PRIORITY_CSV}")
    print(f"Summary Markdown: {SUMMARY_MD}")
    print("[PASS]")


if __name__ == "__main__":
    main()
