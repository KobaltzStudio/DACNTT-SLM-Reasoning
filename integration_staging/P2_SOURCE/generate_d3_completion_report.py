import csv
import json
from pathlib import Path
from datetime import date

BASE = Path(__file__).resolve().parents[1]
REPORT_DIR = BASE / "reports" / "capability"
D3_DIR = REPORT_DIR / "d3_regression"

D2_JSON = REPORT_DIR / "d2_regression" / "extractor_baseline.json"
D3_JSON = D3_DIR / "extractor_vnext_metrics.json"
COMPARISON_CSV = D3_DIR / "d2_d3_comparison.csv"
ERROR_CSV = D3_DIR / "error_analysis.csv"

OUTPUT = REPORT_DIR / "D3_completion_report.md"


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def fmt(value):
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def main():
    for path in [D2_JSON, D3_JSON, COMPARISON_CSV, ERROR_CSV]:
        if not path.exists():
            raise FileNotFoundError(
                f"Required D3 output is missing: {path}"
            )

    d2 = json.loads(D2_JSON.read_text(encoding="utf-8"))
    d3 = json.loads(D3_JSON.read_text(encoding="utf-8"))
    comparison = read_csv(COMPARISON_CSV)
    errors = read_csv(ERROR_CSV)

    if d2["gold_records"] != 185 or d3["gold_records"] != 185:
        raise ValueError("Expected 185 Gold records in both D2 and D3")

    if d3["prediction_records"] != 185:
        raise ValueError("Expected 185 D3 predictions")

    if d3["unique_problem_ids"] != 185:
        raise ValueError("Expected 185 unique D3 problem IDs")

    lines = [
        "# D3 Completion Report",
        "",
        f"Report generated: {date.today().isoformat()}",
        "",
        "## 1. Objective",
        "",
        "D3 evaluates the rule-based capability extractor against Gold vNext. "
        "The purpose is to measure extractor behavior under the updated "
        "problem-level annotations produced through the D3 adjudication process.",
        "",
        "## 2. Gold vNext",
        "",
        f"- Total Gold records: {d3['gold_records']}",
        f"- Unique problem IDs: {d3['unique_problem_ids']}",
        f"- Guideline version: {d3.get('guideline_version', 'Not recorded')}",
        f"- Gold status: {d3.get('gold_status', 'Not recorded')}",
        "- Gold vNext contains AI-adjudicated cases pending human confirmation.",
        "",
        "## 3. Experimental Configuration",
        "",
        "- Extractor: `scripts/extract_capabilities_rule_based.py`",
        "- Rules: `config/capability_rules_v2.json`",
        "- Evaluation unit: problem-level",
        "- D3 Gold: Gold vNext",
        "- D2 reference Gold: Gold v2",
        "- Extractor implementation and rules are unchanged between D2 and D3.",
        "",
        "## 4. D3 Evaluation Results",
        "",
        "| Metric | D3 result |",
        "|---|---:|",
        f"| Gold records | {d3['gold_records']} |",
        f"| Prediction records | {d3['prediction_records']} |",
        f"| Exact matches | {d3['exact_matches']} |",
        f"| Exact match rate | {fmt(d3['exact_match_rate'])} |",
        f"| Micro Precision | {fmt(d3['micro']['precision'])} |",
        f"| Micro Recall | {fmt(d3['micro']['recall'])} |",
        f"| Micro F1 | {fmt(d3['micro']['f1'])} |",
        f"| Macro F1 | {fmt(d3['macro_f1'])} |",
        "",
        "### 4.1 Per-capability metrics",
        "",
        "| Capability | Support | TP | FP | FN | Precision | Recall | F1 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for capability, metric in d3["capabilities"].items():
        lines.append(
            f"| {capability} | {metric['support']} | "
            f"{metric['TP']} | {metric['FP']} | {metric['FN']} | "
            f"{fmt(metric['precision'])} | {fmt(metric['recall'])} | "
            f"{fmt(metric['f1'])} |"
        )

    lines.extend([
        "",
        "## 5. D2 and D3 Comparison",
        "",
        "| Level | Metric | Capability | D2 | D3 | Delta (D3-D2) |",
        "|---|---|---|---:|---:|---:|",
    ])

    for row in comparison:
        lines.append(
            f"| {row['level']} | {row['metric']} | "
            f"{row['capability']} | {row['d2']} | {row['d3']} | "
            f"{row['delta_d3_minus_d2']} |"
        )

    lines.extend([
        "",
        "### Interpretation",
        "",
        "D2 uses Gold v2, whereas D3 uses Gold vNext. The extractor "
        "implementation and rule configuration are held constant. Therefore, "
        "differences in measured metrics indicate sensitivity to the updated "
        "Gold annotations; they must not be interpreted as an improvement "
        "or degradation of the extractor itself.",
        "",
        "## 6. Error Analysis",
        "",
        f"- Number of problem records with at least one capability error: {len(errors)}",
        f"- Error analysis file: `d3_regression/error_analysis.csv`",
        "",
        "The error analysis records false positives, false negatives, "
        "the original question, matched evidence, and fired rules for each "
        "problem with an incorrect prediction.",
        "",
        "## 7. Output Artifacts",
        "",
        "| Artifact | Path |",
        "|---|---|",
        "| D3 evaluation input | `d3_regression/gold_evaluation_input.jsonl` |",
        "| D3 predictions | `d3_regression/extractor_predictions.jsonl` |",
        "| D3 evidence | `d3_regression/extractor_evidence.jsonl` |",
        "| D3 metrics JSON | `d3_regression/extractor_vnext_metrics.json` |",
        "| D3 capability metrics | `d3_regression/capability_metrics.csv` |",
        "| D2-D3 comparison CSV | `d3_regression/d2_d3_comparison.csv` |",
        "| D2-D3 comparison JSON | `d3_regression/d2_d3_comparison.json` |",
        "| D3 error analysis | `d3_regression/error_analysis.csv` |",
        "",
        "## 8. Limitations",
        "",
        "1. Gold vNext includes AI-adjudicated labels that are pending human confirmation.",
        "2. The evaluation measures a rule-based extractor against problem-level labels; "
        "it does not establish that every matched lexical pattern represents "
        "a mathematically necessary capability.",
        "3. D2-D3 metric differences are affected by the change in Gold annotations.",
        "4. Error analysis identifies prediction mismatches but does not automatically "
        "establish whether the Gold label or extractor rule is responsible.",
        "",
        "## 9. Completion Status",
        "",
        "- [x] Gold vNext evaluation input generated.",
        "- [x] Extractor predictions and evidence generated.",
        "- [x] D3 metrics calculated.",
        "- [x] D2-D3 comparison generated.",
        "- [x] D3 error analysis generated.",
        "- [x] Completion report generated.",
        "",
        "Human confirmation of the AI-adjudicated cases remains a separate "
        "validation activity and is not claimed as completed by this report.",
        "",
    ])

    OUTPUT.write_text("\n".join(lines), encoding="utf-8")

    print("D3 COMPLETION REPORT")
    print(f"Output: {OUTPUT}")
    print(f"D3 records: {d3['gold_records']}")
    print(f"D3 error records: {len(errors)}")
    print("[PASS]")


if __name__ == "__main__":
    main()
