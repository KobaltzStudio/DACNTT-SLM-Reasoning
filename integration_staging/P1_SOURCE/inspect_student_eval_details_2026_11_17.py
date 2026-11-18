from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[4]
MANUAL = ROOT / "experiments" / "week2September" / "manual"
OUT = MANUAL / "reports" / "capability" / "student_eval_2026-11-17"
INSPECTION = OUT / "student_eval_source_inspection.json"

def read_json(path):
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)

def print_json(label, value):
    print(f"\n{'=' * 24} {label} {'=' * 24}")
    print(json.dumps(value, ensure_ascii=False, indent=2))

def print_source_context(path, patterns, before=5, after=12):
    print(f"\n{'=' * 24} SOURCE: {path.name} {'=' * 24}")
    if not path.exists():
        print("MISSING:", path)
        return

    lines = path.read_text(encoding="utf-8-sig").splitlines()
    hits = set()

    for i, line in enumerate(lines):
        if any(re.search(p, line, re.I) for p in patterns):
            start = max(0, i - before)
            end = min(len(lines), i + after + 1)
            hits.update(range(start, end))

    if not hits:
        print("No matching lines.")
        return

    previous = -2
    for i in sorted(hits):
        if i > previous + 1:
            print("\n---")
        print(f"{i + 1:04d}: {lines[i]}")
        previous = i

def main():
    if not INSPECTION.exists():
        raise FileNotFoundError(INSPECTION)

    report = read_json(INSPECTION)

    print("PYTHON_JSON_PARSE: PASS")
    print("INSPECTION_FILE:", INSPECTION)

    for item in report.get("gold_files", []):
        print_json(
            "GOLD FILE: " + Path(item["path"]).name,
            {
                k: item.get(k)
                for k in (
                    "path", "exists", "records", "unique_problem_ids",
                    "missing_problem_id_records", "duplicate_problem_ids",
                    "first_record_keys", "first_records", "sha256"
                )
            }
        )

    print_json("ADJUDICATION CSV", report.get("adjudication_csv"))
    print_json("STUDENT PREDICTIONS", report.get("prediction_file"))
    print_json("EVALUATION SUMMARY", report.get("evaluation_summary"))
    print_json("CHECKPOINT METADATA", report.get("checkpoint"))

    scripts = MANUAL / "scripts"

    print_source_context(
        scripts / "eval_student.py",
        [
            r"def ",
            r"add_argument",
            r"ground_truth",
            r"answer",
            r"correct",
            r"accuracy",
            r"write",
            r"jsonl",
            r"output",
            r"prediction",
            r"checkpoint",
            r"dev",
            r"normalize",
        ],
        before=3,
        after=10,
    )

    print_source_context(
        scripts / "student_common.py",
        [
            r"def ",
            r"GSM8K_TRAIN",
            r"problem_id",
            r"ground_truth",
            r"answer",
            r"normalize",
            r"load",
        ],
        before=3,
        after=10,
    )

    print_source_context(
        scripts / "download_gsm8k_train.py",
        [
            r"def extract_gsm8k_answer",
            r"def normalize_text",
            r"####",
            r"answer",
        ],
        before=3,
        after=15,
    )

    print_source_context(
        scripts / "train_round.py",
        [
            r"eval_student",
            r"student_ckpt",
            r"adapter_dir",
            r"output",
        ],
        before=3,
        after=8,
    )

    inventory_md = OUT / "student_capability_input_inventory.md"
    if inventory_md.exists():
        print("\n========== INPUT INVENTORY MARKDOWN ==========")
        print(inventory_md.read_text(encoding="utf-8-sig"))

    print("\nDETAIL_INSPECTION_STATUS: PASS")

if __name__ == "__main__":
    main()
