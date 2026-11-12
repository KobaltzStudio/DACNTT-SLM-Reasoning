import csv
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path.cwd()
MANUAL = ROOT / "experiments/week2September/manual"

RULES_PATH = MANUAL / "config/capability_rules_v3.1.json"
EXTRACTOR_PATH = MANUAL / "scripts/extract_capabilities_rule_based.py"
NEGATIVE_FILES = [
    MANUAL / "data/regression/capability_regression_cases_v1.jsonl",
    MANUAL / "data/regression/capability_regression_cases_v3_1.jsonl",
]

RETENTION_IDS = {
    "gsm8k_train_00014",
    "gsm8k_train_00025",
    "gsm8k_train_00040",
    "gsm8k_train_00068",
    "gsm8k_train_02059",
    "gsm8k_train_02342",
    "gsm8k_train_02486",
    "gsm8k_train_02858",
    "gsm8k_train_03016",
    "gsm8k_train_03048",
    "gsm8k_train_03439",
    "gsm8k_train_05451",
    "gsm8k_train_07117",
}

def load_extractor():
    spec = importlib.util.spec_from_file_location(
        "extractor_v31_audit", EXTRACTOR_PATH
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def read_jsonl(path):
    records = []
    if not path.exists():
        print(f"MISSING JSONL: {path}")
        return records

    with path.open("r", encoding="utf-8-sig") as f:
        for line_number, line in enumerate(f, start=1):
            if line.strip():
                try:
                    records.append((line_number, json.loads(line)))
                except json.JSONDecodeError as exc:
                    print(f"JSON ERROR {path}:{line_number}: {exc}")
    return records

def main():
    print("\n========== 1. NEGATIVE JSONL CONTENT ==========")
    all_negative_records = []

    for path in NEGATIVE_FILES:
        print(f"\nFILE: {path}")
        records = read_jsonl(path)
        print("RECORD COUNT:", len(records))

        for line_number, record in records:
            print(f"\n--- line {line_number} ---")
            print("FIELDS:", list(record.keys()))
            print(json.dumps(record, ensure_ascii=False, indent=2))
            all_negative_records.append((path.name, record))

    print("\n========== 2. RULE REGEX EXACT VALUES ==========")
    rule_data = json.loads(RULES_PATH.read_text(encoding="utf-8-sig"))
    division_rule = rule_data["rules"]["division"]

    print("SCHEMA:", rule_data.get("schema_version"))
    print("DIVISION POSITIVE PATTERNS:")
    for index, pattern in enumerate(division_rule.get("patterns", [])):
        print(f"  [{index}] {pattern!r}")

    print("DIVISION NEGATIVE PATTERNS:")
    for index, pattern in enumerate(division_rule.get("negative_patterns", [])):
        print(f"  [{index}] {pattern!r}")

    print("\n========== 3. REGEX MATCH DIAGNOSTICS ==========")
    extractor = load_extractor()
    compiled = extractor.compile_rules(rule_data)

    questions = []

    for filename, record in all_negative_records:
        question = (
            record.get("question")
            or record.get("problem")
            or record.get("text")
        )
        if question:
            questions.append((f"{filename}:{record.get('id', record.get('test_id', '?'))}", question))

    # Retrieve the approved question for the known retention failure.
    approved_root = MANUAL / "reports/capability"
    for csv_path in approved_root.rglob("*.csv"):
        try:
            with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                if not reader.fieldnames or "problem_id" not in reader.fieldnames:
                    continue
                for row in reader:
                    if row.get("problem_id") == "gsm8k_train_02342":
                        question = row.get("question", "")
                        if question:
                            questions.append(
                                (f"gsm8k_train_02342 from {csv_path}", question)
                            )
        except (OSError, UnicodeDecodeError, csv.Error):
            continue

    seen = set()
    for label, question in questions:
        key = (label, question)
        if key in seen:
            continue
        seen.add(key)

        normalized = extractor.normalize_text(question)
        division = compiled["division"]

        negative_hits = [
            i for i, pattern in enumerate(division["negative"])
            if pattern.search(normalized)
        ]
        positive_hits = [
            i for i, pattern in enumerate(division["positive"])
            if pattern.search(normalized)
        ]

        predicted, evidence, fired = extractor.extract_capabilities(
            question, compiled
        )

        print(f"\n--- {label} ---")
        print("QUESTION:", question)
        print("NORMALIZED:", normalized)
        print("DIVISION NEGATIVE HITS:", negative_hits)
        print("DIVISION POSITIVE HITS:", positive_hits)
        print("PREDICTED:", predicted)
        print("DIVISION RULES FIRED:", fired.get("division", []))
        print("DIVISION EVIDENCE:", evidence.get("division", []))

    print("\n========== 4. SEARCH FOR RETENTION INPUT CSV ==========")
    candidates = []

    for csv_path in MANUAL.rglob("*.csv"):
        try:
            with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                if not reader.fieldnames or "problem_id" not in reader.fieldnames:
                    continue
                rows = list(reader)

            ids = {row.get("problem_id") for row in rows}
            overlap = ids & RETENTION_IDS

            if len(overlap) >= 8:
                candidates.append((csv_path, len(rows), len(overlap)))

        except (OSError, UnicodeDecodeError, csv.Error):
            continue

    if not candidates:
        print("No candidate CSV found with at least 8 matching retention IDs.")
    else:
        for path, row_count, overlap in sorted(
            candidates, key=lambda item: item[2], reverse=True
        ):
            print(
                f"CSV: {path}\n"
                f"  rows={row_count}, matching_retention_ids={overlap}"
            )

    print("\n========== 5. RETENTION TEST SCRIPT ==========")
    retention_script = MANUAL / "scripts/test_division_retention_13.py"
    if retention_script.exists():
        print(retention_script.read_text(encoding="utf-8-sig"))
    else:
        print("Retention test script not found:", retention_script)

if __name__ == "__main__":
    main()
