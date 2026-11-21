#!/usr/bin/env python3
"""Read-only audit of verified trajectory pool against its token table."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT_DEFAULT = Path(r"C:\Users\PC - NGHI\Desktop\Pipeline\P2\experiments\week2September\manual")
POOL_REL = Path("trajectory/pool/pool_v1_verified.jsonl")
TOKENS_REL = Path("trajectory/pool/pool_v1_tokens.jsonl")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_jsonl(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as f:
        for line_no, raw in enumerate(f, 1):
            if not raw.strip():
                continue
            try:
                obj = json.loads(raw)
                if not isinstance(obj, dict):
                    raise ValueError("JSONL record is not an object")
                records.append(obj)
            except Exception as exc:
                errors.append({"line": line_no, "error": str(exc)})
    return records, errors


def first_value(obj: dict[str, Any], paths: list[tuple[str, ...]]) -> Any:
    for path in paths:
        cur: Any = obj
        found = True
        for key in path:
            if not isinstance(cur, dict) or key not in cur:
                found = False
                break
            cur = cur[key]
        if found and cur is not None:
            return cur
    return None


def normalize_id(value: Any) -> str | None:
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def index_records(records: list[dict[str, Any]], kind: str) -> tuple[dict[str, dict[str, Any]], list[str], list[dict[str, Any]]]:
    paths = [
        ("trajectory_id",),
        ("id",),
        ("trajectory", "trajectory_id"),
    ]
    indexed: dict[str, dict[str, Any]] = {}
    missing: list[str] = []
    duplicates: list[dict[str, Any]] = []
    for row_no, row in enumerate(records, 1):
        tid = normalize_id(first_value(row, paths))
        if tid is None:
            missing.append(str(row_no))
            continue
        if tid in indexed:
            duplicates.append({"trajectory_id": tid, "record_number": row_no})
            continue
        indexed[tid] = row
    return indexed, missing, duplicates


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit P2 verified pool/token-table consistency.")
    parser.add_argument("--root", type=Path, default=ROOT_DEFAULT)
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()

    root = args.root.resolve()
    pool_path = root / POOL_REL
    token_path = root / TOKENS_REL
    if not pool_path.is_file():
        print(f"MISSING_INPUT={pool_path}", file=sys.stderr)
        return 2
    if not token_path.is_file():
        print(f"MISSING_INPUT={token_path}", file=sys.stderr)
        return 2

    pool, pool_errors = read_jsonl(pool_path)
    tokens, token_errors = read_jsonl(token_path)
    pool_idx, pool_missing_ids, pool_duplicates = index_records(pool, "pool")
    token_idx, token_missing_ids, token_duplicates = index_records(tokens, "tokens")

    pool_ids = set(pool_idx)
    token_ids = set(token_idx)
    missing_tokens = sorted(pool_ids - token_ids)
    extra_tokens = sorted(token_ids - pool_ids)

    problem_mismatches: list[dict[str, str]] = []
    invalid_token_counts: list[dict[str, Any]] = []
    missing_problem_ids: list[dict[str, str]] = []
    token_values: list[int] = []

    problem_paths = [("problem_id",), ("problem", "problem_id")]
    for tid in sorted(pool_ids & token_ids):
        p_row = pool_idx[tid]
        t_row = token_idx[tid]
        p_problem = normalize_id(first_value(p_row, problem_paths))
        t_problem = normalize_id(first_value(t_row, problem_paths))
        if p_problem is None or t_problem is None:
            missing_problem_ids.append({
                "trajectory_id": tid,
                "pool_problem_id": str(p_problem),
                "token_problem_id": str(t_problem),
            })
        elif p_problem != t_problem:
            problem_mismatches.append({
                "trajectory_id": tid,
                "pool_problem_id": p_problem,
                "token_problem_id": t_problem,
            })

        raw_count = first_value(t_row, [("response_tokens",), ("tokens", "response_tokens")])
        valid = isinstance(raw_count, int) and not isinstance(raw_count, bool) and raw_count > 0
        if not valid:
            invalid_token_counts.append({"trajectory_id": tid, "value": raw_count})
        else:
            token_values.append(raw_count)

    pool_hash = sha256_file(pool_path)
    token_hash = sha256_file(token_path)
    output_dir = args.output_dir
    if output_dir is None:
        output_dir = root / "reports" / "p1p2_integration" / "g6_token_audit" / "run_20261117_1800"
    output_dir = output_dir.resolve()
    if output_dir.exists():
        print(f"OUTPUT_DIR_ALREADY_EXISTS={output_dir}", file=sys.stderr)
        return 3
    output_dir.mkdir(parents=True, exist_ok=False)

    checks = {
        "pool_jsonl_parse": not pool_errors,
        "token_jsonl_parse": not token_errors,
        "pool_trajectory_id_present": not pool_missing_ids,
        "token_trajectory_id_present": not token_missing_ids,
        "pool_trajectory_id_unique": not pool_duplicates,
        "token_trajectory_id_unique": not token_duplicates,
        "token_table_covers_pool": not missing_tokens,
        "token_table_has_no_extra_ids": not extra_tokens,
        "problem_ids_match": not problem_mismatches and not missing_problem_ids,
        "response_tokens_positive_integer": not invalid_token_counts,
    }
    passed = all(checks.values())
    report = {
        "schema_version": "p1p2.g6-token-audit.v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "inputs": {
            "verified_pool": {"path": str(pool_path), "sha256": pool_hash, "size_bytes": pool_path.stat().st_size},
            "token_table": {"path": str(token_path), "sha256": token_hash, "size_bytes": token_path.stat().st_size},
        },
        "counts": {
            "pool_records": len(pool),
            "pool_unique_trajectory_ids": len(pool_idx),
            "token_records": len(tokens),
            "token_unique_trajectory_ids": len(token_idx),
            "common_trajectory_ids": len(pool_ids & token_ids),
            "missing_token_records": len(missing_tokens),
            "extra_token_records": len(extra_tokens),
            "problem_id_mismatches": len(problem_mismatches),
            "missing_problem_ids": len(missing_problem_ids),
            "invalid_response_tokens": len(invalid_token_counts),
            "pool_parse_errors": len(pool_errors),
            "token_parse_errors": len(token_errors),
            "pool_duplicate_ids": len(pool_duplicates),
            "token_duplicate_ids": len(token_duplicates),
            "token_count_min": min(token_values) if token_values else None,
            "token_count_max": max(token_values) if token_values else None,
            "token_count_sum": sum(token_values) if token_values else None,
        },
        "checks": checks,
        "details": {
            "pool_parse_errors_sample": pool_errors[:20],
            "token_parse_errors_sample": token_errors[:20],
            "pool_missing_id_record_numbers": pool_missing_ids[:50],
            "token_missing_id_record_numbers": token_missing_ids[:50],
            "pool_duplicate_ids_sample": pool_duplicates[:50],
            "token_duplicate_ids_sample": token_duplicates[:50],
            "missing_tokens_sample": missing_tokens[:100],
            "extra_tokens_sample": extra_tokens[:100],
            "problem_mismatches_sample": problem_mismatches[:100],
            "missing_problem_ids_sample": missing_problem_ids[:100],
            "invalid_token_counts_sample": invalid_token_counts[:100],
        },
        "status": "PASS" if passed else "FAIL",
    }

    json_path = output_dir / "g6_token_audit.json"
    md_path = output_dir / "g6_token_audit.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# G6 token-table audit",
        "",
        f"- Status: **{report['status']}**",
        f"- Pool records: {len(pool)}; unique IDs: {len(pool_idx)}",
        f"- Token records: {len(tokens)}; unique IDs: {len(token_idx)}",
        f"- Common IDs: {len(pool_ids & token_ids)}",
        f"- Missing token rows: {len(missing_tokens)}",
        f"- Extra token rows: {len(extra_tokens)}",
        f"- Problem ID mismatches: {len(problem_mismatches)}",
        f"- Invalid response_tokens: {len(invalid_token_counts)}",
        "",
        "## Input fingerprints",
        f"- Verified pool SHA-256: `{pool_hash}`",
        f"- Token table SHA-256: `{token_hash}`",
        "",
        "## Checks",
    ]
    lines.extend(f"- [{'x' if ok else ' '}] {name}" for name, ok in checks.items())
    lines += ["", "## Interpretation", "A PASS means the token table is structurally aligned with the verified pool by trajectory_id and problem_id. It does not by itself prove historical tokenization provenance or equality with historical train-log pool hashes."]
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"G6_TOKEN_AUDIT={report['status']}")
    for name, value in report["counts"].items():
        print(f"{name.upper()}={value}")
    print(f"POOL_SHA256={pool_hash}")
    print(f"TOKEN_TABLE_SHA256={token_hash}")
    print(f"REPORT_DIR={output_dir}")
    print(f"JSON={json_path}")
    print(f"MARKDOWN={md_path}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
