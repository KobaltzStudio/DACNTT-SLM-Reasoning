from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[4]
MANUAL = REPO / "experiments" / "week2September" / "manual"
DATA = MANUAL / "data"
REPORT_DIR = MANUAL / "reports" / "gold" / "review_2026-11-16"

GOLD_VFINAL = DATA / "gold_vfinal"
PARENT_DIR = DATA / "gold_vnext_candidate_2026-11-16"
R1_DIR = DATA / "gold_vnext_candidate_2026-11-16_r1"
FROZEN_DIR = DATA / "gold_vnext_frozen_2026-11-16_r1"

BASELINE_PATH = REPORT_DIR / "gold_r1_freeze_baseline_sha256.json"
APPROVAL_PATH = REPORT_DIR / "gold_r1_freeze_approval_2026-11-16.json"
AUDIT_PATH = REPORT_DIR / "gold_r1_freeze_audit_2026-11-16.json"

GOLD_BATCH = GOLD_VFINAL / "batch_100_annotations_vfinal.jsonl"
GOLD_SUPPLEMENT = GOLD_VFINAL / "supplement_annotations_vfinal.jsonl"
GOLD_MANIFEST = GOLD_VFINAL / "gold_vfinal_manifest.json"

RAW_TRAIN = DATA / "raw" / "gsm8k_train.jsonl"
RAW_SUPPLEMENT = DATA / "raw" / "supplement_selected.jsonl"

PARENT_BATCH = PARENT_DIR / "batch_100_annotations_vnext.jsonl"
PARENT_SUPPLEMENT = PARENT_DIR / "supplement_annotations_vnext.jsonl"
PARENT_MANIFEST = PARENT_DIR / "gold_vnext_manifest.json"

R1_BATCH = R1_DIR / "batch_100_annotations_vnext.jsonl"
R1_SUPPLEMENT = R1_DIR / "supplement_annotations_vnext.jsonl"
R1_MANIFEST = R1_DIR / "gold_vnext_manifest.json"

FROZEN_BATCH_NAME = "batch_100_annotations_vnext.jsonl"
FROZEN_SUPPLEMENT_NAME = "supplement_annotations_vnext.jsonl"
FROZEN_MANIFEST_NAME = "gold_vnext_manifest.json"

EXPECTED_VERSION = "vNext-candidate-2026-11-16-r1"
EXPECTED_APPROVAL_STATEMENT = (
    "I_APPROVE_FREEZE_GOLD_VNEXT_CANDIDATE_2026-11-16_r1"
)

PROTECTED_PATHS = {
    "gold_vfinal_batch": GOLD_BATCH,
    "gold_vfinal_supplement": GOLD_SUPPLEMENT,
    "gold_vfinal_manifest": GOLD_MANIFEST,
    "raw_train": RAW_TRAIN,
    "raw_supplement": RAW_SUPPLEMENT,
    "parent_batch": PARENT_BATCH,
    "parent_supplement": PARENT_SUPPLEMENT,
    "parent_manifest": PARENT_MANIFEST,
    "r1_batch": R1_BATCH,
    "r1_supplement": R1_SUPPLEMENT,
    "r1_manifest": R1_MANIFEST,
}


class FreezeError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> dict:
    if not path.is_file():
        raise FreezeError(f"Required JSON file is missing: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        raise FreezeError(f"Cannot parse JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise FreezeError(f"Expected a JSON object: {path}")
    return value


def load_jsonl(path: Path, expected_count: int) -> list[dict]:
    if not path.is_file():
        raise FreezeError(f"Required JSONL file is missing: {path}")

    records = []
    with path.open("r", encoding="utf-8-sig") as f:
        for line_number, line in enumerate(f, start=1):
            if not line.strip():
                raise FreezeError(
                    f"Blank JSONL line at {path}:{line_number}"
                )
            try:
                record = json.loads(line)
            except Exception as exc:
                raise FreezeError(
                    f"Invalid JSON at {path}:{line_number}: {exc}"
                ) from exc
            if not isinstance(record, dict):
                raise FreezeError(
                    f"JSONL record is not an object at {path}:{line_number}"
                )
            records.append(record)

    if len(records) != expected_count:
        raise FreezeError(
            f"Wrong record count for {path}: "
            f"expected {expected_count}, got {len(records)}"
        )
    return records


def check_hash(value: str, label: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(c not in "0123456789abcdef" for c in value.lower())
    ):
        raise FreezeError(f"Invalid SHA256 value for {label}: {value!r}")


def verify_baseline() -> dict:
    baseline = load_json(BASELINE_PATH)

    if baseline.get("baseline_verification_status") != "PASS":
        raise FreezeError(
            "Baseline verification status is not PASS."
        )

    recorded = baseline.get("protected_and_candidate_sha256")
    if not isinstance(recorded, dict):
        raise FreezeError(
            "Baseline has no protected_and_candidate_sha256 object."
        )

    results = {}
    for key, path in PROTECTED_PATHS.items():
        if not path.is_file():
            raise FreezeError(f"Protected file is missing: {path}")

        expected = recorded.get(key)
        check_hash(expected, f"baseline.{key}")

        actual = sha256(path)
        if actual != expected.lower():
            raise FreezeError(
                f"Baseline mismatch for {key}: "
                f"expected {expected}, actual {actual}"
            )

        results[key] = {
            "path": str(path.relative_to(REPO)),
            "sha256": actual,
            "status": "PASS",
        }

    return results


def verify_candidate() -> dict:
    manifest = load_json(R1_MANIFEST)

    if manifest.get("version") != EXPECTED_VERSION:
        raise FreezeError(
            f"Unexpected r1 version: {manifest.get('version')!r}"
        )
    if manifest.get("candidate_status") != "VALIDATED_PENDING_USER_APPROVAL":
        raise FreezeError(
            "Candidate status is not VALIDATED_PENDING_USER_APPROVAL."
        )
    if manifest.get("freeze_status") != "NOT_FROZEN":
        raise FreezeError("Candidate is not in NOT_FROZEN state.")
    if manifest.get("validation_status") != "PASS":
        raise FreezeError("Candidate validation_status is not PASS.")
    if manifest.get("approval_required_before_freeze") is not True:
        raise FreezeError(
            "Manifest does not require approval before freeze."
        )

    for field in (
        "ground_truth_modified",
        "difficulty_modified",
        "gold_vfinal_modified",
        "human_confirmed_records_modified",
    ):
        if manifest.get(field) is not False:
            raise FreezeError(
                f"Safety invariant failed: {field} is not false."
            )

    if manifest.get("records") != 185:
        raise FreezeError("Manifest total records must equal 185.")
    if manifest.get("batch_100_records") != 100:
        raise FreezeError("Manifest batch count must equal 100.")
    if manifest.get("supplement_records") != 85:
        raise FreezeError("Manifest supplement count must equal 85.")

    candidate_hashes = manifest.get("candidate_sha256")
    if not isinstance(candidate_hashes, dict):
        raise FreezeError("Missing candidate_sha256 in r1 manifest.")

    actual_batch_hash = sha256(R1_BATCH)
    actual_supplement_hash = sha256(R1_SUPPLEMENT)
    actual_manifest_hash = sha256(R1_MANIFEST)

    check_hash(candidate_hashes.get("batch"), "r1 candidate batch")
    check_hash(
        candidate_hashes.get("supplement"),
        "r1 candidate supplement",
    )

    if candidate_hashes["batch"].lower() != actual_batch_hash:
        raise FreezeError("r1 batch hash does not match its manifest.")
    if candidate_hashes["supplement"].lower() != actual_supplement_hash:
        raise FreezeError("r1 supplement hash does not match its manifest.")

    if not PARENT_BATCH.is_file() or not PARENT_SUPPLEMENT.is_file():
        raise FreezeError("Parent candidate files are missing.")

    if PARENT_BATCH.read_bytes() != R1_BATCH.read_bytes():
        raise FreezeError("r1 batch is not byte-identical to parent batch.")

    batch_records = load_jsonl(R1_BATCH, 100)
    supplement_records = load_jsonl(R1_SUPPLEMENT, 85)

    # Confirm that all records are JSON objects and that total count is 185.
    if len(batch_records) + len(supplement_records) != 185:
        raise FreezeError("Combined candidate record count is not 185.")

    source_hashes = manifest.get("source_sha256")
    if not isinstance(source_hashes, dict):
        raise FreezeError("Missing source_sha256 in r1 manifest.")

    source_mapping = {
        "batch": GOLD_BATCH,
        "supplement": GOLD_SUPPLEMENT,
        "gold_manifest": GOLD_MANIFEST,
        "raw_train": RAW_TRAIN,
        "supplement_raw": RAW_SUPPLEMENT,
    }
    for source_key, source_path in source_mapping.items():
        entry = source_hashes.get(source_key)
        if not isinstance(entry, dict):
            raise FreezeError(
                f"Missing source_sha256.{source_key} in r1 manifest."
            )
        recorded_hash = entry.get("actual_sha256")
        check_hash(recorded_hash, f"source_sha256.{source_key}")
        if sha256(source_path) != recorded_hash.lower():
            raise FreezeError(
                f"r1 source hash mismatch for {source_key}."
            )

    return {
        "version": manifest["version"],
        "batch_count": len(batch_records),
        "supplement_count": len(supplement_records),
        "total_count": 185,
        "batch_sha256": actual_batch_hash,
        "supplement_sha256": actual_supplement_hash,
        "manifest_sha256": actual_manifest_hash,
        "parent_batch_byte_identical": True,
        "validation_status": "PASS",
    }


def verify_approval(candidate: dict) -> dict:
    approval = load_json(APPROVAL_PATH)

    if approval.get("approval_status") != "APPROVED":
        raise FreezeError("Approval status must be APPROVED.")

    if approval.get("approval_statement") != EXPECTED_APPROVAL_STATEMENT:
        raise FreezeError("Approval statement does not match exactly.")

    approved_by = approval.get("approved_by")
    if (
        not isinstance(approved_by, str)
        or not approved_by.strip()
        or approved_by.strip().upper() in {
            "USER",
            "YOUR NAME",
            "TBD",
            "TODO",
            "PLACEHOLDER",
        }
    ):
        raise FreezeError(
            "approved_by must contain the actual approver's identity."
        )

    if approval.get("candidate_version") != EXPECTED_VERSION:
        raise FreezeError("Approval candidate_version does not match r1.")

    approved_hashes = approval.get("candidate_sha256")
    expected_hashes = {
        "batch": candidate["batch_sha256"],
        "supplement": candidate["supplement_sha256"],
        "manifest": candidate["manifest_sha256"],
    }

    if not isinstance(approved_hashes, dict):
        raise FreezeError("Approval is missing candidate_sha256.")

    for key, expected in expected_hashes.items():
        actual = approved_hashes.get(key)
        check_hash(actual, f"approval.candidate_sha256.{key}")
        if actual.lower() != expected:
            raise FreezeError(
                f"Approval hash mismatch for {key}: "
                f"approval={actual}, actual={expected}"
            )

    scope = approval.get("scope")
    if not isinstance(scope, dict):
        raise FreezeError("Approval is missing scope.")
    if scope.get("freeze_candidate_only") is not True:
        raise FreezeError("Approval scope must freeze candidate only.")
    if scope.get("modify_gold_vfinal") is not False:
        raise FreezeError("Approval must prohibit modifying Gold vFinal.")
    if scope.get("modify_raw_data") is not False:
        raise FreezeError("Approval must prohibit modifying raw data.")
    if scope.get("modify_parent_candidate") is not False:
        raise FreezeError(
            "Approval must prohibit modifying parent candidate."
        )
    if scope.get("modify_r1_candidate") is not False:
        raise FreezeError("Approval must prohibit modifying r1 candidate.")

    return {
        "approval_status": "APPROVED",
        "approved_by": approved_by.strip(),
        "approved_date": approval.get("approved_date"),
        "approval_statement": EXPECTED_APPROVAL_STATEMENT,
    }


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def audit_frozen(expected_candidate: dict, baseline_results: dict) -> dict:
    if not FROZEN_DIR.is_dir():
        raise FreezeError(f"Frozen directory does not exist: {FROZEN_DIR}")

    frozen_batch = FROZEN_DIR / FROZEN_BATCH_NAME
    frozen_supplement = FROZEN_DIR / FROZEN_SUPPLEMENT_NAME
    frozen_manifest_path = FROZEN_DIR / FROZEN_MANIFEST_NAME

    frozen_manifest = load_json(frozen_manifest_path)

    if frozen_manifest.get("version") != EXPECTED_VERSION:
        raise FreezeError("Frozen manifest version mismatch.")
    if frozen_manifest.get("candidate_status") != "FROZEN_RELEASE":
        raise FreezeError("Frozen candidate_status is incorrect.")
    if frozen_manifest.get("freeze_status") != "FROZEN":
        raise FreezeError("Frozen freeze_status is incorrect.")
    if frozen_manifest.get("release_status") != "FROZEN":
        raise FreezeError("Frozen release_status is incorrect.")

    if frozen_batch.read_bytes() != R1_BATCH.read_bytes():
        raise FreezeError("Frozen batch is not byte-identical to r1.")
    if frozen_supplement.read_bytes() != R1_SUPPLEMENT.read_bytes():
        raise FreezeError("Frozen supplement is not byte-identical to r1.")

    frozen_batch_hash = sha256(frozen_batch)
    frozen_supplement_hash = sha256(frozen_supplement)

    if frozen_batch_hash != expected_candidate["batch_sha256"]:
        raise FreezeError("Frozen batch hash does not match r1.")
    if frozen_supplement_hash != expected_candidate["supplement_sha256"]:
        raise FreezeError("Frozen supplement hash does not match r1.")

    # Re-check all protected files after release creation.
    post_baseline = verify_baseline()

    return {
        "frozen_directory": str(FROZEN_DIR.relative_to(REPO)),
        "freeze_status": "FROZEN",
        "batch_sha256": frozen_batch_hash,
        "supplement_sha256": frozen_supplement_hash,
        "batch_byte_identical_to_r1": True,
        "supplement_byte_identical_to_r1": True,
        "protected_files_unchanged": True,
        "protected_file_count": len(post_baseline),
        "status": "PASS",
    }


def create_frozen_release(
    candidate: dict,
    baseline_results: dict,
    approval: dict,
) -> dict:
    if FROZEN_DIR.exists():
        raise FreezeError(
            f"Frozen destination already exists; refusing to overwrite: "
            f"{FROZEN_DIR}"
        )

    r1_manifest = load_json(R1_MANIFEST)
    timestamp = datetime.now(timezone.utc).isoformat()

    frozen_manifest = dict(r1_manifest)
    frozen_manifest["candidate_status"] = "FROZEN_RELEASE"
    frozen_manifest["freeze_status"] = "FROZEN"
    frozen_manifest["release_status"] = "FROZEN"
    frozen_manifest["approval_required_before_freeze"] = False
    frozen_manifest["freeze_metadata"] = {
        "frozen_at_utc": timestamp,
        "source_candidate_version": EXPECTED_VERSION,
        "source_candidate_directory": str(R1_DIR.relative_to(REPO)),
        "approval": approval,
        "source_candidate_sha256": {
            "batch": candidate["batch_sha256"],
            "supplement": candidate["supplement_sha256"],
            "manifest": candidate["manifest_sha256"],
        },
        "baseline_verification_status": "PASS",
        "baseline_protected_file_count": len(baseline_results),
        "freeze_scope": (
            "Create a separate frozen release from r1. "
            "Do not modify Gold vFinal, raw data, parent candidate, "
            "or r1 candidate."
        ),
    }

    FROZEN_DIR.parent.mkdir(parents=True, exist_ok=True)
    temp_dir = Path(
        tempfile.mkdtemp(
            prefix=".gold_vnext_frozen_r1_staging_",
            dir=str(FROZEN_DIR.parent),
        )
    )

    try:
        shutil.copy2(R1_BATCH, temp_dir / FROZEN_BATCH_NAME)
        shutil.copy2(R1_SUPPLEMENT, temp_dir / FROZEN_SUPPLEMENT_NAME)
        write_json(temp_dir / FROZEN_MANIFEST_NAME, frozen_manifest)

        # Verify staged files before publishing the directory.
        if (temp_dir / FROZEN_BATCH_NAME).read_bytes() != R1_BATCH.read_bytes():
            raise FreezeError("Staged batch copy verification failed.")
        if (
            (temp_dir / FROZEN_SUPPLEMENT_NAME).read_bytes()
            != R1_SUPPLEMENT.read_bytes()
        ):
            raise FreezeError("Staged supplement copy verification failed.")

        load_json(temp_dir / FROZEN_MANIFEST_NAME)

        # Atomic directory rename on the same filesystem.
        os.rename(temp_dir, FROZEN_DIR)
    except Exception:
        # Preserve the staging directory for forensic inspection.
        raise

    return audit_frozen(candidate, baseline_results)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit or freeze Gold vNext candidate r1."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--audit-only",
        action="store_true",
        help="Validate baseline and r1 without creating a release.",
    )
    mode.add_argument(
        "--freeze",
        action="store_true",
        help="Create frozen release after validating explicit approval.",
    )
    args = parser.parse_args()

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    report = {
        "script": Path(__file__).name,
        "candidate_version": EXPECTED_VERSION,
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "FREEZE" if args.freeze else "AUDIT_ONLY",
        "checks": {},
        "status": "FAIL",
    }

    try:
        baseline_results = verify_baseline()
        report["checks"]["baseline_11_files"] = {
            "status": "PASS",
            "count": len(baseline_results),
            "files": baseline_results,
        }

        candidate = verify_candidate()
        report["checks"]["r1_candidate"] = candidate

        if args.audit_only:
            report["checks"]["approval"] = {
                "status": "NOT_CHECKED",
                "reason": "Audit-only mode does not require approval.",
            }

            if FROZEN_DIR.exists():
                report["checks"]["frozen_release"] = audit_frozen(
                    candidate, baseline_results
                )
            else:
                report["checks"]["frozen_release"] = {
                    "status": "NOT_CREATED",
                    "expected_path": str(FROZEN_DIR.relative_to(REPO)),
                }

            report["status"] = "PASS"

        elif args.freeze:
            approval = verify_approval(candidate)
            report["checks"]["approval"] = approval

            frozen_result = create_frozen_release(
                candidate, baseline_results, approval
            )
            report["checks"]["frozen_release"] = frozen_result
            report["status"] = "PASS"

    except Exception as exc:
        report["error"] = str(exc)
        report["status"] = "FAIL"

    report["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
    write_json(AUDIT_PATH, report)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\nAUDIT_REPORT: {AUDIT_PATH}")
    print(f"FINAL_STATUS: {report['status']}")

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
