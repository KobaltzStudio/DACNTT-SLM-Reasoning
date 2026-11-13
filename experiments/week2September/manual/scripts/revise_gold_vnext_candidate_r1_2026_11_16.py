from __future__ import annotations

import csv
import hashlib
import json
import shutil
from pathlib import Path


BASE = Path(__file__).resolve().parents[1]

SOURCE_DIR = BASE / "data/gold_vnext_candidate_2026-11-16"
REVISION_DIR = BASE / "data/gold_vnext_candidate_2026-11-16_r1"

REPORT_DIR = BASE / "reports/gold/review_2026-11-16"

BATCH_NAME = "batch_100_annotations_vnext.jsonl"
SUPPLEMENT_NAME = "supplement_annotations_vnext.jsonl"
MANIFEST_NAME = "gold_vnext_manifest.json"

LEDGER_PATH = REPORT_DIR / "user_adjudication_2026-11-16.csv"
FINAL_REPORT_PATH = REPORT_DIR / "gold_review_63_final_adjudication.md"
VALIDATION_JSON_PATH = REPORT_DIR / "gold_review_63_validation_report.json"
VALIDATION_MD_PATH = REPORT_DIR / "gold_review_63_validation_report.md"

REVISED_NOTES = {
    "gsm8k_train_00713": (
        "Adjudicated decision: retain the dataset target answer 15% and mark "
        "this problem as ambiguous. The intended calculation assumes: "
        "(1) malaria-infected and Zika-infected mosquito groups are disjoint; "
        "(2) the stated 50% vaccine reduction applies to post-bite infection "
        "risk for both malaria and Zika. Assumption (2) is not established by "
        "the literal wording 'malaria vaccine'. Therefore, 15% is retained "
        "as the intended dataset target under these assumptions, but must "
        "not be described as the mathematically certain result of a "
        "malaria-only vaccine model."
    ),
    "gsm8k_train_00830": (
        "Adjudicated capability labels: addition, subtraction, multiplication, "
        "percentage. Subtraction is included because the separately supplied "
        "source variant derives the mango lassi price as "
        "25 - (18 + 4.50) = 2.50. Important source distinction: the current "
        "raw dataset record states that the lassi costs $2, asks for the total "
        "meal cost, and has ground truth 25. The alternate source variant "
        "asks for the lassi price and derives $2.50. These are different "
        "question targets. Preserve the current raw record's ground truth 25; "
        "do not replace it with $2.50. The current raw question's wording "
        "'with tax' is not accompanied by a separately calculated tax amount."
    ),
}


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8-sig") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL {path}:{line_no}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"Expected JSON object at {path}:{line_no}")
            rows.append(row)
    return rows


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"Refusing to write empty CSV: {path}")
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def index_by_id(rows: list[dict], label: str) -> dict[str, dict]:
    result = {}
    for row in rows:
        pid = row.get("problem_id")
        if not pid:
            raise ValueError(f"{label}: missing problem_id")
        if pid in result:
            raise ValueError(f"{label}: duplicate problem_id {pid}")
        result[pid] = row
    return result


def main() -> None:
    print("Manual root:", BASE)
    print("Source candidate:", SOURCE_DIR)
    print("Revision candidate:", REVISION_DIR)

    if not SOURCE_DIR.is_dir():
        raise FileNotFoundError(SOURCE_DIR)

    if REVISION_DIR.exists():
        raise FileExistsError(
            f"Revision already exists; refusing to overwrite: {REVISION_DIR}"
        )

    required = [
        SOURCE_DIR / BATCH_NAME,
        SOURCE_DIR / SUPPLEMENT_NAME,
        SOURCE_DIR / MANIFEST_NAME,
        LEDGER_PATH,
        FINAL_REPORT_PATH,
        VALIDATION_JSON_PATH,
        VALIDATION_MD_PATH,
    ]
    missing = [str(p) for p in required if not p.is_file()]
    if missing:
        raise FileNotFoundError("Missing required files:\n" + "\n".join(missing))

    source_batch_path = SOURCE_DIR / BATCH_NAME
    source_supplement_path = SOURCE_DIR / SUPPLEMENT_NAME
    source_manifest_path = SOURCE_DIR / MANIFEST_NAME

    parent_hashes_before = {
        "batch": sha256(source_batch_path),
        "supplement": sha256(source_supplement_path),
        "manifest": sha256(source_manifest_path),
    }

    source_batch = read_jsonl(source_batch_path)
    source_supplement = read_jsonl(source_supplement_path)
    source_batch_by_id = index_by_id(source_batch, "source batch")
    source_supplement_by_id = index_by_id(
        source_supplement, "source supplement"
    )

    if len(source_batch) != 100 or len(source_supplement) != 85:
        raise ValueError("Unexpected source candidate record counts.")

    if not set(REVISED_NOTES) <= set(source_supplement_by_id):
        raise ValueError("One or more target IDs are missing from supplement.")

    # Load ledger and verify it contains the same two adjudicated IDs.
    ledger = read_csv(LEDGER_PATH)
    ledger_by_id = index_by_id(ledger, "adjudication ledger")

    if len(ledger) != 63:
        raise ValueError(f"Expected 63 ledger rows, got {len(ledger)}")

    if not set(REVISED_NOTES) <= set(ledger_by_id):
        raise ValueError("One or more target IDs are missing from ledger.")

    # Create a new revision folder. The original candidate remains untouched.
    REVISION_DIR.mkdir(parents=True)

    try:
        revision_batch_path = REVISION_DIR / BATCH_NAME
        revision_supplement_path = REVISION_DIR / SUPPLEMENT_NAME
        revision_manifest_path = REVISION_DIR / MANIFEST_NAME

        # Preserve batch 100 byte-for-byte.
        shutil.copyfile(source_batch_path, revision_batch_path)

        revised_supplement = []
        for old_row in source_supplement:
            row = dict(old_row)
            pid = row["problem_id"]
            if pid in REVISED_NOTES:
                row["notes"] = REVISED_NOTES[pid]
            revised_supplement.append(row)

        write_jsonl(revision_supplement_path, revised_supplement)

        revised_supplement_by_id = index_by_id(
            revised_supplement, "revision supplement"
        )

        # Confirm that only notes for the two intended IDs changed.
        unexpected_changes = []
        for pid, old_row in source_supplement_by_id.items():
            new_row = revised_supplement_by_id[pid]

            if pid in REVISED_NOTES:
                old_without_notes = {
                    k: v for k, v in old_row.items() if k != "notes"
                }
                new_without_notes = {
                    k: v for k, v in new_row.items() if k != "notes"
                }
                if old_without_notes != new_without_notes:
                    unexpected_changes.append(pid)
            elif old_row != new_row:
                unexpected_changes.append(pid)

        if unexpected_changes:
            raise ValueError(
                "Unexpected supplement changes: "
                + ", ".join(unexpected_changes)
            )

        if sha256(source_batch_path) != sha256(revision_batch_path):
            raise ValueError("Batch 100 is not byte-identical.")

        # Confirm inventory and record schema.
        if set(source_batch_by_id) != set(index_by_id(
            read_jsonl(revision_batch_path), "revision batch"
        )):
            raise ValueError("Batch inventory changed.")

        if set(source_supplement_by_id) != set(revised_supplement_by_id):
            raise ValueError("Supplement inventory changed.")

        expected_fields = {
            "problem_id",
            "capabilities_manual",
            "difficulty_manual",
            "notes",
            "annotator_id",
            "schema_version",
        }

        schema_errors = []
        for split_name, rows in [
            ("batch", read_jsonl(revision_batch_path)),
            ("supplement", revised_supplement),
        ]:
            for row in rows:
                if set(row) != expected_fields:
                    schema_errors.append(
                        f"{split_name}:{row.get('problem_id')}:fields"
                    )
                if row.get("schema_version") != "v1":
                    schema_errors.append(
                        f"{split_name}:{row.get('problem_id')}:schema_version"
                    )
                if not isinstance(row.get("capabilities_manual"), list):
                    schema_errors.append(
                        f"{split_name}:{row.get('problem_id')}:capabilities"
                    )

        if schema_errors:
            raise ValueError("Schema errors: " + "; ".join(schema_errors[:20]))

        # Update the adjudication ledger so it matches the revised candidate.
        for pid, note in REVISED_NOTES.items():
            ledger_by_id[pid]["final_annotation_notes"] = note

        write_csv(LEDGER_PATH, ledger)

        # Update manifest with revision lineage and fresh hashes.
        with source_manifest_path.open("r", encoding="utf-8-sig") as f:
            manifest = json.load(f)

        manifest["version"] = "vNext-candidate-2026-11-16-r1"
        manifest["candidate_status"] = "VALIDATED_PENDING_USER_APPROVAL"
        manifest["freeze_status"] = "NOT_FROZEN"
        manifest["revision"] = 1
        manifest["revision_reason"] = (
            "Resolve contradictory legacy annotation notes for "
            "gsm8k_train_00713 and gsm8k_train_00830."
        )
        manifest["parent_candidate"] = (
            "data/gold_vnext_candidate_2026-11-16"
        )
        manifest["revision_scope"] = {
            "notes_only_ids": sorted(REVISED_NOTES),
            "capabilities_modified": False,
            "difficulty_modified": False,
            "ground_truth_modified": False,
        }
        manifest["candidate_sha256"] = {
            "batch": sha256(revision_batch_path),
            "supplement": sha256(revision_supplement_path),
        }
        manifest["approval_required_before_freeze"] = True
        manifest["validation_status"] = "PASS"

        revision_manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # Re-read revision files and perform final checks.
        final_batch = read_jsonl(revision_batch_path)
        final_supplement = read_jsonl(revision_supplement_path)
        final_supplement_by_id = index_by_id(
            final_supplement, "final revision supplement"
        )

        checks = [
            {
                "name": "batch_count_100",
                "passed": len(final_batch) == 100,
                "detail": len(final_batch),
            },
            {
                "name": "supplement_count_85",
                "passed": len(final_supplement) == 85,
                "detail": len(final_supplement),
            },
            {
                "name": "total_unique_185",
                "passed": (
                    len(set(
                        index_by_id(final_batch, "final batch")
                    ) | set(final_supplement_by_id)) == 185
                ),
                "detail": 185,
            },
            {
                "name": "batch_byte_identical_to_parent",
                "passed": (
                    sha256(revision_batch_path) == sha256(source_batch_path)
                ),
                "detail": sha256(revision_batch_path),
            },
            {
                "name": "only_two_notes_changed",
                "passed": not unexpected_changes,
                "detail": sorted(REVISED_NOTES),
            },
            {
                "name": "target_notes_replaced",
                "passed": all(
                    final_supplement_by_id[pid]["notes"] == note
                    for pid, note in REVISED_NOTES.items()
                ),
                "detail": sorted(REVISED_NOTES),
            },
            {
                "name": "ledger_63_rows",
                "passed": len(ledger) == 63,
                "detail": len(ledger),
            },
            {
                "name": "ledger_notes_match_candidate",
                "passed": all(
                    ledger_by_id[pid]["final_annotation_notes"] == note
                    for pid, note in REVISED_NOTES.items()
                ),
                "detail": sorted(REVISED_NOTES),
            },
            {
                "name": "source_candidate_unchanged",
                "passed": (
                    sha256(source_batch_path) == parent_hashes_before["batch"]
                    and sha256(source_supplement_path) == parent_hashes_before["supplement"]
                    and sha256(source_manifest_path) == parent_hashes_before["manifest"]
                ),
                "detail": parent_hashes_before,
            },
        ]

        failed = [item for item in checks if not item["passed"]]
        if failed:
            raise RuntimeError(
                "Revision validation failed: "
                + json.dumps(failed, ensure_ascii=False)
            )

        validation = {
            "status": "PASS",
            "candidate_status": "VALIDATED_PENDING_USER_APPROVAL",
            "freeze_status": "NOT_FROZEN",
            "revision": 1,
            "parent_candidate": str(SOURCE_DIR),
            "revision_candidate": str(REVISION_DIR),
            "records": {
                "batch": len(final_batch),
                "supplement": len(final_supplement),
                "total": len(final_batch) + len(final_supplement),
                "notes_revised": len(REVISED_NOTES),
                "ledger_rows": len(ledger),
            },
            "revised_note_ids": sorted(REVISED_NOTES),
            "checks": checks,
            "source_candidate_hashes": {
                "batch": sha256(source_batch_path),
                "supplement": sha256(source_supplement_path),
                "manifest": sha256(source_manifest_path),
            },
            "revision_candidate_hashes": {
                "batch": sha256(revision_batch_path),
                "supplement": sha256(revision_supplement_path),
                "manifest": sha256(revision_manifest_path),
            },
            "gold_vfinal_modified": False,
            "raw_ground_truth_modified": False,
            "freeze_status_note": (
                "Revision is validated but not frozen. User approval required."
            ),
        }

        validation_json = REPORT_DIR / (
            "gold_review_63_validation_report_r1.json"
        )
        validation_md = REPORT_DIR / (
            "gold_review_63_validation_report_r1.md"
        )

        validation_json.write_text(
            json.dumps(validation, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        md = [
            "# Gold vNext Candidate Revision r1 Validation",
            "",
            "- Status: **PASS**",
            "- Candidate status: **VALIDATED_PENDING_USER_APPROVAL**",
            "- Freeze status: **NOT FROZEN**",
            "- Batch records: **100**",
            "- Supplement records: **85**",
            "- Total records: **185**",
            "- Revised notes: **2**",
            "- Ledger rows: **63**",
            "",
            "## Revised records",
            "",
            "- `gsm8k_train_00713`: replaced contradictory note; retained 15% "
            "with explicit vaccine-scope and disjoint-group assumptions.",
            "- `gsm8k_train_00830`: replaced contradictory note; added "
            "subtraction and retained raw ground truth 25 separately from "
            "the alternate variant's $2.50 target.",
            "",
            "## Checks",
            "",
        ]

        for item in checks:
            md.append(
                f"- **{'PASS' if item['passed'] else 'FAIL'}** "
                f"`{item['name']}`: {item['detail']}"
            )

        md += [
            "",
            "## Source protection",
            "",
            "- Parent candidate retained unchanged.",
            "- Gold vFinal not modified.",
            "- Raw ground truth not modified.",
            "- Batch copied byte-for-byte from parent candidate.",
            "- Only the two specified supplement notes were revised.",
            "- Freeze status remains NOT FROZEN.",
            "",
        ]

        validation_md.write_text("\n".join(md), encoding="utf-8")

        # Update the final adjudication report with a revision note.
        report_text = FINAL_REPORT_PATH.read_text(encoding="utf-8")
        revision_section = (
            "\n## Revision r1 — note consistency correction\n\n"
            "- `gsm8k_train_00713`: replaced the contradictory legacy note. "
            "The 15% target remains accepted only under the two explicit "
            "assumptions; ambiguity remains flagged.\n"
            "- `gsm8k_train_00830`: replaced the contradictory legacy note. "
            "Subtraction is included; raw ground truth 25 remains distinct "
            "from the alternate variant's $2.50 target.\n"
            "- No capability, difficulty, or ground-truth values were changed "
            "by this revision.\n"
            "- Revision candidate: `gold_vnext_candidate_2026-11-16_r1`.\n"
            "- Freeze status: **NOT FROZEN**.\n"
        )

        if "## Revision r1 — note consistency correction" not in report_text:
            FINAL_REPORT_PATH.write_text(
                report_text.rstrip() + "\n" + revision_section,
                encoding="utf-8",
            )

        print()
        print("REVISION BUILD: PASS")
        print("Batch:", len(final_batch))
        print("Supplement:", len(final_supplement))
        print("Total:", len(final_batch) + len(final_supplement))
        print("Notes revised:", len(REVISED_NOTES))
        print("Ledger rows:", len(ledger))
        print("Candidate:", REVISION_DIR)
        print("Manifest:", revision_manifest_path)
        print("Validation JSON:", validation_json)
        print("Validation Markdown:", validation_md)
        print("Freeze status: NOT FROZEN")

    except Exception:
        print("REVISION BUILD FAILED.")
        print("Revision directory retained for inspection:", REVISION_DIR)
        raise


if __name__ == "__main__":
    main()

