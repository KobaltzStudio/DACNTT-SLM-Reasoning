import csv
import json
from pathlib import Path

ROOT = Path("experiments/week2September/manual")
AUDIT = ROOT / "reports/capability/p1_extractor_v3_1_2026-11-14"

FILES = {
    "official_metrics": AUDIT / "approved170_evaluation/metrics_v3_1_approved170.json",
    "candidate_metrics": AUDIT / "candidate_analysis/multiplication_exception_candidate/candidate_metrics.json",
    "official_prediction_changes": AUDIT / "approved170_evaluation/prediction_changes_v3_vs_v3_1.csv",
    "candidate_changes": AUDIT / "candidate_analysis/multiplication_exception_candidate/candidate_changes.csv",
    "negative_regression": AUDIT / "regression/division_v3_1_negative_results.csv",
    "retention_regression": AUDIT / "regression/division_retention_13_results.csv",
    "approved_predictions": AUDIT / "approved170_evaluation/predictions_v3_1_all170.csv",
    "false_negatives": AUDIT / "approved170_evaluation/false_negatives_v3_1.csv",
    "false_positives": AUDIT / "approved170_evaluation/false_positives_v3_1.csv",
}

def inspect_json(name, path):
    print(f"\n{'=' * 90}\nJSON: {name}\nPATH: {path}")
    if not path.exists():
        print("MISSING")
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        print(json.dumps(data, ensure_ascii=False, indent=2))
    except Exception as exc:
        print(f"READ ERROR: {exc}")

def inspect_csv(name, path, limit=5):
    print(f"\n{'=' * 90}\nCSV: {name}\nPATH: {path}")
    if not path.exists():
        print("MISSING")
        return
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        print(f"ROWS: {len(rows)}")
        print(f"COLUMNS: {reader.fieldnames}")
        for i, row in enumerate(rows[:limit], start=1):
            print(f"ROW {i}: {json.dumps(row, ensure_ascii=False)}")
        if len(rows) > limit:
            print(f"... {len(rows) - limit} additional rows")
    except Exception as exc:
        print(f"READ ERROR: {exc}")

def main():
    print("V3.1 AUDIT INPUT INSPECTION")
    print(f"Project root: {Path.cwd()}")

    for name in ("official_metrics", "candidate_metrics"):
        inspect_json(name, FILES[name])

    for name, path in FILES.items():
        if name not in ("official_metrics", "candidate_metrics"):
            inspect_csv(name, path)

    config = ROOT / "config/capability_rules_v3.1.json"
    backup = ROOT / "config/backups/capability_rules_v3.1_before_inverse_percentage_exception_20261112_155233.json"

    for label, path in (("official_config", config), ("pre_exception_backup", backup)):
        print(f"\n{'=' * 90}\nCONFIG: {label}\nPATH: {path}")
        if not path.exists():
            print("MISSING")
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
            print("TOP-LEVEL KEYS:", list(data.keys()) if isinstance(data, dict) else type(data).__name__)
            print(json.dumps(data, ensure_ascii=False, indent=2)[:12000])
        except Exception as exc:
            print(f"READ ERROR: {exc}")

if __name__ == "__main__":
    main()
