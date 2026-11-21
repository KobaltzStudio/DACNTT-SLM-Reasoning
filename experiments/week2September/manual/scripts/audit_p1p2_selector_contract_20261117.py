#!/usr/bin/env python3
"""Read-only contract audit for the P1/P2 selector and controller."""
from __future__ import annotations

import ast
import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

P2_FILES = [
    "scripts/selection.py",
    "scripts/learnability.py",
    "scripts/select_round.py",
    "scripts/train_round.py",
    "scripts/compute_nll.py",
    "scripts/build_pool_tokens.py",
    "scripts/student_common.py",
    "scripts/eval_student.py",
]

P1_FILES = [
    "integration_staging/P1/scripts/selection_common.py",
    "integration_staging/P1/scripts/compute_learnability.py",
    "integration_staging/P1/scripts/evaluate_student_capabilities.py",
    "integration_staging/P1/scripts/build_capability_graph.py",
]

EXPECTED_SOURCE_HASHES = {
    "scripts/selection.py":
        "586B36254A10B5A144ABB0559D90057A56DFC59C33B7FCA6C233502B4F10DEAE",
    "scripts/learnability.py":
        "A97F44C5905BF3779BA1909C28174C4CF96E31E06C83C4FFEFE1858C7420E4C3",
    "scripts/select_round.py":
        "06CED4DE235C2E22223810E8C52C14E02B943223E02C5B0712B1F45303DE8281",
    "scripts/train_round.py":
        "D78E7E329BA49E7C17E16265EE49B40E113F6B9EFCB65BEF9BF574C50BEF95FE",
    "scripts/compute_nll.py":
        "SOURCE_HASH_TO_BE_REPORTED",
    "scripts/student_common.py":
        "C3BF2DFCDF0525B481CF25F467E39A09748B4FD48DC905DC3EDD3C03AC8983FB",
    "scripts/eval_student.py":
        "52A653F64D8EC720BF340F3F258B6C779BAFEA63B9E1A333539675DFEC31A5F8",
}

CAPABILITIES = {
    "addition", "subtraction", "multiplication", "division",
    "percentage", "fraction", "ratio",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_jsonl(path: Path):
    rows = []
    with path.open("r", encoding="utf-8-sig") as stream:
        for line_no, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except Exception as exc:
                raise ValueError(
                    f"Invalid JSONL {path}, line {line_no}: {exc}"
                ) from exc
    return rows


def function_signatures(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    result = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = [a.arg for a in node.args.args]
            result.append({
                "name": node.name,
                "args": args,
                "line": node.lineno,
            })
    return sorted(result, key=lambda x: (x["line"], x["name"]))


def run_help(path: Path):
    if not path.is_file():
        return {"status": "MISSING", "path": str(path)}
    try:
        proc = subprocess.run(
            [sys.executable, str(path), "--help"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=90,
        )
        output = (proc.stdout or "") + "\n" + (proc.stderr or "")
        return {
            "status": "PASS" if proc.returncode == 0 else "FAIL",
            "returncode": proc.returncode,
            "help": output[:18000],
        }
    except Exception as exc:
        return {"status": "ERROR", "error": repr(exc)}


def find_capabilities(row):
    candidates = [
        row.get("capabilities"),
        row.get("metadata", {}).get("capabilities")
        if isinstance(row.get("metadata"), dict) else None,
    ]
    for value in candidates:
        if isinstance(value, list):
            return value
    return None


def find_verification(row):
    metadata = row.get("metadata")
    if isinstance(metadata, dict):
        return metadata.get("verification_status")
    return row.get("verification_status")


def main():
    report = {
        "schema": "p1p2.selector_contract_audit.v1",
        "root": str(ROOT),
        "source_files": {},
        "config": {},
        "pool": {},
        "tokens": {},
        "splits": {},
        "cli": {},
        "findings": [],
    }

    # 1. Source file inventory, hashes and function contracts.
    for rel in P2_FILES + P1_FILES:
        path = ROOT / rel
        if not path.is_file():
            report["source_files"][rel] = {"status": "MISSING"}
            continue

        actual_hash = sha256_file(path)
        expected = EXPECTED_SOURCE_HASHES.get(rel)
        hash_status = (
            "MATCH" if expected and expected != "SOURCE_HASH_TO_BE_REPORTED"
            and actual_hash.upper() == expected.upper()
            else "NOT_PINNED" if not expected
            or expected == "SOURCE_HASH_TO_BE_REPORTED"
            else "MISMATCH"
        )

        report["source_files"][rel] = {
            "status": "FOUND",
            "sha256": actual_hash,
            "expected_sha256": expected,
            "hash_status": hash_status,
            "bytes": path.stat().st_size,
            "functions": function_signatures(path),
        }

    # 2. Frozen config: read only.
    config_path = ROOT / "config/experiment_config.json"
    if config_path.is_file():
        cfg = read_json(config_path)
        report["config"] = {
            "path": str(config_path),
            "sha256": sha256_file(config_path),
            "seeds": cfg.get("seeds"),
            "schedule": cfg.get("schedule"),
            "budget": cfg.get("budget"),
            "selection": cfg.get("selection"),
            "training": cfg.get("training"),
            "model": cfg.get("model"),
            "evaluation": cfg.get("evaluation"),
        }
    else:
        report["findings"].append("MISSING config/experiment_config.json")

    # 3. Verified pool schema and capability labels.
    pool_path = ROOT / "trajectory/pool/pool_v1_verified.jsonl"
    pool_rows = []
    pool_by_id = {}

    if pool_path.is_file():
        pool_rows = read_jsonl(pool_path)
        trajectory_ids = []
        problem_ids = []
        capability_counts = Counter()
        capability_paths = Counter()
        verification_counts = Counter()
        missing_caps = []
        unknown_caps = []
        malformed_caps = []

        for index, row in enumerate(pool_rows):
            tid = str(row.get("trajectory_id", "")).strip()
            pid = str(row.get("problem_id", "")).strip()
            trajectory_ids.append(tid)
            problem_ids.append(pid)

            if tid:
                if tid in pool_by_id:
                    raise ValueError(f"Duplicate pool trajectory_id: {tid}")
                pool_by_id[tid] = row

            caps = find_capabilities(row)
            if caps is None:
                missing_caps.append(index)
            else:
                path_name = (
                    "top_level" if isinstance(row.get("capabilities"), list)
                    else "metadata"
                )
                capability_paths[path_name] += 1

                if not caps:
                    malformed_caps.append(index)
                if len(caps) != len(set(caps)):
                    malformed_caps.append(index)

                for cap in caps:
                    capability_counts[str(cap)] += 1
                    if cap not in CAPABILITIES:
                        unknown_caps.append(str(cap))

            verification_counts[str(find_verification(row))] += 1

        report["pool"] = {
            "path": str(pool_path),
            "sha256": sha256_file(pool_path),
            "records": len(pool_rows),
            "unique_trajectory_ids": len(set(trajectory_ids)),
            "unique_problem_ids": len(set(problem_ids)),
            "duplicate_trajectory_ids": (
                len(trajectory_ids) - len(set(trajectory_ids))
            ),
            "empty_trajectory_ids": sum(not x for x in trajectory_ids),
            "empty_problem_ids": sum(not x for x in problem_ids),
            "capability_field_paths": dict(capability_paths),
            "capability_counts": dict(capability_counts),
            "verification_counts": dict(verification_counts),
            "missing_capability_rows": len(missing_caps),
            "malformed_capability_rows": len(malformed_caps),
            "unknown_capability_values": sorted(set(unknown_caps)),
            "sample_record": pool_rows[0] if pool_rows else None,
        }
    else:
        report["findings"].append("MISSING verified pool")

    # 4. Token table and pool consistency.
    tokens_path = ROOT / "trajectory/pool/pool_v1_tokens.jsonl"
    tokens_summary_path = tokens_path.with_suffix(".summary.json")

    if tokens_path.is_file():
        token_rows = read_jsonl(tokens_path)
        token_by_id = {}
        duplicate_token_ids = []
        invalid_token_rows = []

        for row in token_rows:
            tid = str(row.get("trajectory_id", "")).strip()
            if not tid or tid in token_by_id:
                duplicate_token_ids.append(tid)
            else:
                token_by_id[tid] = row

            try:
                if int(row["response_tokens"]) <= 0:
                    invalid_token_rows.append(tid)
            except Exception:
                invalid_token_rows.append(tid)

        pool_ids = set(pool_by_id)
        token_ids = set(token_by_id)

        report["tokens"] = {
            "path": str(tokens_path),
            "sha256": sha256_file(tokens_path),
            "records": len(token_rows),
            "unique_trajectory_ids": len(token_ids),
            "duplicate_ids": duplicate_token_ids[:20],
            "invalid_token_rows": invalid_token_rows[:20],
            "pool_minus_tokens": len(pool_ids - token_ids),
            "tokens_minus_pool": len(token_ids - pool_ids),
            "sample_row": token_rows[0] if token_rows else None,
        }

        if tokens_summary_path.is_file():
            report["tokens"]["summary"] = read_json(tokens_summary_path)
            report["tokens"]["summary_sha256"] = sha256_file(
                tokens_summary_path
            )
        else:
            report["tokens"]["summary"] = "MISSING"

        if pool_ids != token_ids:
            report["findings"].append(
                "Pool trajectory IDs and token table IDs do not match exactly"
            )
    else:
        report["tokens"] = {"status": "MISSING"}
        report["findings"].append("MISSING pool_v1_tokens.jsonl")

    # 5. D_pool membership.
    d_pool_path = ROOT / "splits/d_pool_ids.txt"
    if d_pool_path.is_file():
        d_pool_ids = {
            line.strip()
            for line in d_pool_path.read_text(
                encoding="utf-8-sig"
            ).splitlines()
            if line.strip()
        }
        pool_problem_ids = {
            str(row.get("problem_id", "")).strip()
            for row in pool_rows
            if row.get("problem_id")
        }
        report["splits"]["d_pool"] = {
            "path": str(d_pool_path),
            "sha256": sha256_file(d_pool_path),
            "ids": len(d_pool_ids),
            "pool_unique_problem_ids": len(pool_problem_ids),
            "pool_problem_ids_outside_d_pool": sorted(
                pool_problem_ids - d_pool_ids
            )[:30],
        }
    else:
        report["findings"].append("MISSING splits/d_pool_ids.txt")

    # 6. P2 CLI contracts. --help only; no NLL or training is executed.
    report["cli"]["compute_nll"] = run_help(
        ROOT / "scripts/compute_nll.py"
    )
    report["cli"]["train_round"] = run_help(
        ROOT / "scripts/train_round.py"
    )
    report["cli"]["eval_student"] = run_help(
        ROOT / "scripts/eval_student.py"
    )

    # 7. Source hash comparison.
    mismatches = [
        name for name, item in report["source_files"].items()
        if item.get("hash_status") == "MISMATCH"
    ]
    missing = [
        name for name, item in report["source_files"].items()
        if item.get("status") == "MISSING"
    ]
    report["source_hash_mismatches"] = mismatches
    report["missing_source_files"] = missing

    output = (
        ROOT / "reports/p1p2_integration/source_review/"
        / "selector_contract_audit_20261117.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)

    encoded = (
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    ).encode("utf-8")

    if output.exists():
        raise FileExistsError(
            "Audit report already exists; refusing overwrite: " + str(output)
        )

    output.write_bytes(encoded)

    print("SELECTOR_CONTRACT_AUDIT=COMPLETED")
    print(f"P2_SOURCE_FILES_FOUND={sum(x.get('status') == 'FOUND' for k, x in report['source_files'].items() if k in P2_FILES)}/{len(P2_FILES)}")
    print(f"P1_SOURCE_FILES_FOUND={sum(x.get('status') == 'FOUND' for k, x in report['source_files'].items() if k in P1_FILES)}/{len(P1_FILES)}")
    print(f"SOURCE_HASH_MISMATCHES={len(mismatches)}")
    print(f"POOL_RECORDS={report.get('pool', {}).get('records')}")
    print(f"POOL_UNIQUE_PROBLEMS={report.get('pool', {}).get('unique_problem_ids')}")
    print(f"POOL_CAPABILITY_PATHS={report.get('pool', {}).get('capability_field_paths')}")
    print(f"POOL_CAPABILITY_COUNTS={report.get('pool', {}).get('capability_counts')}")
    print(f"TOKEN_RECORDS={report.get('tokens', {}).get('records')}")
    print(f"TOKEN_POOL_ID_DIFF={report.get('tokens', {}).get('pool_minus_tokens')}/{report.get('tokens', {}).get('tokens_minus_pool')}")
    print(f"CONFIG_SHA256={report.get('config', {}).get('sha256')}")
    print(f"COMPUTE_NLL_HELP={report['cli']['compute_nll']['status']}")
    print(f"TRAIN_ROUND_HELP={report['cli']['train_round']['status']}")
    print(f"EVAL_STUDENT_HELP={report['cli']['eval_student']['status']}")
    print(f"FINDINGS={len(report['findings'])}")
    print(f"REPORT={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
