import csv
import json
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone

BASE = Path(__file__).resolve().parents[1]

AUDIT_DIR = BASE / "reports" / "capability" / "d3_audit"
SOURCE_DIR = BASE / "data" / "gold_vnext"
OUTPUT_DIR = BASE / "data" / "gold_vfinal"

HUMAN_INPUT = AUDIT_DIR / "adjudication_human_review.csv"
HUMAN_CONFIRMED = AUDIT_DIR / "adjudication_human_confirmed.csv"

BATCH_INPUT = SOURCE_DIR / "batch_100_annotations_vnext.jsonl"
SUPPLEMENT_INPUT = SOURCE_DIR / "supplement_annotations_vnext.jsonl"

BATCH_OUTPUT = OUTPUT_DIR / "batch_100_annotations_vfinal.jsonl"
SUPPLEMENT_OUTPUT = OUTPUT_DIR / "supplement_annotations_vfinal.jsonl"

MANIFEST_OUTPUT = OUTPUT_DIR / "gold_vfinal_manifest.json"
VALIDATION_OUTPUT = AUDIT_DIR / "gold_vfinal_validation.json"

VALID_CAPABILITIES = {
    "addition",
    "subtraction",
    "multiplication",
    "division",
    "percentage",
    "fraction",
    "ratio",
}

VALID_DIFFICULTIES = {"easy", "medium", "hard"}

EXPECTED_BATCH = 100
EXPECTED_SUPPLEMENT = 85
EXPECTED_TOTAL = 185


def read_jsonl(path):
    if not path.exists():
        raise FileNotFoundError(f"Missing input file: {path}")

    records = []
    with path.open("r", encoding="utf-8-sig") as f:
        for line_number, line in enumerate(f, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON at {path}:{line_number}"
                ) from exc

            if not isinstance(record, dict):
                raise ValueError(
                    f"Expected JSON object at {path}:{line_number}"
                )

            records.append(record)

    return records


def write_jsonl(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def parse_capabilities(value, field_name, problem_id):
    if isinstance(value, list):
        labels = value
    else:
        raw = str(value or "").strip()

        if not raw:
            raise ValueError(
                f"Empty {field_name} for {problem_id}"
            )

        # Accept JSON array or semicolon-separated values.
        if raw.startswith("["):
            try:
                labels = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON in {field_name} for {problem_id}"
                ) from exc
        else:
            labels = [x.strip() for x in raw.split(";") if x.strip()]

    if not isinstance(labels, list):
        raise ValueError(
            f"{field_name} must be a list for {problem_id}"
        )

    labels = [str(x).strip() for x in labels]

    if len(labels) != len(set(labels)):
        raise ValueError(
            f"Duplicate capabilities for {problem_id}: {labels}"
        )

    invalid = sorted(set(labels) - VALID_CAPABILITIES)
    if invalid:
        raise ValueError(
            f"Invalid capabilities for {problem_id}: {invalid}"
        )

    return sorted(labels)


def load_human_confirmations():
    if not HUMAN_INPUT.exists():
        raise FileNotFoundError(HUMAN_INPUT)

    with HUMAN_INPUT.open(
        "r", encoding="utf-8-sig", newline=""
    ) as f:
        rows = list(csv.DictReader(f))

    if len(rows) != 22:
        raise ValueError(
            f"Expected 22 adjudication rows, found {len(rows)}"
        )

    confirmations = {}
    confirmed_rows = []

    for row in rows:
        problem_id = row.get("problem_id", "").strip()

        if not problem_id:
            raise ValueError("An adjudication row has an empty problem_id")

        if problem_id in confirmations:
            raise ValueError(f"Duplicate adjudication ID: {problem_id}")

        if str(row.get("question_matches_raw", "")).lower() != "true":
            raise ValueError(
                f"Question/raw mismatch for {problem_id}"
            )

        # The project team explicitly confirmed the current AI decisions
        # in the conversation on 2026-11-06, without requesting revisions.
        capabilities = parse_capabilities(
            row.get("final_capabilities", ""),
            "final_capabilities",
            problem_id,
        )

        difficulty = str(
            row.get("final_difficulty", "")
        ).strip().lower()

        if difficulty not in VALID_DIFFICULTIES:
            raise ValueError(
                f"Invalid final difficulty for {problem_id}: {difficulty}"
            )

        confirmed = dict(row)
        confirmed["human_review_status"] = "CONFIRMED"
        confirmed["human_confirmed_capabilities"] = ";".join(capabilities)
        confirmed["human_confirmed_difficulty"] = difficulty
        confirmed["human_reviewer"] = "Project team (chat confirmation)"
        confirmed["human_review_notes"] = (
            "The project team explicitly confirmed the current AI "
            "adjudication in the conversation on 2026-11-06. "
            "No label or difficulty revision was requested."
        )

        confirmed_rows.append(confirmed)
        confirmations[problem_id] = {
            "capabilities": capabilities,
            "difficulty": difficulty,
        }

    fields = list(confirmed_rows[0].keys())

    HUMAN_CONFIRMED.parent.mkdir(parents=True, exist_ok=True)
    with HUMAN_CONFIRMED.open(
        "w", encoding="utf-8-sig", newline=""
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fields,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(confirmed_rows)

    return confirmations


def index_records(records, label):
    result = {}

    for record in records:
        problem_id = record.get("problem_id")

        if not problem_id:
            raise ValueError(f"{label} contains a record without problem_id")

        if problem_id in result:
            raise ValueError(
                f"Duplicate problem_id in {label}: {problem_id}"
            )

        result[problem_id] = record

    return result


def apply_confirmations(records, confirmations, source_name):
    output = []

    for original in records:
        record = dict(original)
        problem_id = record["problem_id"]

        if problem_id in confirmations:
            if "capabilities_manual" not in record:
                raise ValueError(
                    f"{source_name}: missing capabilities_manual "
                    f"for adjudicated ID {problem_id}"
                )

            if "difficulty_manual" not in record:
                raise ValueError(
                    f"{source_name}: missing difficulty_manual "
                    f"for adjudicated ID {problem_id}"
                )

            decision = confirmations[problem_id]
            record["capabilities_manual"] = decision["capabilities"]
            record["difficulty_manual"] = decision["difficulty"]

        output.append(record)

    return output


def compare_records(source_records, final_records, confirmations):
    source_by_id = index_records(source_records, "Gold vNext")
    final_by_id = index_records(final_records, "Gold vFinal")

    if set(source_by_id) != set(final_by_id):
        raise ValueError("Gold vNext and Gold vFinal ID inventories differ")

    changed_capabilities = 0
    changed_difficulties = 0
    unadjudicated_changes = []
    immutable_field_changes = []

    for problem_id, source in source_by_id.items():
        final = final_by_id[problem_id]

        if source.get("capabilities_manual") != final.get("capabilities_manual"):
            changed_capabilities += 1

        if source.get("difficulty_manual") != final.get("difficulty_manual"):
            changed_difficulties += 1

        if problem_id not in confirmations and source != final:
            unadjudicated_changes.append(problem_id)

        # All fields other than the two adjudicated label fields must remain
        # unchanged for every record.
        source_other = {
            k: v for k, v in source.items()
            if k not in {"capabilities_manual", "difficulty_manual"}
        }
        final_other = {
            k: v for k, v in final.items()
            if k not in {"capabilities_manual", "difficulty_manual"}
        }

        if source_other != final_other:
            immutable_field_changes.append(problem_id)

    if unadjudicated_changes:
        raise ValueError(
            f"Unadjudicated records changed: {unadjudicated_changes[:10]}"
        )

    if immutable_field_changes:
        raise ValueError(
            "Non-label fields changed: "
            f"{immutable_field_changes[:10]}"
        )

    return {
        "changed_capability_records": changed_capabilities,
        "changed_difficulty_records": changed_difficulties,
        "unadjudicated_changes": len(unadjudicated_changes),
        "non_label_field_changes": len(immutable_field_changes),
    }


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)

    confirmations = load_human_confirmations()

    batch_vnext = read_jsonl(BATCH_INPUT)
    supplement_vnext = read_jsonl(SUPPLEMENT_INPUT)

    if len(batch_vnext) != EXPECTED_BATCH:
        raise ValueError(
            f"Expected {EXPECTED_BATCH} batch records, found {len(batch_vnext)}"
        )

    if len(supplement_vnext) != EXPECTED_SUPPLEMENT:
        raise ValueError(
            f"Expected {EXPECTED_SUPPLEMENT} supplement records, "
            f"found {len(supplement_vnext)}"
        )

    batch_ids = set(index_records(batch_vnext, "batch vNext"))
    supplement_ids = set(index_records(supplement_vnext, "supplement vNext"))

    overlap = batch_ids & supplement_ids
    if overlap:
        raise ValueError(
            f"Duplicate IDs across batch and supplement: {sorted(overlap)}"
        )

    all_source_ids = batch_ids | supplement_ids

    missing_decisions = sorted(set(confirmations) - all_source_ids)
    if missing_decisions:
        raise ValueError(
            f"Adjudication IDs missing from Gold vNext: {missing_decisions}"
        )

    batch_vfinal = apply_confirmations(
        batch_vnext, confirmations, "batch"
    )
    supplement_vfinal = apply_confirmations(
        supplement_vnext, confirmations, "supplement"
    )

    write_jsonl(BATCH_OUTPUT, batch_vfinal)
    write_jsonl(SUPPLEMENT_OUTPUT, supplement_vfinal)

    all_vnext = batch_vnext + supplement_vnext
    all_vfinal = batch_vfinal + supplement_vfinal

    comparison = compare_records(
        all_vnext, all_vfinal, confirmations
    )

    final_ids = [
        record["problem_id"] for record in all_vfinal
    ]

    if len(final_ids) != EXPECTED_TOTAL:
        raise ValueError(
            f"Expected {EXPECTED_TOTAL} final records, found {len(final_ids)}"
        )

    if len(final_ids) != len(set(final_ids)):
        raise ValueError("Duplicate IDs in Gold vFinal")

    for record in all_vfinal:
        labels = record.get("capabilities_manual")
        difficulty = record.get("difficulty_manual")

        if not isinstance(labels, list):
            raise ValueError(
                f"capabilities_manual must be a list: {record['problem_id']}"
            )

        invalid = sorted(set(labels) - VALID_CAPABILITIES)
        if invalid:
            raise ValueError(
                f"Invalid labels for {record['problem_id']}: {invalid}"
            )

        if difficulty not in VALID_DIFFICULTIES:
            raise ValueError(
                f"Invalid difficulty for {record['problem_id']}: {difficulty}"
            )

    manifest = {
        "gold_version": "vFinal",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_version": "Gold vNext",
        "human_confirmation_source": (
            "adjudication_human_review.csv plus explicit project-team "
            "confirmation in conversation on 2026-11-06"
        ),
        "human_confirmed_adjudication_count": len(confirmations),
        "batch_count": len(batch_vfinal),
        "supplement_count": len(supplement_vfinal),
        "total_count": len(all_vfinal),
        "unique_problem_ids": len(set(final_ids)),
        "ground_truth_policy": (
            "No ground-truth/source-answer fields are modified by this script."
        ),
        "comparison_against_vnext": comparison,
        "files": {
            "batch": str(BATCH_OUTPUT.relative_to(BASE)),
            "supplement": str(SUPPLEMENT_OUTPUT.relative_to(BASE)),
            "human_confirmation": str(
                HUMAN_CONFIRMED.relative_to(BASE)
            ),
        },
    }

    MANIFEST_OUTPUT.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    validation = {
        "status": "PASS",
        "checks": {
            "batch_count_100": len(batch_vfinal) == EXPECTED_BATCH,
            "supplement_count_85": len(supplement_vfinal) == EXPECTED_SUPPLEMENT,
            "total_count_185": len(all_vfinal) == EXPECTED_TOTAL,
            "unique_ids_185": len(set(final_ids)) == EXPECTED_TOTAL,
            "batch_supplement_no_overlap": not bool(overlap),
            "all_22_adjudications_confirmed": len(confirmations) == 22,
            "all_adjudication_ids_exist": not bool(missing_decisions),
            "all_capabilities_valid": all(
                set(r["capabilities_manual"]) <= VALID_CAPABILITIES
                for r in all_vfinal
            ),
            "all_difficulties_valid": all(
                r["difficulty_manual"] in VALID_DIFFICULTIES
                for r in all_vfinal
            ),
            "no_unadjudicated_changes": (
                comparison["unadjudicated_changes"] == 0
            ),
            "no_non_label_field_changes": (
                comparison["non_label_field_changes"] == 0
            ),
        },
        "counts": {
            "batch": len(batch_vfinal),
            "supplement": len(supplement_vfinal),
            "total": len(all_vfinal),
            "confirmed_adjudications": len(confirmations),
            **comparison,
        },
    }

    if not all(validation["checks"].values()):
        validation["status"] = "FAIL"

    VALIDATION_OUTPUT.write_text(
        json.dumps(validation, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("GOLD VFINAL BUILD")
    print(f"Confirmed adjudications: {len(confirmations)}")
    print(f"Batch records: {len(batch_vfinal)}")
    print(f"Supplement records: {len(supplement_vfinal)}")
    print(f"Total records: {len(all_vfinal)}")
    print(f"Changed capability records: {comparison['changed_capability_records']}")
    print(f"Changed difficulty records: {comparison['changed_difficulty_records']}")
    print(f"Unadjudicated changes: {comparison['unadjudicated_changes']}")
    print(f"Non-label field changes: {comparison['non_label_field_changes']}")
    print(f"Human confirmation CSV: {HUMAN_CONFIRMED}")
    print(f"Manifest: {MANIFEST_OUTPUT}")
    print(f"Validation: {VALIDATION_OUTPUT}")
    print(f"Status: {validation['status']}")

    if validation["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
