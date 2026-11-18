from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

POOL_PATH = ROOT / "trajectory/pool/pool_v1_verified.jsonl"
TOKENS_PATH = ROOT / "trajectory/pool/pool_v1_tokens.jsonl"
SUMMARY_PATH = ROOT / "trajectory/pool/pool_v1_tokens.summary.json"
D_POOL_PATH = ROOT / "splits/d_pool_ids.txt"

TAXONOMY = {
    "addition",
    "subtraction",
    "multiplication",
    "division",
    "percentage",
    "fraction",
    "ratio",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSONL: {path}:{line_number}: {exc}"
                ) from exc

            if not isinstance(row, dict):
                raise ValueError(
                    f"Expected JSON object: {path}:{line_number}"
                )
            rows.append(row)

    return rows


def write_exclusive(path: Path, content: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    descriptor = os.open(str(path), flags, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        try:
            path.unlink()
        except OSError:
            pass
        raise


def atomic_replace(path: Path, content: bytes) -> None:
    temp_path = path.with_name(path.name + ".sync_tmp")
    if temp_path.exists():
        raise FileExistsError(
            f"Temporary file already exists; refusing to overwrite: {temp_path}"
        )

    write_exclusive(temp_path, content)
    os.replace(temp_path, path)


def check(condition: bool, name: str, detail: str = "") -> bool:
    print(f"{name}={'PASS' if condition else 'FAIL'}")
    if detail:
        print(f"{name}_DETAIL={detail}")
    return condition


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit pool/token consistency and optionally synchronize token summary hash."
    )
    parser.add_argument(
        "--sync",
        action="store_true",
        help="Update only pool_sha256 in token summary after all structural checks pass.",
    )
    args = parser.parse_args()

    required = [POOL_PATH, TOKENS_PATH, SUMMARY_PATH, D_POOL_PATH]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        for path in missing:
            print(f"MISSING_FILE={path}")
        return 2

    pool_hash = sha256_file(POOL_PATH)
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    pool_rows = read_jsonl(POOL_PATH)
    token_rows = read_jsonl(TOKENS_PATH)

    pool_by_id = {}
    token_by_id = {}
    duplicate_pool_ids = []
    duplicate_token_ids = []
    invalid_pool_rows = []
    invalid_capability_rows = []
    invalid_token_rows = []
    token_problem_mismatches = []

    for index, row in enumerate(pool_rows, start=1):
        trajectory_id = row.get("trajectory_id")
        problem_id = row.get("problem_id")

        if not isinstance(trajectory_id, str) or not trajectory_id:
            invalid_pool_rows.append(f"row_{index}:missing_trajectory_id")
            continue

        if not isinstance(problem_id, str) or not problem_id:
            invalid_pool_rows.append(f"{trajectory_id}:missing_problem_id")

        if trajectory_id in pool_by_id:
            duplicate_pool_ids.append(trajectory_id)

        pool_by_id[trajectory_id] = row

        metadata = row.get("metadata")
        if not isinstance(metadata, dict) or metadata.get("verification_status") != "valid":
            invalid_pool_rows.append(f"{trajectory_id}:verification_status")

        capabilities = row.get("capabilities")
        if not isinstance(capabilities, list) or not capabilities:
            invalid_capability_rows.append(f"{trajectory_id}:empty_or_invalid")
        else:
            unknown = sorted(
                capability
                for capability in capabilities
                if not isinstance(capability, str) or capability not in TAXONOMY
            )
            if unknown:
                invalid_capability_rows.append(
                    f"{trajectory_id}:unknown={unknown}"
                )

    for index, row in enumerate(token_rows, start=1):
        trajectory_id = row.get("trajectory_id")
        problem_id = row.get("problem_id")
        response_tokens = row.get("response_tokens")

        if not isinstance(trajectory_id, str) or not trajectory_id:
            invalid_token_rows.append(f"row_{index}:missing_trajectory_id")
            continue

        if trajectory_id in token_by_id:
            duplicate_token_ids.append(trajectory_id)

        token_by_id[trajectory_id] = row

        if not isinstance(response_tokens, int) or isinstance(response_tokens, bool) or response_tokens <= 0:
            invalid_token_rows.append(f"{trajectory_id}:invalid_response_tokens")

        pool_row = pool_by_id.get(trajectory_id)
        if pool_row is not None and pool_row.get("problem_id") != problem_id:
            token_problem_mismatches.append(trajectory_id)

    pool_ids = set(pool_by_id)
    token_ids = set(token_by_id)
    missing_token_ids = sorted(pool_ids - token_ids)
    extra_token_ids = sorted(token_ids - pool_ids)

    token_sum = sum(
        row["response_tokens"]
        for row in token_rows
        if isinstance(row.get("response_tokens"), int)
        and not isinstance(row.get("response_tokens"), bool)
        and row["response_tokens"] > 0
    )

    d_pool_ids = {
        line.strip()
        for line in D_POOL_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    pool_problem_ids = {
        row.get("problem_id")
        for row in pool_rows
        if isinstance(row.get("problem_id"), str) and row.get("problem_id")
    }
    outside_d_pool = sorted(pool_problem_ids - d_pool_ids)

    print("=== INPUT HASHES ===")
    print(f"POOL_SHA256={pool_hash}")
    print(f"TOKEN_TABLE_SHA256={sha256_file(TOKENS_PATH)}")
    print(f"SUMMARY_SHA256_BEFORE={sha256_file(SUMMARY_PATH)}")
    print(f"SUMMARY_POOL_SHA256_BEFORE={summary.get('pool_sha256')}")

    print("\n=== ROW COUNTS ===")
    print(f"POOL_ROWS={len(pool_rows)}")
    print(f"TOKEN_ROWS={len(token_rows)}")
    print(f"POOL_UNIQUE_TRAJECTORY_IDS={len(pool_ids)}")
    print(f"TOKEN_UNIQUE_TRAJECTORY_IDS={len(token_ids)}")
    print(f"TOKEN_RESPONSE_SUM={token_sum}")
    print(f"SUMMARY_N_TRAJECTORIES={summary.get('n_trajectories')}")
    print(f"SUMMARY_RESPONSE_TOKENS_SUM={summary.get('response_tokens_sum')}")

    checks = {
        "POOL_NONEMPTY": len(pool_rows) > 0,
        "TOKEN_TABLE_NONEMPTY": len(token_rows) > 0,
        "NO_DUPLICATE_POOL_IDS": not duplicate_pool_ids,
        "NO_DUPLICATE_TOKEN_IDS": not duplicate_token_ids,
        "POOL_TOKEN_ID_SETS_EQUAL": pool_ids == token_ids,
        "NO_TOKEN_PROBLEM_ID_MISMATCH": not token_problem_mismatches,
        "NO_INVALID_POOL_ROWS": not invalid_pool_rows,
        "NO_INVALID_CAPABILITY_ROWS": not invalid_capability_rows,
        "NO_INVALID_TOKEN_ROWS": not invalid_token_rows,
        "SUMMARY_POOL_ROW_COUNT_MATCH": len(pool_rows) == summary.get("n_trajectories"),
        "SUMMARY_TOKEN_ROW_COUNT_MATCH": len(token_rows) == summary.get("n_trajectories"),
        "SUMMARY_TOKEN_SUM_MATCH": token_sum == summary.get("response_tokens_sum"),
        "ALL_POOL_PROBLEMS_IN_D_POOL": not outside_d_pool,
    }

    print("\n=== STRUCTURAL CHECKS ===")
    all_passed = True
    for name, passed in checks.items():
        all_passed = check(passed, name) and all_passed

    print(f"D_POOL_UNIQUE_IDS={len(d_pool_ids)}")
    print(f"POOL_UNIQUE_PROBLEM_IDS={len(pool_problem_ids)}")
    print(f"POOL_PROBLEMS_OUTSIDE_D_POOL={len(outside_d_pool)}")

    if duplicate_pool_ids:
        print(f"DUPLICATE_POOL_ID_EXAMPLES={duplicate_pool_ids[:10]}")
    if duplicate_token_ids:
        print(f"DUPLICATE_TOKEN_ID_EXAMPLES={duplicate_token_ids[:10]}")
    if missing_token_ids:
        print(f"MISSING_TOKEN_ID_EXAMPLES={missing_token_ids[:10]}")
    if extra_token_ids:
        print(f"EXTRA_TOKEN_ID_EXAMPLES={extra_token_ids[:10]}")
    if token_problem_mismatches:
        print(f"TOKEN_PROBLEM_MISMATCH_EXAMPLES={token_problem_mismatches[:10]}")
    if invalid_pool_rows:
        print(f"INVALID_POOL_ROW_EXAMPLES={invalid_pool_rows[:10]}")
    if invalid_capability_rows:
        print(f"INVALID_CAPABILITY_EXAMPLES={invalid_capability_rows[:10]}")
    if invalid_token_rows:
        print(f"INVALID_TOKEN_ROW_EXAMPLES={invalid_token_rows[:10]}")
    if outside_d_pool:
        print(f"OUTSIDE_D_POOL_EXAMPLES={outside_d_pool[:20]}")

    if not all_passed:
        print("\nSUMMARY_SYNC=BLOCKED")
        print("REASON=Structural consistency checks failed; summary was not modified.")
        return 1

    if not args.sync:
        print("\nSTRUCTURAL_AUDIT=PASS")
        print("SUMMARY_SYNC=NOT_REQUESTED")
        return 0

    old_summary_bytes = SUMMARY_PATH.read_bytes()
    backup_path = SUMMARY_PATH.with_name(
        SUMMARY_PATH.stem
        + ".pre_sync_"
        + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + SUMMARY_PATH.suffix
    )

    write_exclusive(backup_path, old_summary_bytes)

    updated_summary = dict(summary)
    updated_summary["pool_sha256"] = pool_hash

    updated_bytes = (
        json.dumps(
            updated_summary,
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")

    atomic_replace(SUMMARY_PATH, updated_bytes)

    summary_after = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    final_hash = sha256_file(POOL_PATH)

    print("\n=== SUMMARY SYNCHRONIZATION ===")
    print(f"SUMMARY_BACKUP={backup_path}")
    print(f"SUMMARY_POOL_SHA256_AFTER={summary_after.get('pool_sha256')}")
    print(f"POOL_SHA256_AFTER={final_hash}")
    print(f"SUMMARY_SHA256_AFTER={sha256_file(SUMMARY_PATH)}")

    if summary_after.get("pool_sha256") != final_hash:
        print("SUMMARY_SYNC=FAIL")
        return 3

    print("SUMMARY_SYNC=PASS")
    print("UPDATED_FIELDS=pool_sha256")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"AUDIT_FATAL={type(exc).__name__}: {exc}", file=sys.stderr)
        raise
