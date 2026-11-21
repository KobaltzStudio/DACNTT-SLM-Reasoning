from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]

PARENT_DIR = BASE / "data/gold_vnext_candidate_2026-11-16"
R1_DIR = BASE / "data/gold_vnext_candidate_2026-11-16_r1"
REPORT_DIR = BASE / "reports/gold/review_2026-11-16"

BATCH = "batch_100_annotations_vnext.jsonl"
SUPPLEMENT = "supplement_annotations_vnext.jsonl"
MANIFEST = "gold_vnext_manifest.json"

LEDGER = REPORT_DIR / "user_adjudication_2026-11-16.csv"
FINAL_REPORT = REPORT_DIR / "gold_review_63_final_adjudication.md"

OUT_JSON = REPORT_DIR / "gold_review_63_postbuild_audit_r1.json"
OUT_MD = REPORT_DIR / "gold_review_63_postbuild_audit_r1.md"

EXPECTED_NOTES = {
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

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))

def read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8-sig") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError(f"Expected object: {path}:{line_no}")
            rows.append(row)
    return rows

def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def index(rows: list[dict], label: str) -> dict[str, dict]:
    result = {}
    for row in rows:
        pid = row.get("problem_id")
        if not pid or pid in result:
            raise ValueError(f"{label}: missing/duplicate problem_id {pid}")
        result[pid] = row
    return result

def add_check(checks, name, passed, detail):
    checks.append({
        "name": name,
        "passed": bool(passed),
        "detail": detail,
    })

def main():
    required = [
        PARENT_DIR / BATCH,
        PARENT_DIR / SUPPLEMENT,
        PARENT_DIR / MANIFEST,
        R1_DIR / BATCH,
        R1_DIR / SUPPLEMENT,
        R1_DIR / MANIFEST,
        LEDGER,
        FINAL_REPORT,
    ]
    missing = [str(p) for p in required if not p.is_file()]
    if missing:
        raise FileNotFoundError("Missing files:\n" + "\n".join(missing))

    checks = []

    parent_manifest = read_json(PARENT_DIR / MANIFEST)
    r1_manifest = read_json(R1_DIR / MANIFEST)

    parent_batch = read_jsonl(PARENT_DIR / BATCH)
    parent_supp = read_jsonl(PARENT_DIR / SUPPLEMENT)
    r1_batch = read_jsonl(R1_DIR / BATCH)
    r1_supp = read_jsonl(R1_DIR / SUPPLEMENT)

    parent_batch_idx = index(parent_batch, "parent batch")
    parent_supp_idx = index(parent_supp, "parent supplement")
    r1_batch_idx = index(r1_batch, "r1 batch")
    r1_supp_idx = index(r1_supp, "r1 supplement")

    # Record counts and inventory.
    add_check(checks, "parent_batch_100", len(parent_batch) == 100, len(parent_batch))
    add_check(checks, "parent_supplement_85", len(parent_supp) == 85, len(parent_supp))
    add_check(checks, "r1_batch_100", len(r1_batch) == 100, len(r1_batch))
    add_check(checks, "r1_supplement_85", len(r1_supp) == 85, len(r1_supp))

    overlap = set(r1_batch_idx) & set(r1_supp_idx)
    union_count = len(set(r1_batch_idx) | set(r1_supp_idx))
    add_check(checks, "batch_supplement_disjoint", not overlap, sorted(overlap))
    add_check(checks, "r1_total_unique_185", union_count == 185, union_count)

    add_check(
        checks,
        "batch_byte_identical_to_parent",
        sha256(PARENT_DIR / BATCH) == sha256(R1_DIR / BATCH),
        {
            "parent": sha256(PARENT_DIR / BATCH),
            "r1": sha256(R1_DIR / BATCH),
        },
    )

    # Check parent files against the hashes recorded in its own manifest.
    parent_hashes = parent_manifest.get("candidate_sha256", {})
    parent_batch_expected = parent_hashes.get("batch")
    parent_supp_expected = parent_hashes.get("supplement")

    add_check(
        checks,
        "parent_batch_matches_parent_manifest",
        bool(parent_batch_expected)
        and sha256(PARENT_DIR / BATCH) == parent_batch_expected,
        {
            "manifest_hash": parent_batch_expected,
            "actual_hash": sha256(PARENT_DIR / BATCH),
        },
    )
    add_check(
        checks,
        "parent_supplement_matches_parent_manifest",
        bool(parent_supp_expected)
        and sha256(PARENT_DIR / SUPPLEMENT) == parent_supp_expected,
        {
            "manifest_hash": parent_supp_expected,
            "actual_hash": sha256(PARENT_DIR / SUPPLEMENT),
        },
    )

    # Verify that only the two specified notes changed in supplement.
    unexpected_changes = []
    for pid, old_row in parent_supp_idx.items():
        new_row = r1_supp_idx.get(pid)
        if new_row is None:
            unexpected_changes.append(f"{pid}:missing")
            continue
        if pid in EXPECTED_NOTES:
            old_other = {k: v for k, v in old_row.items() if k != "notes"}
            new_other = {k: v for k, v in new_row.items() if k != "notes"}
            if old_other != new_other:
                unexpected_changes.append(f"{pid}:non_note_field_changed")
        elif old_row != new_row:
            unexpected_changes.append(f"{pid}:unexpected_change")

    add_check(
        checks,
        "only_two_supplement_notes_changed",
        not unexpected_changes,
        unexpected_changes or sorted(EXPECTED_NOTES),
    )

    # Exact note replacement and obsolete-text checks.
    for pid, expected_note in EXPECTED_NOTES.items():
        actual = r1_supp_idx.get(pid, {}).get("notes", "")
        add_check(
            checks,
            f"{pid}_note_exact_match",
            actual == expected_note,
            "Exact expected note comparison",
        )

    note_713 = r1_supp_idx["gsm8k_train_00713"].get("notes", "")
    note_830 = r1_supp_idx["gsm8k_train_00830"].get("notes", "")

    add_check(
        checks,
        "00713_old_contradiction_absent",
        "no ambiguity requiring further review" not in note_713.lower(),
        "Old contradictory phrase must be absent",
    )
    add_check(
        checks,
        "00830_old_contradiction_absent",
        "keep the existing capability labels" not in note_830.lower(),
        "Old contradictory phrase must be absent",
    )
    add_check(
        checks,
        "00830_subtraction_label_present",
        "subtraction" in note_830.lower(),
        "Note explicitly explains subtraction",
    )

    # Check ledger.
    ledger = read_csv(LEDGER)
    ledger_idx = index(ledger, "ledger")
    add_check(checks, "ledger_has_63_rows", len(ledger) == 63, len(ledger))

    ledger_mismatches = []
    for pid, expected_note in EXPECTED_NOTES.items():
        actual = ledger_idx.get(pid, {}).get("final_annotation_notes", "")
        if actual != expected_note:
            ledger_mismatches.append(pid)

    add_check(
        checks,
        "ledger_notes_match_r1",
        not ledger_mismatches,
        ledger_mismatches or sorted(EXPECTED_NOTES),
    )

    # Check revision manifest metadata and hashes.
    add_check(
        checks,
        "r1_manifest_version",
        r1_manifest.get("version") == "vNext-candidate-2026-11-16-r1",
        r1_manifest.get("version"),
    )
    add_check(
        checks,
        "r1_manifest_not_frozen",
        r1_manifest.get("freeze_status") == "NOT_FROZEN",
        r1_manifest.get("freeze_status"),
    )
    add_check(
        checks,
        "r1_manifest_validation_pass",
        r1_manifest.get("validation_status") == "PASS",
        r1_manifest.get("validation_status"),
    )

    r1_hashes = r1_manifest.get("candidate_sha256", {})
    add_check(
        checks,
        "r1_batch_matches_manifest",
        r1_hashes.get("batch") == sha256(R1_DIR / BATCH),
        {
            "manifest_hash": r1_hashes.get("batch"),
            "actual_hash": sha256(R1_DIR / BATCH),
        },
    )
    add_check(
        checks,
        "r1_supplement_matches_manifest",
        r1_hashes.get("supplement") == sha256(R1_DIR / SUPPLEMENT),
        {
            "manifest_hash": r1_hashes.get("supplement"),
            "actual_hash": sha256(R1_DIR / SUPPLEMENT),
        },
    )

    report_text = FINAL_REPORT.read_text(encoding="utf-8-sig")
    add_check(
        checks,
        "final_adjudication_report_has_r1_section",
        "Revision r1" in report_text,
        "Revision r1 section presence",
    )

    failed = [c for c in checks if not c["passed"]]
    status = "PASS" if not failed else "FAIL"

    result = {
        "status": status,
        "candidate": str(R1_DIR),
        "parent_candidate": str(PARENT_DIR),
        "freeze_status": "NOT_FROZEN",
        "counts": {
            "batch": len(r1_batch),
            "supplement": len(r1_supp),
            "total_unique": union_count,
            "ledger_rows": len(ledger),
        },
        "checks": checks,
        "failed_checks": failed,
        "important_limitation": (
            "This audit verifies parent batch and supplement against hashes "
            "stored in the parent manifest. It cannot independently prove "
            "the parent manifest file itself is unchanged because no pre-build "
            "hash of that manifest was recorded."
        ),
        "freeze_authorized": False,
    }

    OUT_JSON.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    md = [
        "# Gold vNext r1 Post-build Independent Audit",
        "",
        f"- Audit status: **{status}**",
        "- Freeze status: **NOT FROZEN**",
        "- Freeze authorized by this audit: **NO**",
        f"- Batch: **{len(r1_batch)}**",
        f"- Supplement: **{len(r1_supp)}**",
        f"- Unique total: **{union_count}**",
        f"- Ledger rows: **{len(ledger)}**",
        "",
        "## Checks",
        "",
    ]

    for c in checks:
        md.append(
            f"- **{'PASS' if c['passed'] else 'FAIL'}** "
            f"`{c['name']}` — {json.dumps(c['detail'], ensure_ascii=False)}"
        )

    md += [
        "",
        "## Limitation",
        "",
        result["important_limitation"],
        "",
        "The revision remains pending user approval. This audit does not freeze or release Gold.",
        "",
    ]

    OUT_MD.write_text("\n".join(md), encoding="utf-8")

    print(f"POST-BUILD AUDIT: {status}")
    print(f"Checks: {len(checks) - len(failed)}/{len(checks)} passed")
    print(f"Failed: {len(failed)}")
    print(f"JSON: {OUT_JSON}")
    print(f"Markdown: {OUT_MD}")
    print("Freeze status: NOT FROZEN")

    if failed:
        for item in failed:
            print("FAIL:", item["name"], item["detail"])
        raise SystemExit(1)

if __name__ == "__main__":
    main()
