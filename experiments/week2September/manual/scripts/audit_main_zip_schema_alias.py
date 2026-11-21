import argparse
import csv
import hashlib
import json
import zipfile
from collections import Counter
from datetime import datetime
from pathlib import PurePosixPath


def read_jsonl(data, label):
    rows = []
    errors = []
    for line_no, line in enumerate(data.decode("utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                rows.append(obj)
            else:
                errors.append(f"{label}:LINE_{line_no}:NOT_OBJECT")
        except Exception as exc:
            errors.append(f"{label}:LINE_{line_no}:{type(exc).__name__}:{exc}")
    return rows, errors


def get_id(row):
    value = row.get("problem_id")
    if value is None:
        value = row.get("id")
    return str(value).strip() if value is not None else ""


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def write_csv(path, rows):
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
    parser.add_argument("--output-root", required=True)
    args = parser.parse_args()

    from pathlib import Path
    archive = Path(args.archive).resolve()
    output_root = Path(args.output_root).resolve()

    if not archive.is_file():
        raise FileNotFoundError(f"ARCHIVE_NOT_FOUND: {archive}")

    run_id = datetime.now().strftime("run_%Y%m%d_%H%M%S")
    out = output_root / run_id
    out.mkdir(parents=True, exist_ok=False)

    predictions = {}
    schema_rows = []
    marker_rows = []
    errors = []

    with zipfile.ZipFile(archive, "r") as zf:
        bad = zf.testzip()
        if bad:
            raise RuntimeError(f"ZIP_INTEGRITY_ERROR: {bad}")

        for name in sorted(zf.namelist()):
            p = PurePosixPath(name)
            parts = p.parts

            is_prediction = (
                p.name.lower() == "eval_dev.jsonl"
                and len(parts) == 3
                and parts[0].startswith(("B2_seed", "B3_seed", "B4_seed", "B5_seed"))
                and parts[1] in ("S1", "S2", "S3")
            )

            if is_prediction:
                raw = zf.read(name)
                rows, parse_errors = read_jsonl(raw, name)
                errors.extend(parse_errors)

                context = parts[0]
                round_name = parts[1]
                predictions[(context, round_name)] = rows

                all_keys = sorted(set().union(*(r.keys() for r in rows))) if rows else []
                missing = {
                    key: sum(1 for row in rows if key not in row)
                    for key in ("problem_id", "id", "status",
                                "verification_status", "correct",
                                "parsed_answer", "raw_output")
                }

                schema_rows.append({
                    "context": context,
                    "round": round_name,
                    "member": name,
                    "sha256": sha256(raw),
                    "rows": len(rows),
                    "id_key_problem_id_count": sum("problem_id" in r for r in rows),
                    "id_key_id_count": sum("id" in r for r in rows),
                    "missing_problem_id": missing["problem_id"],
                    "missing_id": missing["id"],
                    "missing_status": missing["status"],
                    "missing_verification_status": missing["verification_status"],
                    "missing_correct": missing["correct"],
                    "missing_parsed_answer": missing["parsed_answer"],
                    "missing_raw_output": missing["raw_output"],
                    "status_counts": json.dumps(dict(Counter(str(r.get("status")) for r in rows)), sort_keys=True),
                    "all_keys": json.dumps(all_keys, ensure_ascii=False),
                })

            if ".done/" in name.replace("\\", "/") and (
                "eval_dev_" in p.name.lower()
                or "train_" in p.name.lower()
            ):
                raw = zf.read(name)
                try:
                    obj = json.loads(raw.decode("utf-8-sig"))
                    marker_rows.append({
                        "member": name,
                        "parse_status": "OK",
                        "content": json.dumps(obj, ensure_ascii=False, sort_keys=True),
                    })
                except Exception as exc:
                    marker_rows.append({
                        "member": name,
                        "parse_status": f"ERROR:{type(exc).__name__}:{exc}",
                        "content": raw.decode("utf-8-sig", errors="replace")[:2000],
                    })

    alias_rows = []
    compared_fields = (
        "status", "verification_status", "correct",
        "parsed_answer", "raw_output", "ground_truth",
        "format_compliant", "hit_max_new_tokens", "output_tokens"
    )

    for seed in ("13", "42", "2026"):
        b4 = predictions.get((f"B4_seed{seed}", "S1"), [])
        b5 = predictions.get((f"B5_seed{seed}", "S1"), [])

        b4_map = {get_id(r): r for r in b4 if get_id(r)}
        b5_map = {get_id(r): r for r in b5 if get_id(r)}
        common = sorted(set(b4_map) & set(b5_map))

        differences = Counter()
        examples = []

        for problem_id in common:
            left, right = b4_map[problem_id], b5_map[problem_id]
            changed = [
                key for key in compared_fields
                if left.get(key) != right.get(key)
                and (key in left or key in right)
            ]
            for key in changed:
                differences[key] += 1
            if changed and len(examples) < 10:
                examples.append({
                    "problem_id": problem_id,
                    "different_fields": changed,
                    "B4_status": left.get("status"),
                    "B5_status": right.get("status"),
                })

        alias_rows.append({
            "seed": seed,
            "B4_rows": len(b4),
            "B5_rows": len(b5),
            "B4_unique_ids": len(b4_map),
            "B5_unique_ids": len(b5_map),
            "shared_ids": len(common),
            "B4_only_ids": len(set(b4_map) - set(b5_map)),
            "B5_only_ids": len(set(b5_map) - set(b4_map)),
            "field_difference_counts": json.dumps(dict(differences), sort_keys=True),
            "exact_compared_content_match": not differences
                and set(b4_map) == set(b5_map),
            "examples": json.dumps(examples, ensure_ascii=False),
        })

    write_csv(out / "schema_inventory.csv", schema_rows)
    write_csv(out / "b4_b5_s1_alias_comparison.csv", alias_rows)
    write_csv(out / "done_marker_contents.csv", marker_rows)

    summary = {
        "archive": str(archive),
        "prediction_file_count": len(schema_rows),
        "marker_count": len(marker_rows),
        "json_error_count": len(errors),
        "json_errors": errors[:50],
        "b4_b5_s1_comparison": alias_rows,
    }
    (out / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("SCHEMA_ALIAS_AUDIT=COMPLETED")
    print(f"PREDICTION_FILES={len(schema_rows)}")
    print(f"DONE_MARKERS={len(marker_rows)}")
    print(f"JSON_ERRORS={len(errors)}")
    print(f"OUTPUT_DIR={out}")


if __name__ == "__main__":
    main()
