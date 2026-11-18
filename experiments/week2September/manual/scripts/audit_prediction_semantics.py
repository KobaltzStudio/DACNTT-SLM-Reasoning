import argparse
import csv
import hashlib
import importlib.util
import json
import sys
import zipfile
from collections import Counter
from datetime import datetime
from pathlib import Path, PurePosixPath


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def read_jsonl_bytes(data, label):
    rows = []
    errors = []
    try:
        content = data.decode("utf-8-sig")
    except Exception as exc:
        return [], [f"{label}:DECODE_ERROR:{exc}"]

    for line_no, line in enumerate(content.splitlines(), 1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
            if not isinstance(obj, dict):
                errors.append(f"{label}:LINE_{line_no}:NOT_OBJECT")
            else:
                rows.append(obj)
        except Exception as exc:
            errors.append(f"{label}:LINE_{line_no}:{type(exc).__name__}:{exc}")
    return rows, errors


def read_jsonl_file(path):
    return read_jsonl_bytes(path.read_bytes(), str(path))


def load_strict_correct(script_path):
    if not script_path.is_file():
        raise FileNotFoundError(f"CAPABILITY_EVAL_NOT_FOUND: {script_path}")

    spec = importlib.util.spec_from_file_location("capability_eval_audit_module", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("CAPABILITY_EVAL_IMPORT_SPEC_FAILED")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    fn = getattr(module, "strict_correct", None)
    if not callable(fn):
        raise RuntimeError("strict_correct_NOT_FOUND_OR_NOT_CALLABLE")

    return fn


def get_problem_id(row):
    value = row.get("problem_id")
    if value is None:
        value = row.get("id")
    return str(value).strip() if value is not None else ""


def evaluate_rows(rows, strict_fn, label):
    strict_counts = Counter()
    status_counts = Counter()
    verification_counts = Counter()
    correct_counts = Counter()
    missing_fields = Counter()
    strict_errors = []

    for index, row in enumerate(rows):
        status = row.get("status")
        verification = row.get("verification_status")
        correct = row.get("correct")

        status_counts[str(status)] += 1
        verification_counts[str(verification)] += 1
        correct_counts[str(correct)] += 1

        for key in ("problem_id", "status", "verification_status", "correct"):
            if key not in row:
                missing_fields[key] += 1

        try:
            result = strict_fn(row)
            strict_counts[str(bool(result))] += 1
        except Exception as exc:
            strict_errors.append(
                f"{label}:ROW_{index}:STRICT_CORRECT_ERROR:{type(exc).__name__}:{exc}"
            )

    return {
        "rows": len(rows),
        "status_counts": dict(status_counts),
        "verification_status_counts": dict(verification_counts),
        "correct_counts": dict(correct_counts),
        "strict_correct_counts": dict(strict_counts),
        "missing_required_field_counts": dict(missing_fields),
        "strict_error_count": len(strict_errors),
        "strict_errors": strict_errors[:20],
        "sample_keys": sorted(rows[0].keys()) if rows else [],
    }


def normalized_value(row, key):
    value = row.get(key)
    if value is None:
        return None
    if isinstance(value, str):
        return value.strip()
    return value


def compare_prediction_sets(source_rows, derived_rows):
    source_by_id = {get_problem_id(r): r for r in source_rows if get_problem_id(r)}
    derived_by_id = {get_problem_id(r): r for r in derived_rows if get_problem_id(r)}

    shared_ids = sorted(set(source_by_id) & set(derived_by_id))
    source_only = sorted(set(source_by_id) - set(derived_by_id))
    derived_only = sorted(set(derived_by_id) - set(source_by_id))

    candidate_fields = [
        "problem_id", "status", "verification_status", "correct",
        "parsed_answer", "ground_truth", "raw_output",
        "format_compliant", "hit_max_new_tokens", "output_tokens",
    ]

    field_differences = Counter()
    examples = []

    for problem_id in shared_ids:
        left = source_by_id[problem_id]
        right = derived_by_id[problem_id]
        differing = [
            key for key in candidate_fields
            if normalized_value(left, key) != normalized_value(right, key)
            and (key in left or key in right)
        ]
        for key in differing:
            field_differences[key] += 1
        if differing and len(examples) < 20:
            examples.append({
                "problem_id": problem_id,
                "differing_fields": differing,
                "source_status": left.get("status"),
                "derived_status": right.get("status"),
                "source_verification_status": left.get("verification_status"),
                "derived_verification_status": right.get("verification_status"),
                "source_correct": left.get("correct"),
                "derived_correct": right.get("correct"),
            })

    return {
        "source_rows": len(source_rows),
        "derived_rows": len(derived_rows),
        "shared_ids": len(shared_ids),
        "source_only_ids": len(source_only),
        "derived_only_ids": len(derived_only),
        "field_difference_counts": dict(field_differences),
        "examples": examples,
        "same_ids": not source_only and not derived_only,
        "same_compared_fields": not field_differences,
    }


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", required=True)
    parser.add_argument("--capability-eval", required=True)
    parser.add_argument("--derived-root", required=True)
    parser.add_argument("--output-root", required=True)
    args = parser.parse_args()

    archive_path = Path(args.archive).resolve()
    evaluator_path = Path(args.capability_eval).resolve()
    derived_root = Path(args.derived_root).resolve()
    output_root = Path(args.output_root).resolve()

    for path in (archive_path, evaluator_path):
        if not path.is_file():
            raise FileNotFoundError(f"REQUIRED_FILE_NOT_FOUND: {path}")

    strict_fn = load_strict_correct(evaluator_path)

    run_id = datetime.now().strftime("run_%Y%m%d_%H%M%S")
    out_dir = output_root / run_id
    out_dir.mkdir(parents=True, exist_ok=False)

    prediction_report = []
    comparisons = []
    fatal_errors = []

    with zipfile.ZipFile(archive_path, "r") as zf:
        bad = zf.testzip()
        if bad is not None:
            raise RuntimeError(f"ZIP_INTEGRITY_ERROR: {bad}")

        members = sorted(
            name for name in zf.namelist()
            if PurePosixPath(name).name.lower() == "eval_dev.jsonl"
            and len(PurePosixPath(name).parts) == 3
            and PurePosixPath(name).parts[0].startswith(("B2_seed", "B3_seed", "B4_seed", "B5_seed"))
            and PurePosixPath(name).parts[1] in ("S1", "S2", "S3")
        )

        if len(members) != 36:
            raise RuntimeError(f"EXPECTED_36_EVAL_DEV_FILES_FOUND_{len(members)}")

        for member in members:
            raw = zf.read(member)
            rows, errors = read_jsonl_bytes(raw, member)

            if errors:
                fatal_errors.extend(errors)

            ids = [get_problem_id(r) for r in rows]
            id_counts = Counter(ids)
            duplicate_ids = sorted(k for k, v in id_counts.items() if k and v > 1)
            missing_id_count = sum(1 for value in ids if not value)

            semantic = evaluate_rows(rows, strict_fn, member)
            parts = PurePosixPath(member).parts
            context = parts[0]
            round_name = parts[1]

            prediction_report.append({
                "context": context,
                "method": context.split("_")[0],
                "seed": context.split("_seed")[-1],
                "round": round_name,
                "member_path": member,
                "sha256": sha256(raw),
                "rows": len(rows),
                "unique_ids": len(set(ids) - {""}),
                "duplicate_id_count": len(duplicate_ids),
                "missing_id_count": missing_id_count,
                "status_counts": json.dumps(semantic["status_counts"], ensure_ascii=False, sort_keys=True),
                "verification_status_counts": json.dumps(semantic["verification_status_counts"], ensure_ascii=False, sort_keys=True),
                "correct_counts": json.dumps(semantic["correct_counts"], ensure_ascii=False, sort_keys=True),
                "strict_correct_counts": json.dumps(semantic["strict_correct_counts"], ensure_ascii=False, sort_keys=True),
                "missing_required_fields": json.dumps(semantic["missing_required_field_counts"], ensure_ascii=False, sort_keys=True),
                "strict_error_count": semantic["strict_error_count"],
                "sample_keys": json.dumps(semantic["sample_keys"], ensure_ascii=False),
            })

            if context == "B4_seed13":
                derived_name = f"eval_student_ckpt_00{round_name[-1]}_dev_status.jsonl"
                derived_path = derived_root / context / derived_name

                if derived_path.is_file():
                    derived_rows, derived_errors = read_jsonl_file(derived_path)
                    comparison = compare_prediction_sets(rows, derived_rows)
                    comparison.update({
                        "context": context,
                        "round": round_name,
                        "derived_path": str(derived_path),
                        "source_sha256": sha256(raw),
                        "derived_sha256": sha256(derived_path.read_bytes()),
                        "derived_json_error_count": len(derived_errors),
                        "derived_json_errors": derived_errors[:10],
                    })
                    comparisons.append(comparison)
                else:
                    comparisons.append({
                        "context": context,
                        "round": round_name,
                        "derived_path": str(derived_path),
                        "comparison_status": "DERIVED_FILE_NOT_FOUND",
                    })

    write_csv(out_dir / "prediction_semantics.csv", prediction_report)

    (out_dir / "b4_seed13_comparison.json").write_text(
        json.dumps(comparisons, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    summary = {
        "archive": str(archive_path),
        "capability_eval": str(evaluator_path),
        "strict_correct_source": __import__("inspect").getsource(strict_fn),
        "prediction_file_count": len(prediction_report),
        "strict_correct_errors": sum(int(r["strict_error_count"]) for r in prediction_report),
        "missing_required_fields_total": sum(
            sum(json.loads(r["missing_required_fields"]).values())
            for r in prediction_report
        ),
        "fatal_json_errors": fatal_errors[:50],
        "b4_seed13_comparison": comparisons,
    }

    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("PREDICTION_SEMANTICS_AUDIT=COMPLETED")
    print(f"PREDICTION_FILES={len(prediction_report)}")
    print(f"STRICT_CORRECT_ERRORS={summary['strict_correct_errors']}")
    print(f"MISSING_REQUIRED_FIELDS_TOTAL={summary['missing_required_fields_total']}")
    print(f"FATAL_JSON_ERRORS={len(fatal_errors)}")
    print(f"B4_SEED13_COMPARISONS={len(comparisons)}")
    print(f"OUTPUT_DIR={out_dir}")


if __name__ == "__main__":
    main()
