from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path.cwd()

APPROVAL = ROOT / "data/gold_releases/vFinal_2026-11-16/gold_supplement_85_approved_review.csv"
GOLD_LABELS = ROOT / "data/gold_vfinal/supplement_annotations_vfinal.jsonl"
GOLD_MANIFEST = ROOT / "data/gold_vfinal/gold_vfinal_manifest.json"
POOL = ROOT / "trajectory/pool/pool_v1_verified.jsonl"
D_POOL = ROOT / "splits/d_pool_ids.txt"
D_DEV = ROOT / "splits/d_dev_ids.txt"
D_TEST = ROOT / "splits/d_test_ids.txt"

OUT = ROOT / "reports/p1p2_integration/source_review/approval_pool_validation_20261117.json"

EXPECTED_APPROVAL_SHA256 = (
    "d522a7dac7eb969bd9f8c4dd638d89db0710b66d65ab16bef3faad94694c2300"
)

CAPABILITIES = {
    "addition",
    "subtraction",
    "multiplication",
    "division",
    "percentage",
    "fraction",
    "ratio",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_ids(path: Path) -> set[str]:
    if not path.is_file():
        raise FileNotFoundError(path)
    values = [x.strip() for x in path.read_text(encoding="utf-8-sig").splitlines()]
    values = [x for x in values if x]
    if len(values) != len(set(values)):
        raise ValueError(f"Duplicate IDs in {path}")
    return set(values)


def read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        raise FileNotFoundError(path)
    rows = []
    with path.open("r", encoding="utf-8-sig") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: {exc}") from exc
    return rows


def main() -> None:
    required = [
        APPROVAL, GOLD_LABELS, GOLD_MANIFEST, POOL,
        D_POOL, D_DEV, D_TEST,
    ]
    missing = [str(p) for p in required if not p.is_file()]
    if missing:
        raise FileNotFoundError("Missing required inputs:\n" + "\n".join(missing))

    if OUT.exists():
        raise FileExistsError(f"Refusing to overwrite report: {OUT}")

    approval_hash = sha256(APPROVAL)
    if approval_hash != EXPECTED_APPROVAL_SHA256:
        raise ValueError(
            "Approval SHA256 mismatch: "
            f"expected={EXPECTED_APPROVAL_SHA256}, actual={approval_hash}"
        )

    with APPROVAL.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        approval_columns = reader.fieldnames or []
        approval_rows = list(reader)

    required_columns = {"problem_id", "human_approval"}
    missing_columns = required_columns - set(approval_columns)
    if missing_columns:
        raise ValueError(
            f"Approval CSV missing columns: {sorted(missing_columns)}; "
            f"actual={approval_columns}"
        )

    approval_ids_list = [r["problem_id"].strip() for r in approval_rows]
    if any(not x for x in approval_ids_list):
        raise ValueError("Approval CSV contains empty problem_id")
    if len(approval_ids_list) != len(set(approval_ids_list)):
        raise ValueError("Approval CSV contains duplicate problem_id")

    approval_ids = set(approval_ids_list)
    approval_status_counts = Counter(
        (r.get("human_approval") or "").strip()
        for r in approval_rows
    )
    unapproved = [
        r["problem_id"]
        for r in approval_rows
        if not (r.get("human_approval") or "").strip().upper().startswith("APPROVED")
    ]

    gold_rows = read_jsonl(GOLD_LABELS)
    gold_ids_list = [str(r.get("problem_id", "")).strip() for r in gold_rows]
    if any(not x for x in gold_ids_list):
        raise ValueError("Gold labels contain empty problem_id")
    if len(gold_ids_list) != len(set(gold_ids_list)):
        raise ValueError("Gold labels contain duplicate problem_id")
    gold_ids = set(gold_ids_list)

    if len(gold_rows) != 85 or len(gold_ids) != 85:
        raise ValueError(f"Expected 85 Gold rows/IDs; got {len(gold_rows)}/{len(gold_ids)}")
    if len(approval_rows) != 85 or approval_ids != gold_ids:
        raise ValueError(
            "Approval IDs do not exactly match Gold IDs: "
            f"approval={len(approval_ids)}, gold={len(gold_ids)}, "
            f"approval_only={len(approval_ids - gold_ids)}, "
            f"gold_only={len(gold_ids - approval_ids)}"
        )
    if unapproved:
        raise ValueError(f"Unapproved rows found: {unapproved[:10]}")

    d_pool = read_ids(D_POOL)
    d_dev = read_ids(D_DEV)
    d_test = read_ids(D_TEST)

    if d_pool & d_dev:
        raise ValueError("D_pool and D_dev overlap")
    if d_pool & d_test:
        raise ValueError("D_pool and D_test overlap")
    if d_dev & d_test:
        raise ValueError("D_dev and D_test overlap")

    pool_rows = read_jsonl(POOL)
    trajectory_ids = [str(r.get("trajectory_id", "")).strip() for r in pool_rows]
    problem_ids = [str(r.get("problem_id", "")).strip() for r in pool_rows]

    if any(not x for x in trajectory_ids):
        raise ValueError("Pool contains empty trajectory_id")
    if any(not x for x in problem_ids):
        raise ValueError("Pool contains empty problem_id")
    if len(trajectory_ids) != len(set(trajectory_ids)):
        raise ValueError("Pool contains duplicate trajectory_id")

    pool_problem_ids = set(problem_ids)
    if not pool_problem_ids.issubset(d_pool):
        raise ValueError(
            "Pool contains problem IDs outside D_pool: "
            f"{sorted(pool_problem_ids - d_pool)[:10]}"
        )
    if pool_problem_ids & d_dev or pool_problem_ids & d_test:
        raise ValueError("Pool overlaps D_dev or D_test")

    capability_counts = Counter()
    capability_type_counts = Counter()
    unknown_capabilities = Counter()
    empty_capability_rows = 0
    invalid_status_counts = Counter()
    extractor_counts = Counter()

    for row in pool_rows:
        caps = row.get("capabilities")
        capability_type_counts[type(caps).__name__] += 1

        if not isinstance(caps, list):
            raise ValueError(
                f"Non-list capabilities in trajectory {row.get('trajectory_id')}"
            )
        if not caps:
            empty_capability_rows += 1

        if len(caps) != len(set(caps)):
            raise ValueError(
                f"Duplicate capability tag in trajectory {row.get('trajectory_id')}"
            )

        for cap in caps:
            if cap not in CAPABILITIES:
                unknown_capabilities[str(cap)] += 1
            else:
                capability_counts[cap] += 1

        status = row.get("metadata", {}).get("verification_status")
        invalid_status_counts[str(status)] += 1
        if status != "valid":
            raise ValueError(
                f"Non-valid trajectory: {row.get('trajectory_id')} status={status}"
            )

        metadata = row.get("metadata", {})
        extractor = metadata.get("capability_extractor")
        extractor_counts[str(extractor)] += 1

    if unknown_capabilities:
        raise ValueError(
            f"Unknown capability tags: {dict(unknown_capabilities)}"
        )
    if empty_capability_rows:
        raise ValueError(
            f"Pool contains {empty_capability_rows} trajectories without capability tags"
        )

    report = {
        "schema_version": "p1p2.approval-pool-audit.v1",
        "read_only": True,
        "approval": {
            "path": str(APPROVAL),
            "sha256": approval_hash,
            "expected_sha256_match": True,
            "rows": len(approval_rows),
            "unique_problem_ids": len(approval_ids),
            "columns": approval_columns,
            "approval_status_counts": dict(approval_status_counts),
            "unapproved_rows": unapproved,
            "exact_id_match_with_gold": approval_ids == gold_ids,
        },
        "gold": {
            "path": str(GOLD_LABELS),
            "rows": len(gold_rows),
            "unique_problem_ids": len(gold_ids),
            "sha256": sha256(GOLD_LABELS),
        },
        "splits": {
            "d_pool_count": len(d_pool),
            "d_dev_count": len(d_dev),
            "d_test_count": len(d_test),
            "pool_problem_count": len(pool_problem_ids),
            "pool_problem_ids_subset_of_d_pool": pool_problem_ids.issubset(d_pool),
            "pool_d_dev_overlap": len(pool_problem_ids & d_dev),
            "pool_d_test_overlap": len(pool_problem_ids & d_test),
        },
        "pool": {
            "path": str(POOL),
            "sha256": sha256(POOL),
            "records": len(pool_rows),
            "unique_trajectory_ids": len(set(trajectory_ids)),
            "unique_problem_ids": len(pool_problem_ids),
            "capability_type_counts": dict(capability_type_counts),
            "capability_counts": dict(capability_counts),
            "empty_capability_rows": empty_capability_rows,
            "unknown_capabilities": dict(unknown_capabilities),
            "verification_status_counts": dict(invalid_status_counts),
            "capability_extractor_counts": dict(extractor_counts),
            "all_trajectories_valid": all(
                r.get("metadata", {}).get("verification_status") == "valid"
                for r in pool_rows
            ),
        },
        "protected_artifacts_modified": False,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("APPROVAL_POOL_AUDIT=PASS")
    print(f"APPROVAL_SHA256={approval_hash}")
    print(f"APPROVAL_ROWS={len(approval_rows)}")
    print(f"GOLD_ROWS={len(gold_rows)}")
    print(f"APPROVAL_GOLD_ID_MATCH={approval_ids == gold_ids}")
    print(f"POOL_RECORDS={len(pool_rows)}")
    print(f"POOL_UNIQUE_PROBLEMS={len(pool_problem_ids)}")
    print(f"POOL_CAPABILITY_COUNTS={dict(capability_counts)}")
    print(f"POOL_EXTRACTOR={dict(extractor_counts)}")
    print(f"REPORT={OUT}")


if __name__ == "__main__":
    main()
