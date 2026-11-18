import json
from pathlib import Path
from datetime import datetime, timezone

MANUAL = Path(__file__).resolve().parents[1]

AUDIT = (
    MANUAL / "reports" / "p1p2_integration"
    / "checkpoint_zip_metadata_audit"
    / "checkpoint_zip_metadata_audit_v2.json"
)

OUT_DIR = (
    MANUAL / "reports" / "p1p2_integration"
    / "provenance" / "B4_seed13"
)

def main():
    if not AUDIT.is_file():
        raise SystemExit(f"MISSING_AUDIT: {AUDIT}")

    audit = json.loads(AUDIT.read_text(encoding="utf-8"))

    if not audit.get("all_checkpoints_pass"):
        raise SystemExit("STOP: checkpoint audit is not PASS")

    config = audit["config_provenance"]
    checkpoints = audit["checkpoints"]

    if len(checkpoints) != 3:
        raise SystemExit("STOP: expected exactly 3 checkpoints")

    if any(c.get("status") != "PASS" for c in checkpoints):
        raise SystemExit("STOP: at least one checkpoint did not PASS")

    record = {
        "record_version": "1.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": {
            "method": "B4",
            "seed": 13,
            "rounds": ["S1", "S2", "S3"],
            "explicit_exclusion": [
                "S0 weights are not verified by this record",
                "No claim is made about other methods or seeds",
                "No claim is made that all P2 runs used this config"
            ]
        },
        "config_and_split": {
            "working_config_sha256": config["working_config_sha256"],
            "working_declared_split_sha256": config["working_declared_split_sha256"],
            "staging_config_sha256": config["staging_config_sha256"],
            "staging_declared_split_sha256": config["staging_declared_split_sha256"],
            "actual_split_sha256": config["actual_split_sha256"],
            "working_config_split_status": "MISMATCH",
            "staging_config_split_status": "MATCH"
        },
        "checkpoint_evidence": [],
        "split_creator": {
            "status": "UNRESOLVED",
            "expected_script_sha256": "052635fa4891476e9ed284f33d372ccaf477fcb708ce5b2d2bf2abd6ac93f539",
            "currently_found_script_sha256": "7f1c9bbe5d832fad4d62b2ca45f922dd207abe785ef1791ecc25ba7689db781e",
            "conclusion": "The currently located create_splits.py copies do not match the creator hash recorded in the split manifest. The split was not regenerated."
        },
        "overall_conclusion": (
            "VERIFIED: B4 seed 13 checkpoints S1-S3 reference the P1 staging "
            "experiment config by SHA-256 in their train_log.json files. "
            "This conclusion is limited to these three checkpoints."
        )
    }

    for c in checkpoints:
        tl = c["train_log"]
        record["checkpoint_evidence"].append({
            "checkpoint_zip": c["filename"],
            "zip_path": c["path"],
            "zip_sha256": c["sha256"],
            "seed": tl["seed"],
            "checkpoint_parent": tl["checkpoint_parent"],
            "config_sha256_in_train_log": tl["config_sha256"],
            "train_set_sha256": tl["train_set_sha256"],
            "pool_sha256": tl["pool_sha256"],
            "n_examples": tl["n_examples"],
            "adapter_weights_present": c["checks"]["adapter_weights_present"],
            "zip_integrity": c["zip_integrity"],
            "audit_status": c["status"]
        })

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    json_path = OUT_DIR / "b4_seed13_provenance_record.json"
    md_path = OUT_DIR / "b4_seed13_provenance_record.md"

    json_path.write_text(
        json.dumps(record, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    lines = [
        "# B4 Seed 13 — Provenance Record",
        "",
        f"- Created (UTC): {record['created_at_utc']}",
        "- Scope: B4, seed 13, S1-S3 only",
        "",
        "## Config and split",
        "",
        f"- Working config SHA-256: `{config['working_config_sha256']}`",
        f"- Working config declared split SHA-256: `{config['working_declared_split_sha256']}`",
        f"- P1 staging config SHA-256: `{config['staging_config_sha256']}`",
        f"- P1 staging config declared split SHA-256: `{config['staging_declared_split_sha256']}`",
        f"- Actual split SHA-256: `{config['actual_split_sha256']}`",
        "- Working config ↔ split: MISMATCH",
        "- P1 staging config ↔ split: MATCH",
        "",
        "## Checkpoint evidence",
        "",
        "| Checkpoint | ZIP SHA-256 | Train-set SHA-256 | Parent | Config SHA in train log | Status |",
        "|---|---|---|---|---|---|",
    ]

    for c in record["checkpoint_evidence"]:
        lines.append(
            f"| {c['checkpoint_zip']} | `{c['zip_sha256']}` "
            f"| `{c['train_set_sha256']}` | `{c['checkpoint_parent']}` "
            f"| `{c['config_sha256_in_train_log']}` | {c['audit_status']} |"
        )

    lines += [
        "",
        "## Split creator",
        "",
        "- Status: UNRESOLVED",
        "- Expected creator SHA-256: `052635fa4891476e9ed284f33d372ccaf477fcb708ce5b2d2bf2abd6ac93f539`",
        "- Located script SHA-256: `7f1c9bbe5d832fad4d62b2ca45f922dd207abe785ef1791ecc25ba7689db781e`",
        "- The split was not regenerated.",
        "",
        "## Conclusion and limitations",
        "",
        record["overall_conclusion"],
        "",
        "This record does not establish S0 weights, other methods, other seeds, or all P2 training runs.",
        "The working config remains unchanged.",
    ]

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("PROVENANCE_RECORD_STATUS: PASS")
    print("JSON:", json_path)
    print("MARKDOWN:", md_path)

if __name__ == "__main__":
    main()
