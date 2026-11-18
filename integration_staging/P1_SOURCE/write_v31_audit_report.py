import csv
import json
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path("experiments/week2September/manual")
AUDIT = ROOT / "reports/capability/p1_extractor_v3_1_2026-11-14"

METRICS_PATH = AUDIT / "approved170_evaluation/metrics_v3_1_approved170.json"
PREDICTIONS_PATH = AUDIT / "approved170_evaluation/predictions_v3_1_all170.csv"
CHANGES_PATH = AUDIT / "approved170_evaluation/prediction_changes_v3_vs_v3_1.csv"
FN_PATH = AUDIT / "approved170_evaluation/false_negatives_v3_1.csv"
FP_PATH = AUDIT / "approved170_evaluation/false_positives_v3_1.csv"

CANDIDATE_METRICS_PATH = (
    AUDIT / "candidate_analysis/multiplication_exception_candidate/candidate_metrics.json"
)
CANDIDATE_CHANGES_PATH = (
    AUDIT / "candidate_analysis/multiplication_exception_candidate/candidate_changes.csv"
)

NEGATIVE_PATH = AUDIT / "regression/division_v3_1_negative_results.csv"
RETENTION_PATH = AUDIT / "regression/division_retention_13_results.csv"

CONFIG_PATH = ROOT / "config/capability_rules_v3.1.json"
BACKUP_CONFIG_PATH = (
    ROOT / "config/backups/"
    "capability_rules_v3.1_before_inverse_percentage_exception_20261112_155233.json"
)

OUTPUT_PATH = AUDIT / "v3_1_experiment_audit.md"

EXPECTED_CAPABILITIES = [
    "addition",
    "subtraction",
    "multiplication",
    "division",
    "percentage",
    "fraction",
    "ratio",
]


def require_file(path):
    if not path.exists():
        raise FileNotFoundError(f"Required file not found: {path}")


def load_json(path):
    require_file(path)
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def load_csv(path):
    require_file(path)
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        columns = reader.fieldnames or []
    return rows, columns


def parse_json_cell(value):
    if value is None or value == "":
        return []
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return []


def fmt_rate(value):
    if value is None:
        return "N/A"
    return f"{value:.4f}"


def fmt_percent(value):
    if value is None:
        return "N/A"
    return f"{value * 100:.2f}%"


def recursive_strings(value):
    result = []
    if isinstance(value, str):
        result.append(value)
    elif isinstance(value, dict):
        for child in value.values():
            result.extend(recursive_strings(child))
    elif isinstance(value, list):
        for child in value:
            result.extend(recursive_strings(child))
    return result


def check(condition, message, errors):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {message}")
    if not condition:
        errors.append(message)


def markdown_table(headers, rows):
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        safe = [str(x).replace("|", "\\|").replace("\n", " ") for x in row]
        lines.append("| " + " | ".join(safe) + " |")
    return "\n".join(lines)


def main():
    errors = []

    print("=" * 76)
    print("V3.1 EXPERIMENT AUDIT")
    print("=" * 76)

    # ---------------------------------------------------------
    # 1. Load all required artifacts
    # ---------------------------------------------------------
    metrics = load_json(METRICS_PATH)
    candidate_metrics = load_json(CANDIDATE_METRICS_PATH)

    predictions, prediction_columns = load_csv(PREDICTIONS_PATH)
    changes, changes_columns = load_csv(CHANGES_PATH)
    false_negatives, fn_columns = load_csv(FN_PATH)
    false_positives, fp_columns = load_csv(FP_PATH)

    candidate_changes, candidate_change_columns = load_csv(
        CANDIDATE_CHANGES_PATH
    )
    negative, negative_columns = load_csv(NEGATIVE_PATH)
    retention, retention_columns = load_csv(RETENTION_PATH)

    config = load_json(CONFIG_PATH)
    backup_config = load_json(BACKUP_CONFIG_PATH)

    # ---------------------------------------------------------
    # 2. Extract official metrics
    # ---------------------------------------------------------
    v3 = metrics["v3_metrics"]
    v31 = metrics["v3_1_metrics"]

    v3_micro = v3["micro"]
    v31_micro = v31["micro"]

    sample_count = metrics["sample_count"]
    prediction_change_count = len(changes)
    candidate_change_count = len(candidate_changes)

    # ---------------------------------------------------------
    # 3. Validate core metrics and artifact consistency
    # ---------------------------------------------------------
    check(sample_count == 170, "Approved evaluation has 170 samples", errors)
    check(len(predictions) == 170, "Prediction CSV contains 170 rows", errors)

    check(
        v31["sample_count"] == 170,
        "v3.1 metrics sample count is 170",
        errors,
    )
    check(
        v31["exact_match_count"] == 8,
        "v3.1 exact match count is 8",
        errors,
    )
    check(
        v31_micro["tp"] == 194
        and v31_micro["fp"] == 17
        and v31_micro["fn"] == 309,
        "v3.1 micro TP/FP/FN are 194/17/309",
        errors,
    )
    check(
        len(false_negatives) == 162,
        "False-negative CSV contains 162 rows",
        errors,
    )
    check(
        len(false_positives) == 17,
        "False-positive CSV contains 17 rows",
        errors,
    )
    check(
        prediction_change_count == 15,
        "Official v3-to-v3.1 prediction changes count is 15",
        errors,
    )
    check(
        candidate_change_count == 1,
        "Candidate exception changed exactly one row",
        errors,
    )

    # Candidate metrics must agree with official final metrics.
    candidate_final = candidate_metrics["candidate"]
    candidate_baseline = candidate_metrics["baseline"]

    check(
        candidate_final["micro"]["tp"] == v31_micro["tp"]
        and candidate_final["micro"]["fp"] == v31_micro["fp"]
        and candidate_final["micro"]["fn"] == v31_micro["fn"],
        "Candidate final micro metrics match official v3.1 metrics",
        errors,
    )

    check(
        candidate_metrics.get("changed_rows") == 1,
        "Candidate analysis reports one changed row",
        errors,
    )

    candidate_ids = candidate_metrics.get("changed_problem_ids", [])
    check(
        candidate_ids == ["gsm8k_train_00011"],
        "Candidate changed problem is gsm8k_train_00011",
        errors,
    )

    if candidate_changes:
        candidate_row_id = candidate_changes[0].get("problem_id")
    else:
        candidate_row_id = None

    check(
        candidate_row_id == "gsm8k_train_00011",
        "Candidate changes CSV identifies gsm8k_train_00011",
        errors,
    )

    # ---------------------------------------------------------
    # 4. Validate negative regression
    # ---------------------------------------------------------
    negative_passes = [
        str(row.get("test_pass", "")).strip().lower() == "true"
        for row in negative
    ]

    check(
        len(negative) == 2,
        "Negative regression contains exactly two cases",
        errors,
    )
    check(
        len(negative_passes) == 2 and all(negative_passes),
        "Both negative regression cases pass",
        errors,
    )

    negative_division_absent = all(
        str(row.get("division_detected", "")).strip().lower() == "false"
        and len(parse_json_cell(row.get("forbidden_found", "[]"))) == 0
        for row in negative
    )

    check(
        negative_division_absent,
        "Division is absent in both negative regression cases",
        errors,
    )

    # ---------------------------------------------------------
    # 5. Validate division retention
    # ---------------------------------------------------------
    retention_correct = [
        str(row.get("division_correct", "")).strip().lower() == "true"
        for row in retention
    ]

    trace_verified = [
        row for row in retention
        if str(row.get("solution_trace_available", "")).strip().upper() == "YES"
    ]

    provisional = [
        row for row in retention
        if str(row.get("annotation_status", "")).strip().upper()
        == "PROVISIONAL_NO_TRACE"
    ]

    check(
        len(retention) == 13,
        "Division retention dataset contains 13 records",
        errors,
    )
    check(
        len(retention_correct) == 13 and all(retention_correct),
        "All 13 retention records have matching division predictions",
        errors,
    )
    check(
        len(trace_verified) == 0,
        "No retention record is trace-verified",
        errors,
    )
    check(
        len(provisional) == 13,
        "All 13 retention records are provisional",
        errors,
    )

    # ---------------------------------------------------------
    # 6. Validate inverse-percentage exception presence
    # ---------------------------------------------------------
    candidate_pattern = candidate_metrics.get("candidate_negative_pattern", "")

    official_strings = recursive_strings(config)
    backup_strings = recursive_strings(backup_config)

    pattern_in_official = (
        bool(candidate_pattern)
        and any(candidate_pattern == value for value in official_strings)
    )
    pattern_in_backup = (
        bool(candidate_pattern)
        and any(candidate_pattern == value for value in backup_strings)
    )

    check(
        pattern_in_official,
        "Candidate inverse-percentage pattern exists in official config",
        errors,
    )
    check(
        not pattern_in_backup,
        "Candidate inverse-percentage pattern is absent from pre-exception backup",
        errors,
    )

    # ---------------------------------------------------------
    # 7. Per-capability metrics
    # ---------------------------------------------------------
    per_capability_rows = []
    for capability in EXPECTED_CAPABILITIES:
        item = v31["per_capability"][capability]
        per_capability_rows.append([
            capability,
            item["tp"],
            item["fp"],
            item["fn"],
            item["tn"],
            fmt_rate(item.get("precision")),
            fmt_rate(item.get("recall")),
            fmt_rate(item.get("f1")),
        ])

    # ---------------------------------------------------------
    # 8. Build report
    # ---------------------------------------------------------
    generated_at = datetime.now().astimezone().isoformat(timespec="seconds")

    report = []

    report.append("# v3.1 Experiment Audit")
    report.append("")
    report.append(f"- Generated at: `{generated_at}`")
    report.append("- Experiment: `Dynamic Learnability-aware CoT Knowledge Distillation`")
    report.append("- Component: Rule-based capability extraction")
    report.append("- Rules version: `v3.1`")
    report.append("- Evaluation set: Approved 170")
    report.append("- Audit status: " + (
        "**PASS WITH DOCUMENTED LIMITATIONS**" if not errors
        else "**FAILED VALIDATION — REVIEW REQUIRED**"
    ))
    report.append("")
    report.append("> Scope note: Approved 170 is an approved/review set, not an independent test set. "
                  "The extractor uses question text and does not inspect Teacher solution traces. "
                  "Gold annotation uncertainty must be considered separately.")
    report.append("")

    report.append("## 1. Objective and scope")
    report.append("")
    report.append(
        "This audit consolidates the v3.1 rule-based capability extractor results, "
        "the approved-170 evaluation, the inverse-percentage multiplication exception, "
        "and the available regression checks. It verifies artifact consistency and "
        "records unresolved limitations. It does not claim generalization to an "
        "independent test set."
    )
    report.append("")

    report.append("## 2. Configuration and change")
    report.append("")
    report.append(f"- Official config: `{CONFIG_PATH.as_posix()}`")
    report.append(f"- Pre-exception backup: `{BACKUP_CONFIG_PATH.as_posix()}`")
    report.append(
        "- The candidate inverse-percentage negative pattern is present in the "
        "official v3.1 config and absent from the pre-exception backup."
    )
    report.append(
        "- The candidate analysis reports one changed problem: "
        "`gsm8k_train_00011`."
    )
    report.append(
        "- For this question, multiplication was removed while percentage was retained. "
        "The gold annotation is `division` and `percentage`; division remains a false negative. "
        "The exception therefore removes the multiplication false positive but does not "
        "solve the missing division prediction."
    )
    report.append("")

    report.append("## 3. Approved 170 evaluation")
    report.append("")
    report.append("### 3.1 Overall metrics")
    report.append("")
    report.append(markdown_table(
        ["Metric", "v3", "v3.1"],
        [
            ["Samples", v3["sample_count"], v31["sample_count"]],
            [
                "Exact match",
                f'{v3["exact_match_count"]}/{v3["sample_count"]} ({fmt_percent(v3["exact_match_rate"])})',
                f'{v31["exact_match_count"]}/{v31["sample_count"]} ({fmt_percent(v31["exact_match_rate"])})',
            ],
            ["Micro TP", v3_micro["tp"], v31_micro["tp"]],
            ["Micro FP", v3_micro["fp"], v31_micro["fp"]],
            ["Micro FN", v3_micro["fn"], v31_micro["fn"]],
            ["Micro precision", fmt_rate(v3_micro["precision"]), fmt_rate(v31_micro["precision"])],
            ["Micro recall", fmt_rate(v3_micro["recall"]), fmt_rate(v31_micro["recall"])],
            ["Micro F1", fmt_rate(v3_micro["f1"]), fmt_rate(v31_micro["f1"])],
        ]
    ))
    report.append("")

    report.append("### 3.2 v3.1 per-capability metrics")
    report.append("")
    report.append(markdown_table(
        ["Capability", "TP", "FP", "FN", "TN", "Precision", "Recall", "F1"],
        per_capability_rows,
    ))
    report.append("")

    report.append("### 3.3 Prediction changes and error counts")
    report.append("")
    report.append(f"- Prediction changes between v3 and final v3.1: **{len(changes)}**.")
    report.append(f"- False negatives: **{len(false_negatives)}**.")
    report.append(f"- False positives: **{len(false_positives)}**.")
    report.append(
        "- The official prediction-changes CSV contains 15 records. "
        "The earlier count of 16 belongs to the pre-exception state; after the "
        "exception changed `gsm8k_train_00011`, that problem no longer contributes "
        "a v3-to-final-v3.1 prediction difference."
    )
    report.append("")

    report.append("## 4. Inverse-percentage exception candidate")
    report.append("")
    report.append(
        f"- Candidate changed rows: **{candidate_metrics.get('changed_rows', 'N/A')}**."
    )
    report.append(
        f"- Changed problem IDs: `{', '.join(candidate_ids) if candidate_ids else 'N/A'}`."
    )
    report.append("")
    report.append(markdown_table(
        ["Metric", "Candidate baseline", "Candidate final / official v3.1"],
        [
            ["TP", candidate_baseline["micro"]["tp"], candidate_final["micro"]["tp"]],
            ["FP", candidate_baseline["micro"]["fp"], candidate_final["micro"]["fp"]],
            ["FN", candidate_baseline["micro"]["fn"], candidate_final["micro"]["fn"]],
            ["Precision", fmt_rate(candidate_baseline["micro"]["precision"]), fmt_rate(candidate_final["micro"]["precision"])],
            ["Recall", fmt_rate(candidate_baseline["micro"]["recall"]), fmt_rate(candidate_final["micro"]["recall"])],
            ["F1", fmt_rate(candidate_baseline["micro"]["f1"]), fmt_rate(candidate_final["micro"]["f1"])],
        ]
    ))
    report.append("")
    report.append(
        "The exception reduces FP from 18 to 17 while TP and FN remain unchanged. "
        "It improves precision and F1 slightly; it does not improve recall. "
        "This is a narrow correction supported by one changed sample, not evidence "
        "of broad multiplication capability improvement."
    )
    report.append("")

    report.append("## 5. Regression results")
    report.append("")
    report.append("### 5.1 Strict negative division regression")
    report.append("")
    report.append(f"- Cases: {len(negative)}.")
    report.append(f"- Passed: {sum(negative_passes)}/{len(negative_passes)}.")
    report.append(
        "- Both cases retain their expected multiplication, percentage, and subtraction "
        "predictions while suppressing division."
    )
    report.append("")
    report.append(markdown_table(
        ["Test", "Source problem", "Predicted capabilities", "Division detected", "PASS"],
        [
            [
                row.get("test_id", ""),
                row.get("source_problem_id", ""),
                ", ".join(parse_json_cell(row.get("predicted_capabilities", "[]"))),
                row.get("division_detected", ""),
                row.get("test_pass", ""),
            ]
            for row in negative
        ],
    ))
    report.append("")

    report.append("### 5.2 Division retention regression")
    report.append("")
    report.append(f"- Total records: {len(retention)}.")
    report.append(f"- Division prediction matched gold: {sum(retention_correct)}/{len(retention_correct)}.")
    report.append(f"- Trace-verified records: {len(trace_verified)}.")
    report.append(f"- Provisional no-trace records: {len(provisional)}.")
    report.append(
        "**Interpretation:** the 13/13 result is provisional. All records have "
        "`solution_trace_available = NO`; therefore this result verifies agreement "
        "with the current provisional annotations only. It must not be described "
        "as trace-verified retention."
    )
    report.append("")

    report.append("## 6. Remaining errors and limitations")
    report.append("")
    report.append(f"- The approved-170 evaluation still contains {len(false_negatives)} false-negative records.")
    report.append(f"- It still contains {len(false_positives)} false-positive records.")
    report.append(
        "- Recall remains limited. The v3.1 micro recall is "
        f"{fmt_rate(v31_micro['recall'])}, so the extractor misses a substantial "
        "number of gold capability labels."
    )
    report.append(
        "- The 170-sample set is an approved/review set, not an independent test set."
    )
    report.append(
        "- The extractor is question-text based and does not use Teacher solution traces."
    )
    report.append(
        "- Some gold labels and retention examples remain provisional and require "
        "trace-based or otherwise documented human verification."
    )
    report.append(
        "- The inverse-percentage exception addresses one observed multiplication "
        "false positive. It does not resolve the division false negative on "
        "`gsm8k_train_00011`."
    )
    report.append("")

    report.append("## 7. Artifact inventory")
    report.append("")
    inventory = [
        ["Official rules", CONFIG_PATH.as_posix(), "KEEP"],
        ["Pre-exception rules backup", BACKUP_CONFIG_PATH.as_posix(), "KEEP"],
        ["Approved 170 metrics", METRICS_PATH.as_posix(), "KEEP"],
        ["Approved 170 predictions", PREDICTIONS_PATH.as_posix(), "KEEP"],
        ["Prediction changes", CHANGES_PATH.as_posix(), "KEEP"],
        ["False negatives", FN_PATH.as_posix(), "KEEP"],
        ["False positives", FP_PATH.as_posix(), "KEEP"],
        ["Candidate metrics", CANDIDATE_METRICS_PATH.as_posix(), "KEEP"],
        ["Candidate changed rows", CANDIDATE_CHANGES_PATH.as_posix(), "KEEP"],
        ["Negative regression", NEGATIVE_PATH.as_posix(), "KEEP"],
        ["Division retention regression", RETENTION_PATH.as_posix(), "KEEP"],
    ]
    report.append(markdown_table(["Artifact", "Path", "Recommendation"], inventory))
    report.append("")

    report.append("## 8. Validation summary")
    report.append("")
    report.append(
        "The audit script validates the approved-170 counts, final metrics, "
        "prediction-change count, candidate changed row, regression outcomes, "
        "retention annotation status, and the presence of the promoted exception "
        "in the official config."
    )
    report.append("")
    if errors:
        report.append("### Validation failures")
        report.append("")
        for error in errors:
            report.append(f"- FAIL: {error}")
        report.append("")
        report.append(
            "**Audit is not cleared.** Resolve the validation failures and rerun "
            "the audit script."
        )
    else:
        report.append(
            "**All mandatory artifact consistency checks passed.** "
            "The documented annotation and evaluation limitations remain open."
        )
    report.append("")

    report.append("## 9. Recommended next actions")
    report.append("")
    report.append("1. Preserve the current v3.1 config and all evaluation artifacts.")
    report.append("2. Do not promote additional rules based only on the Approved 170 set.")
    report.append("3. Prioritize review of high-impact false negatives and false positives.")
    report.append("4. Obtain solution traces or documented human adjudication for provisional labels.")
    report.append("5. Re-evaluate future rule changes on a separately defined validation/test protocol.")
    report.append("")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text("\n".join(report), encoding="utf-8")

    print("\n" + "=" * 76)
    print("VALIDATION SUMMARY")
    print("=" * 76)
    print(f"Prediction changes: {len(changes)}")
    print(f"Candidate changed rows: {len(candidate_changes)}")
    print(f"Negative regression: {sum(negative_passes)}/{len(negative_passes)}")
    print(f"Retention provisional matches: {sum(retention_correct)}/{len(retention_correct)}")
    print(f"Trace-verified retention records: {len(trace_verified)}")
    print(f"False negatives: {len(false_negatives)}")
    print(f"False positives: {len(false_positives)}")

    print(f"\nReport created: {OUTPUT_PATH}")

    if errors:
        print("\nAUDIT VALIDATION FAILED:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("\nAUDIT VALIDATION: PASS WITH DOCUMENTED LIMITATIONS")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"\nFATAL ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(2)
