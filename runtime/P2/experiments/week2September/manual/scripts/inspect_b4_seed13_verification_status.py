import json
from collections import Counter
from pathlib import Path

ROOT = Path(
    r"C:\Users\PC - NGHI\Desktop\Pipeline\P2\experiments\week2September\manual"
)

PRED_DIR = (
    ROOT
    / "integration_staging"
    / "P1"
    / "reports"
    / "task7"
    / "B4"
    / "seed_13"
)

CHECKPOINTS = [
    "student_ckpt_001",
    "student_ckpt_002",
    "student_ckpt_003",
]

def load_rows(path):
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except Exception as exc:
                raise RuntimeError(
                    f"Invalid JSON at {path}:{line_no}: {exc}"
                )
    return rows

def value_label(value):
    if value is None:
        return "<MISSING_OR_NULL>"
    if isinstance(value, bool):
        return f"bool:{value}"
    return f"{type(value).__name__}:{value}"

def main():
    report = []

    for index, checkpoint in enumerate(CHECKPOINTS, start=1):
        prediction = (
            PRED_DIR / f"eval_{checkpoint}_dev.jsonl"
        )

        print("\n" + "=" * 88)
        print("CHECKPOINT:", checkpoint)
        print("PREDICTION:", prediction)
        print("EXISTS:", prediction.exists())

        if not prediction.exists():
            report.append({
                "checkpoint": checkpoint,
                "error": "prediction_file_missing",
                "path": str(prediction),
            })
            continue

        rows = load_rows(prediction)

        verification_counts = Counter(
            value_label(row.get("verification_status"))
            for row in rows
        )

        correct_verification_pairs = Counter(
            (
                value_label(row.get("correct")),
                value_label(row.get("verification_status")),
            )
            for row in rows
        )

        format_counts = Counter(
            value_label(row.get("format_compliant"))
            for row in rows
        )

        parsed_answer_counts = Counter(
            value_label(row.get("parsed_answer"))
            for row in rows
        )

        print("RECORDS:", len(rows))
        print("VERIFICATION_STATUS_COUNTS:")
        for key, count in sorted(verification_counts.items()):
            print(f"  {key}: {count}")

        print("FORMAT_COMPLIANT_COUNTS:")
        for key, count in sorted(format_counts.items()):
            print(f"  {key}: {count}")

        print("CORRECT x VERIFICATION_STATUS:")
        for key, count in sorted(correct_verification_pairs.items()):
            print(f"  {key}: {count}")

        print("PARSED_ANSWER_COUNTS:")
        for key, count in sorted(parsed_answer_counts.items()):
            print(f"  {key}: {count}")

        print("SAMPLE_ROWS:")
        for row in rows[:3]:
            sample = {
                key: row.get(key)
                for key in [
                    "problem_id",
                    "correct",
                    "lenient_correct",
                    "format_compliant",
                    "verification_status",
                    "parsed_answer",
                    "ground_truth",
                    "hit_max_new_tokens",
                ]
            }
            print(json.dumps(sample, ensure_ascii=False))

        report.append({
            "checkpoint": checkpoint,
            "prediction_path": str(prediction),
            "records": len(rows),
            "verification_status_counts": dict(verification_counts),
            "format_compliant_counts": dict(format_counts),
            "correct_verification_pairs": {
                f"{a} | {b}": count
                for (a, b), count in correct_verification_pairs.items()
            },
        })

    output = ROOT / "reports" / "p1p2_integration"
    output.mkdir(parents=True, exist_ok=True)

    report_path = output / "b4_seed13_verification_status_audit.json"
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("\nREPORT:", report_path)

if __name__ == "__main__":
    main()
