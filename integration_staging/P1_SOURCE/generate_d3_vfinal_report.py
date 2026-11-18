import csv
import json
from datetime import date
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]

REPORT_DIR = BASE / "reports" / "capability"
FINAL_DIR = REPORT_DIR / "d3_final_regression"

D2_JSON = REPORT_DIR / "d2_regression" / "extractor_baseline.json"
D3_JSON = FINAL_DIR / "extractor_vfinal_metrics.json"
COMPARISON_CSV = FINAL_DIR / "d2_vfinal_comparison.csv"
ERROR_CSV = FINAL_DIR / "error_analysis.csv"
ERROR_SUMMARY_CSV = FINAL_DIR / "error_analysis_by_capability.csv"
MANIFEST = BASE / "data" / "gold_vfinal" / "gold_vfinal_manifest.json"
VALIDATION = REPORT_DIR / "d3_audit" / "gold_vfinal_validation.json"

OUTPUT = FINAL_DIR / "D3_final_completion_report.md"


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
    required = [
        D2_JSON, D3_JSON, COMPARISON_CSV, ERROR_CSV,
        ERROR_SUMMARY_CSV, MANIFEST, VALIDATION,
    ]

    for path in required:
        if not path.exists():
            raise FileNotFoundError(
                f"Required report input missing: {path}"
            )

    d2 = json.loads(D2_JSON.read_text(encoding="utf-8"))
    d3 = json.loads(D3_JSON.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    validation = json.loads(VALIDATION.read_text(encoding="utf-8"))

    comparison = read_csv(COMPARISON_CSV)
    errors = read_csv(ERROR_CSV)
    error_summary = read_csv(ERROR_SUMMARY_CSV)

    if validation.get("status") != "PASS":
        raise ValueError("Gold vFinal validation is not PASS")

    if d3["gold_version"] != "vFinal":
        raise ValueError("Metrics report is not Gold vFinal")

    if d3["gold_records"] != 185:
        raise ValueError("Expected 185 Gold vFinal records")

    if d3["prediction_records"] != 185:
        raise ValueError("Expected 185 predictions")

    if d3["unique_problem_ids"] != 185:
        raise ValueError("Expected 185 unique problem IDs")

    lines = [
        "# D3 Final Completion Report",
        "",
        f"Report generated: {date.today().isoformat()}",
        "",
        "## 1. Objective",
        "",
        "D3 evaluates the rule-based capability extractor against "
        "the project-team-confirmed Gold vFinal annotations. "
        "The evaluation unit is the individual problem.",
        "",
        "## 2. Gold vFinal",
        "",
        f"- Gold version: {manifest['gold_version']}",
        f"- Batch records: {manifest['batch_count']}",
        f"- Supplement records: {manifest['supplement_count']}",
        f"- Total records: {manifest['total_count']}",
        f"- Unique problem IDs: {manifest['unique_problem_ids']}",
        f"- Confirmed adjudications: {manifest['human_confirmed_adjudication_count']}",
        f"- Validation status: {validation['status']}",
        "- Guideline: v3",
        "",
        "The 22 AI-adjudicated decisions were explicitly confirmed "
        "by the project team. The labels in Gold vFinal remain "
        "identical to Gold vNext; the version change records the "
        "confirmation status and provenance.",
        "",
        "## 3. Experimental Configuration",
        "",
        "- Extractor: `scripts/extract_capabilities_rule_based.py`",
        "- Rules: `config/capability_rules_v2.json`",
        "- Evaluation unit: problem-level",
        "- Gold: Gold vFinal",
        "- Reference baseline: D2 Gold v2",
        "- Extractor and rule implementation are unchanged.",
        "",
        "## 4. D3 vFinal Evaluation Results",
        "",
        "| Metric | Result |",
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

    for cap, metric in d3["capabilities"].items():
        lines.append(
            f"| {cap} | {metric['support']} | "
            f"{metric['TP']} | {metric['FP']} | {metric['FN']} | "
            f"{fmt(metric['precision'])} | "
            f"{fmt(metric['recall'])} | {fmt(metric['f1'])} |"
        )

    lines.extend([
        "",
        "## 5. D2 and D3 vFinal Comparison",
        "",
        "| Level | Metric | Capability | D2 | D3 vFinal | Delta |",
        "|---|---|---|---:|---:|---:|",
    ])

    for row in comparison:
        lines.append(
            f"| {row['level']} | {row['metric']} | "
            f"{row['capability']} | {row['d2']} | "
            f"{row['d3_vfinal']} | "
            f"{row['delta_vfinal_minus_d2']} |"
        )

    lines.extend([
        "",
        "### Interpretation",
        "",
        "D2 and D3 vFinal use different Gold annotation versions. "
        "The extractor implementation and rule configuration are "
        "held constant. Therefore, metric differences must be "
        "interpreted as sensitivity to annotation changes, not "
        "as evidence of extractor improvement.",
        "",
        "## 6. Error Analysis",
        "",
        f"- Problems with at least one mismatch: {len(errors)}",
        "",
        "| Capability | FN | FP |",
        "|---|---:|---:|",
    ])

    for row in error_summary:
        lines.append(
            f"| {row['capability']} | {row['FN']} | {row['FP']} |"
        )

    lines.extend([
        "",
        "The error analysis contains the original question, Gold "
        "labels, predicted labels, false negatives, false positives, "
        "evidence and fired rules. A mismatch alone does not establish "
        "whether the Gold annotation or extractor rule is incorrect.",
        "",
        "## 7. Limitations",
        "",
        "1. The evaluation covers 185 GSM8K problems and does not by "
        "itself establish generalization to other datasets.",
        "2. The 22 adjudication decisions were AI-proposed and then "
        "explicitly confirmed by the project team; this should not be "
        "described as independent inter-human annotation agreement.",
        "3. The rule-based extractor may miss semantically required "
        "capabilities when their wording is not covered by its patterns.",
        "4. D2-D3 metric differences are affected by the Gold annotation "
        "version and are not extractor improvements.",
        "5. Error classification requires reviewing both the mathematical "
        "requirements and the fired rules.",
        "",
        "## 8. Output Artifacts",
        "",
        "| Artifact | Path |",
        "|---|---|",
        "| Gold vFinal manifest | `data/gold_vfinal/gold_vfinal_manifest.json` |",
        "| Gold vFinal validation | `reports/capability/d3_audit/gold_vfinal_validation.json` |",
        "| Evaluation input | `d3_final_regression/gold_evaluation_input.jsonl` |",
        "| Predictions | `d3_final_regression/extractor_predictions.jsonl` |",
        "| Evidence | `d3_final_regression/extractor_evidence.jsonl` |",
        "| Metrics JSON | `d3_final_regression/extractor_vfinal_metrics.json` |",
        "| Capability metrics | `d3_final_regression/capability_metrics.csv` |",
        "| D2-vFinal comparison | `d3_final_regression/d2_vfinal_comparison.csv` |",
        "| Error analysis | `d3_final_regression/error_analysis.csv` |",
        "| Error summary | `d3_final_regression/error_analysis_by_capability.csv` |",
        "| Priority review | `d3_final_regression/priority_error_review_annotated.csv` |",
        "",
        "## 9. Completion Status",
        "",
        "- [x] Gold vFinal created and validated.",
        "- [x] 22 adjudication decisions confirmed by the project team.",
        "- [x] Evaluation input generated.",
        "- [x] Extractor predictions and evidence generated.",
        "- [x] D3 vFinal metrics calculated.",
        "- [x] D2-D3 vFinal comparison generated.",
        "- [x] Error analysis generated.",
        "- [ ] Priority error review completed.",
        "- [ ] Decision on extractor rule v3 documented.",
        "",
    ])

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")

    print("D3 VFINAL COMPLETION REPORT")
    print(f"Gold records: {d3['gold_records']}")
    print(f"Error records: {len(errors)}")
    print(f"Output: {OUTPUT}")
    print("[PASS]")


if __name__ == "__main__":
    main()
