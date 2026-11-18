from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from learnability import score_checkpoint
from selection import fill_budget, rank_by_score

POOL_DEFAULT = ROOT / "trajectory/pool/pool_v1_verified.jsonl"
TOKENS_DEFAULT = ROOT / "trajectory/pool/pool_v1_tokens.jsonl"
D_POOL_DEFAULT = ROOT / "splits/d_pool_ids.txt"
CONFIG_DEFAULT = ROOT / "config/experiment_config.json"
TAXONOMY = ("addition", "subtraction", "multiplication", "division", "percentage", "fraction", "ratio")
METHODS = ("P1-DEFICIT", "P1P2")
POLICY_VERSION = "p1p2_priority_v1"
EXPECTED_ALPHA = 0.5


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_number}: {exc}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"Expected JSON object at {path}:{line_number}")
            rows.append(row)
    return rows


def _require_file(path: Path, label: str) -> Path:
    path = Path(path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"{label} not found: {path}")
    return path


def load_pool(pool_path: Path, d_pool_path: Path) -> tuple[dict[str, dict], dict[str, str]]:
    pool_path = _require_file(pool_path, "Verified pool")
    d_pool_path = _require_file(d_pool_path, "D_pool ID file")
    d_pool_ids = {line.strip() for line in d_pool_path.read_text(encoding="utf-8").splitlines() if line.strip()}
    pool_by_id: dict[str, dict] = {}
    problems: dict[str, str] = {}
    for index, row in enumerate(read_jsonl(pool_path), 1):
        tid, pid = row.get("trajectory_id"), row.get("problem_id")
        if not isinstance(tid, str) or not tid:
            raise ValueError(f"Pool row {index}: invalid trajectory_id")
        if not isinstance(pid, str) or not pid:
            raise ValueError(f"Pool row {index}: invalid problem_id")
        if tid in pool_by_id:
            raise ValueError(f"Duplicate trajectory_id in pool: {tid}")
        metadata = row.get("metadata")
        if not isinstance(metadata, dict) or metadata.get("verification_status") != "valid":
            raise ValueError(f"{tid}: metadata.verification_status must be valid")
        capabilities = row.get("capabilities")
        if not isinstance(capabilities, list) or not capabilities:
            raise ValueError(f"{tid}: capability list is empty or invalid")
        if any(not isinstance(tag, str) for tag in capabilities):
            raise ValueError(f"{tid}: capability tags must be strings")
        if len(capabilities) != len(set(capabilities)):
            raise ValueError(f"{tid}: duplicate capability tags")
        unknown = sorted(set(capabilities) - set(TAXONOMY))
        if unknown:
            raise ValueError(f"{tid}: unknown capability tags: {unknown}")
        if pid not in d_pool_ids:
            raise ValueError(f"{tid}: problem_id is outside D_pool: {pid}")
        pool_by_id[tid] = row
        problems[tid] = pid
    if not pool_by_id:
        raise ValueError("Verified pool is empty")
    return pool_by_id, problems


def load_tokens(tokens_path: Path, pool_path: Path, problems: dict[str, str]) -> dict[str, int]:
    tokens_path = _require_file(tokens_path, "Token table")
    pool_path = _require_file(pool_path, "Verified pool")
    summary_path = tokens_path.with_suffix(".summary.json")
    summary = read_json(_require_file(summary_path, "Token summary"))
    actual_pool_hash = sha256_file(pool_path)
    if summary.get("pool_sha256") != actual_pool_hash:
        raise ValueError("Token summary pool_sha256 does not match the supplied pool file")
    rows = read_jsonl(tokens_path)
    tokens: dict[str, int] = {}
    for index, row in enumerate(rows, 1):
        tid, pid, count = row.get("trajectory_id"), row.get("problem_id"), row.get("response_tokens")
        if not isinstance(tid, str) or not tid:
            raise ValueError(f"Token row {index}: invalid trajectory_id")
        if tid in tokens:
            raise ValueError(f"Duplicate token row: {tid}")
        if tid not in problems:
            raise ValueError(f"Token row not present in verified pool: {tid}")
        if problems[tid] != pid:
            raise ValueError(f"Token problem_id mismatch: {tid}")
        if not isinstance(count, int) or isinstance(count, bool) or count <= 0:
            raise ValueError(f"Invalid response_tokens for {tid}: {count}")
        tokens[tid] = count
    if set(tokens) != set(problems):
        missing, extra = sorted(set(problems) - set(tokens)), sorted(set(tokens) - set(problems))
        raise ValueError(f"Pool/token IDs differ. Missing={missing[:5]}, extra={extra[:5]}")
    if len(rows) != summary.get("n_trajectories"):
        raise ValueError("Token summary n_trajectories mismatch")
    if sum(tokens.values()) != summary.get("response_tokens_sum"):
        raise ValueError("Token summary response_tokens_sum mismatch")
    return tokens


def load_capability_deficits(state_path: Path, method: str, seed: int, round_number: int) -> dict[str, float]:
    state = read_json(_require_file(state_path, "Capability state"))
    if state.get("schema_version") != "p1p2.capability-state.v1":
        raise ValueError("Unsupported capability state schema")
    target = state.get("target")
    if not isinstance(target, dict):
        raise ValueError("Capability state target is missing or invalid")
    expected = {"method": method, "seed": seed, "selection_round": round_number}
    for key, value in expected.items():
        if target.get(key) != value:
            raise ValueError(f"State target {key} mismatch: expected {value}, got {target.get(key)}")
    capabilities = state.get("capabilities")
    if not isinstance(capabilities, dict):
        raise ValueError("Capability state has no capabilities object")
    deficits: dict[str, float] = {}
    for capability in TAXONOMY:
        item = capabilities.get(capability)
        if not isinstance(item, dict):
            raise ValueError(f"Missing capability state: {capability}")
        value = item.get("deficit")
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError(f"Invalid deficit for {capability}: {value}")
        deficits[capability] = float(value)
    return deficits


def load_previous_train_ids(paths: list[Path], problems: dict[str, str], method: str, seed: int,
                            current_round: int, pool_sha256: str) -> list[str]:
    trained: set[str] = set()
    seen_rounds: set[int] = set()
    for path in paths:
        data = read_json(_require_file(path, "Previous train set"))
        if data.get("schema_version") != "p1p2.train-set.v1":
            raise ValueError(f"Unsupported previous train-set schema: {path}")
        if data.get("method") != method:
            raise ValueError(f"Previous train-set method mismatch: {path}")
        if data.get("training_seed") != seed:
            raise ValueError(f"Previous train-set seed mismatch: {path}")
        previous_round = data.get("round")
        if not isinstance(previous_round, int) or isinstance(previous_round, bool) or not 1 <= previous_round < current_round:
            raise ValueError(f"Previous train-set round must be in [1, {current_round - 1}]: {path}")
        if previous_round in seen_rounds:
            raise ValueError(f"Duplicate previous train-set round {previous_round}")
        seen_rounds.add(previous_round)
        if data.get("pool_sha256") != pool_sha256:
            raise ValueError(f"Previous train-set pool hash mismatch: {path}")
        ids = data.get("trajectory_ids")
        if not isinstance(ids, list) or not ids:
            raise ValueError(f"Invalid or empty trajectory_ids in {path}")
        for tid in ids:
            if not isinstance(tid, str) or tid not in problems:
                raise ValueError(f"Previous train set contains unknown trajectory: {tid}")
            trained.add(tid)
    expected_rounds = set(range(1, current_round))
    if seen_rounds != expected_rounds:
        raise ValueError(f"Previous train-set rounds incomplete: expected {sorted(expected_rounds)}, got {sorted(seen_rounds)}")
    return sorted(trained)


def load_nll(nll_path: Path, tokens: dict[str, int], source_checkpoint: str,
             pool_path: Path) -> tuple[dict[str, float], str]:
    nll_path = _require_file(nll_path, "NLL file")
    pool_path = _require_file(pool_path, "Verified pool")
    ell_by_id: dict[str, float] = {}
    for index, row in enumerate(read_jsonl(nll_path), 1):
        tid = row.get("trajectory_id")
        if not isinstance(tid, str) or not tid:
            raise ValueError(f"NLL row {index}: invalid trajectory_id")
        if tid in ell_by_id:
            raise ValueError(f"Duplicate NLL trajectory_id: {tid}")
        if tid not in tokens:
            raise ValueError(f"NLL trajectory not present in token table: {tid}")
        if row.get("checkpoint") != source_checkpoint:
            raise ValueError(f"NLL checkpoint mismatch for {tid}: expected {source_checkpoint}, got {row.get('checkpoint')}")
        if row.get("n_tokens") != tokens[tid]:
            raise ValueError(f"NLL token count mismatch for {tid}")
        ell = row.get("ell")
        if not isinstance(ell, (int, float)) or isinstance(ell, bool) or not math.isfinite(ell):
            raise ValueError(f"Invalid ell value for {tid}: {ell}")
        ell_by_id[tid] = float(ell)
    if set(ell_by_id) != set(tokens):
        missing, extra = sorted(set(tokens) - set(ell_by_id)), sorted(set(ell_by_id) - set(tokens))
        raise ValueError(f"NLL does not cover token table. Missing={missing[:5]}, extra={extra[:5]}")
    summary_path = nll_path.with_suffix(".summary.json")
    summary = read_json(_require_file(summary_path, "NLL summary"))
    if summary.get("checkpoint") != source_checkpoint:
        raise ValueError("NLL summary checkpoint mismatch")
    if summary.get("pool_sha256") != sha256_file(pool_path):
        raise ValueError("NLL summary pool_sha256 mismatch against supplied pool")
    if summary.get("n_trajectories") != len(tokens):
        raise ValueError("NLL summary trajectory count mismatch")
    return ell_by_id, sha256_file(nll_path)


def average_percentile_ranks(scores: dict[str, float]) -> dict[str, float]:
    if not scores:
        raise ValueError("Cannot rank an empty score mapping")
    ordered = sorted(scores.items(), key=lambda item: (item[1], item[0]))
    n = len(ordered)
    if n == 1:
        return {ordered[0][0]: 0.5}
    result: dict[str, float] = {}
    index = 0
    while index < n:
        end = index + 1
        value = ordered[index][1]
        while end < n and ordered[end][1] == value:
            end += 1
        average_rank = ((index + 1) + end) / 2.0
        percentile = (average_rank - 1.0) / (n - 1.0)
        for position in range(index, end):
            result[ordered[position][0]] = percentile
        index = end
    return result


def calculate_p1_scores(pool_by_id: dict[str, dict], deficits: dict[str, float]) -> dict[str, float]:
    result: dict[str, float] = {}
    for tid, row in pool_by_id.items():
        tags = row["capabilities"]
        result[tid] = sum(deficits[tag] for tag in tags) / len(tags)
    return result


def publish_pair_no_overwrite(train_set_path: Path, selection_log_path: Path,
                              train_set_bytes: bytes, selection_log_bytes: bytes) -> None:
    train_set_path, selection_log_path = Path(train_set_path), Path(selection_log_path)
    if train_set_path.resolve() == selection_log_path.resolve():
        raise ValueError("Train-set and selection-log paths must be different")
    train_set_path.parent.mkdir(parents=True, exist_ok=True)
    selection_log_path.parent.mkdir(parents=True, exist_ok=True)
    if train_set_path.exists() or selection_log_path.exists():
        raise FileExistsError("Refusing to overwrite an existing selector output")
    nonce = f"{os.getpid()}"
    train_tmp = train_set_path.with_name(train_set_path.name + f".{nonce}.tmp")
    log_tmp = selection_log_path.with_name(selection_log_path.name + f".{nonce}.tmp")
    created_train = False
    created_temps: list[Path] = []
    try:
        for temp_path, content in ((train_tmp, train_set_bytes), (log_tmp, selection_log_bytes)):
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            fd = os.open(str(temp_path), flags, 0o600)
            created_temps.append(temp_path)
            with os.fdopen(fd, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
        os.link(train_tmp, train_set_path)
        created_train = True
        os.link(log_tmp, selection_log_path)
    except Exception:
        if created_train and train_set_path.exists() and sha256_file(train_set_path) == hashlib.sha256(train_set_bytes).hexdigest():
            train_set_path.unlink()
        raise
    finally:
        for temp_path in created_temps:
            temp_path.unlink(missing_ok=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="P1-DEFICIT/P1P2 selector using canonical P2 selection primitives.")
    parser.add_argument("--method", required=True, choices=METHODS)
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--round", required=True, type=int, choices=(1, 2, 3))
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--nll", type=Path, default=None)
    parser.add_argument("--previous-train-set", type=Path, action="append", default=[])
    parser.add_argument("--pool", type=Path, default=POOL_DEFAULT)
    parser.add_argument("--tokens", type=Path, default=TOKENS_DEFAULT)
    parser.add_argument("--d-pool", type=Path, default=D_POOL_DEFAULT)
    parser.add_argument("--config", type=Path, default=CONFIG_DEFAULT)
    return parser


def run_selection(args: argparse.Namespace) -> dict[str, Any]:
    if args.seed < 0:
        raise ValueError("seed must be non-negative")
    if args.method == "P1-DEFICIT" and args.nll is not None:
        raise ValueError("P1-DEFICIT does not accept an NLL input")
    if args.method == "P1P2" and args.nll is None:
        raise ValueError("P1P2 requires --nll for the current source checkpoint")
    source_checkpoint = f"S{args.round - 1}"
    config_path = _require_file(args.config, "Frozen experiment config")
    config = read_json(config_path)
    selection_cfg = config.get("selection")
    budget_cfg = config.get("budget")
    if not isinstance(selection_cfg, dict) or not isinstance(budget_cfg, dict):
        raise ValueError("Frozen config is missing selection or budget section")
    alpha = selection_cfg.get("alpha")
    alpha_tuned = selection_cfg.get("alpha_tuned")
    if alpha != EXPECTED_ALPHA or alpha_tuned is not False:
        raise ValueError(f"Frozen alpha policy mismatch: expected alpha={EXPECTED_ALPHA}, alpha_tuned=false; got {alpha}, {alpha_tuned}")
    budget = budget_cfg.get("beta_round_tokens")
    n_cap = selection_cfg.get("n_cap")
    if not isinstance(budget, int) or isinstance(budget, bool) or budget <= 0:
        raise ValueError("Invalid beta_round_tokens in frozen config")
    if n_cap != 1:
        raise ValueError(f"Frozen protocol requires n_cap=1, found {n_cap}")
    if selection_cfg.get("allow_reselect_across_rounds") is not True:
        raise ValueError("Frozen protocol requires allow_reselect_across_rounds=true")

    pool_path = _require_file(args.pool, "Verified pool")
    tokens_path = _require_file(args.tokens, "Token table")
    pool_hash = sha256_file(pool_path)
    pool_by_id, problems = load_pool(pool_path, args.d_pool)
    tokens = load_tokens(tokens_path, pool_path, problems)
    deficits = load_capability_deficits(args.state, args.method, args.seed, args.round)
    trained_ids = load_previous_train_ids(args.previous_train_set, problems, args.method, args.seed, args.round, pool_hash)
    p1_scores = calculate_p1_scores(pool_by_id, deficits)
    p2_scores = None
    p2_percentiles = None
    ell_by_id = None
    ell_star = sigma = n_reference = nll_sha256 = None
    if args.method == "P1P2":
        ell_by_id, nll_sha256 = load_nll(args.nll, tokens, source_checkpoint, pool_path)
        scoring = score_checkpoint(ell_by_id, trained_ids)
        p2_scores = scoring["l_proxy"]
        ell_star, sigma, n_reference = scoring["ell_star"], scoring["sigma"], scoring["n_reference"]
        p2_percentiles = average_percentile_ranks(p2_scores)
        combined_scores = {tid: EXPECTED_ALPHA * p1_scores[tid] + (1.0 - EXPECTED_ALPHA) * p2_percentiles[tid] for tid in problems}
    else:
        combined_scores = dict(p1_scores)
    order = rank_by_score(combined_scores)
    selected, reasons, tokens_used, stopped = fill_budget(order, problems, tokens, budget, n_cap)
    if not stopped:
        raise ValueError(f"Candidate order exhausted before budget stop: {tokens_used}/{budget}")
    if not selected:
        raise ValueError("Selector returned an empty train set")
    if tokens_used > budget:
        raise ValueError(f"Budget violation: {tokens_used} > {budget}")
    ranks = {tid: rank for rank, tid in enumerate(order, 1)}
    log_rows = []
    for tid in sorted(problems):
        reason = reasons.get(tid, "not_selected")
        row = pool_by_id[tid]
        log_rows.append({
            "record_type": "selection", "policy_version": POLICY_VERSION, "method": args.method,
            "seed": args.seed, "round": args.round, "source_checkpoint": source_checkpoint,
            "trajectory_id": tid, "problem_id": problems[tid], "capabilities": row["capabilities"],
            "token_count": tokens[tid], "p1_deficit_score": p1_scores[tid],
            "p2_l_proxy": p2_scores[tid] if p2_scores is not None else None,
            "p2_percentile_rank": p2_percentiles[tid] if p2_percentiles is not None else None,
            "combined_score": combined_scores[tid], "rank": ranks[tid],
            "selected": reason == "selected", "reason": reason,
            "nll_ell": ell_by_id[tid] if ell_by_id is not None else None,
        })
    train_set = {
        "schema_version": "p1p2.train-set.v1", "method": args.method, "training_seed": args.seed,
        "round": args.round, "source_checkpoint": source_checkpoint,
        "priority_policy": {"version": POLICY_VERSION, "alpha": EXPECTED_ALPHA if args.method == "P1P2" else 1.0,
                             "p1_component": "mean_capability_deficit",
                             "p2_component": "average_percentile_rank_of_l_proxy" if args.method == "P1P2" else None,
                             "percentile_tie_policy": "average_rank"},
        "pool": str(pool_path), "pool_sha256": pool_hash,
        "tokens_file": str(tokens_path), "tokens_sha256": sha256_file(tokens_path),
        "tokens_summary_sha256": sha256_file(tokens_path.with_suffix(".summary.json")),
        "config": str(config_path), "config_sha256": sha256_file(config_path),
        "state_file": str(Path(args.state).resolve()), "state_sha256": sha256_file(args.state),
        "nll_file": str(Path(args.nll).resolve()) if args.nll else None, "nll_sha256": nll_sha256,
        "ell_star": ell_star, "sigma": sigma, "n_reference": n_reference,
        "n_eligible": len(problems), "n_trained_before": len(trained_ids),
        "trained_reference_exclusions": trained_ids, "beta_round_tokens": budget, "n_cap": n_cap,
        "allow_reselect_across_rounds": True, "tokens_used": tokens_used, "n_selected": len(selected),
        "trajectory_ids": selected,
    }
    out_dir = Path(args.out_dir).resolve()
    train_path, log_path = out_dir / "train_set.json", out_dir / "selection_log.jsonl"
    train_bytes = (json.dumps(train_set, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    log_bytes = "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in log_rows).encode("utf-8")
    publish_pair_no_overwrite(train_path, log_path, train_bytes, log_bytes)
    return {"method": args.method, "seed": args.seed, "round": args.round, "source_checkpoint": source_checkpoint,
            "n_eligible": len(problems), "n_trained_before": len(trained_ids), "n_selected": len(selected),
            "tokens_used": tokens_used, "budget": budget, "train_set": train_path, "selection_log": log_path}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_selection(args)
    for key, value in result.items():
        print(f"{key.upper()}={value}")
    print("P1P2_SELECTION=PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"P1P2_SELECTOR_ERROR={type(exc).__name__}: {exc}", file=sys.stderr)
        raise
