from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

TRAIN_SET = ROOT / "runs/p1p2_integration/P1-DEFICIT_seed13/round_001/train_set.json"
SELECTION_LOG = ROOT / "runs/p1p2_integration/P1-DEFICIT_seed13/round_001/selection_log.jsonl"

POOL = ROOT / "trajectory/pool/pool_v1_verified.jsonl"
TOKENS = ROOT / "trajectory/pool/pool_v1_tokens.jsonl"
TOKEN_SUMMARY = ROOT / "trajectory/pool/pool_v1_tokens.summary.json"
D_POOL = ROOT / "splits/d_pool_ids.txt"
CONFIG = ROOT / "config/experiment_config.json"
STATE = ROOT / "reports/p1p2_integration/capability_state/P1-DEFICIT_seed13/S0_state.json"

EXPECTED_METHOD = "P1-DEFICIT"
EXPECTED_SEED = 13
EXPECTED_ROUND = 1
EXPECTED_SOURCE = "S0"


def fail(message: str) -> None:
    raise ValueError(message)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_json(path: Path):
    if not path.is_file():
        fail(f"MISSING_FILE: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path):
    if not path.is_file():
        fail(f"MISSING_FILE: {path}")
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                fail(f"INVALID_JSONL: {path}:{line_no}: {exc}")
    return rows


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def main() -> int:
    for path in (
        TRAIN_SET, SELECTION_LOG, POOL, TOKENS,
        TOKEN_SUMMARY, D_POOL, CONFIG, STATE,
    ):
        require(path.is_file(), f"MISSING_FILE: {path}")

    train = read_json(TRAIN_SET)
    log_rows = read_jsonl(SELECTION_LOG)
    pool_rows = read_jsonl(POOL)
    token_rows = read_jsonl(TOKENS)
    token_summary = read_json(TOKEN_SUMMARY)
    config = read_json(CONFIG)

    require(train.get("schema_version") == "p1p2.train-set.v1",
            "TRAIN_SET_SCHEMA_MISMATCH")
    require(train.get("method") == EXPECTED_METHOD, "METHOD_MISMATCH")
    require(train.get("training_seed") == EXPECTED_SEED, "SEED_MISMATCH")
    require(train.get("round") == EXPECTED_ROUND, "ROUND_MISMATCH")
    require(train.get("source_checkpoint") == EXPECTED_SOURCE,
            "SOURCE_CHECKPOINT_MISMATCH")

    expected_hashes = {
        "pool_sha256": POOL,
        "tokens_sha256": TOKENS,
        "tokens_summary_sha256": TOKEN_SUMMARY,
        "config_sha256": CONFIG,
        "state_sha256": STATE,
    }

    for field, path in expected_hashes.items():
        actual = sha256(path)
        recorded = train.get(field)
        require(recorded == actual,
                f"HASH_MISMATCH: {field}: recorded={recorded}, actual={actual}")
        print(f"HASH_PASS | {field} | {actual}")

    selection_cfg = config.get("selection", {})
    budget_cfg = config.get("budget", {})
    budget = budget_cfg.get("beta_round_tokens")

    require(selection_cfg.get("n_cap") == 1, "N_CAP_MISMATCH")
    require(selection_cfg.get("alpha") == 0.5, "ALPHA_MISMATCH")
    require(selection_cfg.get("alpha_tuned") is False, "ALPHA_TUNED_MUST_BE_FALSE")
    require(selection_cfg.get("allow_reselect_across_rounds") is True,
            "RESELECT_POLICY_MISMATCH")
    require(train.get("beta_round_tokens") == budget, "TRAIN_SET_BUDGET_MISMATCH")
    require(train.get("n_cap") == 1, "TRAIN_SET_N_CAP_MISMATCH")

    pool_by_id = {}
    problem_ids = set()

    for row in pool_rows:
        tid = row.get("trajectory_id")
        pid = row.get("problem_id")
        require(isinstance(tid, str) and tid, "POOL_ROW_MISSING_TRAJECTORY_ID")
        require(tid not in pool_by_id, f"DUPLICATE_POOL_TRAJECTORY: {tid}")
        require(isinstance(pid, str) and pid, f"POOL_ROW_MISSING_PROBLEM_ID: {tid}")
        metadata = row.get("metadata") or {}
        require(metadata.get("verification_status") == "valid",
                f"POOL_ROW_NOT_VERIFIED: {tid}")
        caps = row.get("capabilities")
        require(isinstance(caps, list) and len(caps) > 0,
                f"POOL_ROW_MISSING_CAPABILITIES: {tid}")
        pool_by_id[tid] = row
        problem_ids.add(pid)

    token_by_id = {}
    for row in token_rows:
        tid = row.get("trajectory_id")
        require(isinstance(tid, str) and tid, "TOKEN_ROW_MISSING_TRAJECTORY_ID")
        require(tid not in token_by_id, f"DUPLICATE_TOKEN_TRAJECTORY: {tid}")
        count = row.get("response_tokens")
        require(isinstance(count, int) and not isinstance(count, bool) and count > 0,
                f"INVALID_RESPONSE_TOKENS: {tid}")
        token_by_id[tid] = count

    require(set(token_by_id) == set(pool_by_id),
            "TOKEN_TABLE_POOL_COVERAGE_MISMATCH")
    require(len(pool_by_id) == 4353, f"UNEXPECTED_POOL_COUNT: {len(pool_by_id)}")
    require(token_summary.get("n_trajectories") == len(pool_by_id),
            "TOKEN_SUMMARY_COUNT_MISMATCH")
    require(token_summary.get("pool_sha256") == sha256(POOL),
            "TOKEN_SUMMARY_POOL_HASH_MISMATCH")

    d_pool_ids = {
        line.strip()
        for line in D_POOL.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    require(problem_ids.issubset(d_pool_ids),
            "VERIFIED_POOL_CONTAINS_PROBLEM_OUTSIDE_D_POOL")

    selected_ids = train.get("trajectory_ids")
    require(isinstance(selected_ids, list) and selected_ids,
            "TRAIN_SET_IDS_MISSING")
    require(len(selected_ids) == len(set(selected_ids)),
            "DUPLICATE_SELECTED_TRAJECTORY_IDS")
    require(all(tid in pool_by_id for tid in selected_ids),
            "SELECTED_ID_OUTSIDE_VERIFIED_POOL")

    selected_token_sum = sum(token_by_id[tid] for tid in selected_ids)
    require(selected_token_sum == train.get("tokens_used"),
            "TRAIN_SET_TOKEN_SUM_MISMATCH")
    require(selected_token_sum <= budget,
            f"TOKEN_BUDGET_EXCEEDED: {selected_token_sum}/{budget}")
    require(len(selected_ids) == train.get("n_selected"),
            "TRAIN_SET_SELECTED_COUNT_MISMATCH")
    require(len(pool_by_id) == train.get("n_eligible"),
            "TRAIN_SET_ELIGIBLE_COUNT_MISMATCH")

    log_by_id = {}
    for row in log_rows:
        tid = row.get("trajectory_id")
        require(isinstance(tid, str) and tid, "LOG_ROW_MISSING_TRAJECTORY_ID")
        require(tid not in log_by_id, f"DUPLICATE_SELECTION_LOG_ID: {tid}")
        log_by_id[tid] = row

    require(set(log_by_id) == set(pool_by_id),
            "SELECTION_LOG_POOL_COVERAGE_MISMATCH")

    selected_from_log = {
        tid for tid, row in log_by_id.items()
        if row.get("selected") is True
    }
    require(selected_from_log == set(selected_ids),
            "SELECTION_LOG_SELECTED_IDS_MISMATCH")

    for tid in selected_ids:
        row = log_by_id[tid]
        require(row.get("method") == EXPECTED_METHOD, f"LOG_METHOD_MISMATCH: {tid}")
        require(row.get("seed") == EXPECTED_SEED, f"LOG_SEED_MISMATCH: {tid}")
        require(row.get("round") == EXPECTED_ROUND, f"LOG_ROUND_MISMATCH: {tid}")
        require(row.get("source_checkpoint") == EXPECTED_SOURCE,
                f"LOG_SOURCE_CHECKPOINT_MISMATCH: {tid}")
        require(row.get("token_count") == token_by_id[tid],
                f"LOG_TOKEN_COUNT_MISMATCH: {tid}")
        require(row.get("reason") == "selected", f"LOG_REASON_MISMATCH: {tid}")

    print(f"POOL_COUNT={len(pool_by_id)}")
    print(f"TOKEN_TABLE_COUNT={len(token_by_id)}")
    print(f"D_POOL_PROBLEM_COUNT={len(d_pool_ids)}")
    print(f"SELECTION_LOG_ROWS={len(log_rows)}")
    print(f"SELECTED_COUNT={len(selected_ids)}")
    print(f"SELECTED_TOKENS={selected_token_sum}")
    print(f"TOKEN_BUDGET={budget}")
    print(f"TOKEN_REMAINING={budget - selected_token_sum}")
    print(f"TRAIN_SET_SHA256={sha256(TRAIN_SET)}")
    print(f"SELECTION_LOG_SHA256={sha256(SELECTION_LOG)}")
    print("P1_DEFICIT_ARTIFACT_AUDIT=PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"P1_DEFICIT_ARTIFACT_AUDIT=FAIL: {type(exc).__name__}: {exc}",
              file=sys.stderr)
        raise
