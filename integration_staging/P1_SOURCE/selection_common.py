"""Deterministic, fail-fast selectors for B2/B3/B4/B5.

Budget A counts trajectory response tokens only (n_traj); <|im_end|> is excluded.
B4 ranks once conceptually by S0 L_proxy and walks that ranking across rounds.
B5 ranks by the current S_t L_proxy and permits cross-round re-selection.
"""
import argparse
import json
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from student_common import (  # noqa: E402
    MANUAL_DIR, POOL_VERIFIED, CONFIG_PATH, load_config, load_pool,
    load_tokenizer, encode_example, sha256_file,
)


def read_jsonl(path):
    if not path or not Path(path).exists():
        return []
    rows = []
    with Path(path).open(encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise ValueError(f"{path}:{i}: invalid JSON: {exc}") from exc
    return rows


def atomic_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    if tmp.exists():
        raise RuntimeError(f"stale temporary artifact exists: {tmp}; inspect before continuing")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)



def rank_by_learnability(pool, scores):
    """Descending L_proxy; trajectory_id ascending is the deterministic tie-break."""
    return sorted(pool, key=lambda r: (-float(scores[r["trajectory_id"]]["l_proxy"]), r["trajectory_id"]))


def fill_budget(candidates, lengths, budget, used_problems=None, excluded_ids=None):
    """Greedy Budget-A fill. Oversized candidates are skipped; later candidates are still examined."""
    used = set(used_problems or ())
    excluded = set(excluded_ids or ())
    selected, events, spent = [], [], 0
    for rank, row in enumerate(candidates, 1):
        tid, pid = row["trajectory_id"], row["problem_id"]
        nt = int(lengths[tid])
        if pid in used:
            reason = "n_cap_reached"
            choose = False
        elif tid in excluded:
            reason = "already_selected_in_previous_round"
            choose = False
        elif spent + nt > budget:
            reason = "budget_exhausted_skip_continue"
            choose = False
        else:
            reason = "selected"
            choose = True
            selected.append(row)
            used.add(pid)
            spent += nt
        events.append({"rank": rank, "trajectory_id": tid, "problem_id": pid,
                       "tokens": nt, "selected": choose, "reason": reason})
    return selected, events, spent


def parser_for(method):
    p = argparse.ArgumentParser(description=f"Select one round for {method}")
    p.add_argument("--round", type=int, required=True)
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--log", type=Path, required=True)
    p.add_argument("--pool", type=Path, default=POOL_VERIFIED)
    p.add_argument("--config", type=Path, default=CONFIG_PATH)
    p.add_argument("--scores", type=Path)
    p.add_argument("--source-checkpoint")
    p.add_argument("--budget", type=int, help="reduced budget for smoke tests only")
    return p


def _resume_if_complete(method, a, pool_ids, log_rows):
    existing_round = [r for r in log_rows if r.get("record_type") == "selection"
                      and r.get("method") == method
                      and int(r.get("training_seed", -1)) == a.seed
                      and int(r.get("round", -1)) == a.round]
    out_exists = a.out.exists()
    if not out_exists and not existing_round:
        return False
    if not out_exists or not existing_round:
        raise RuntimeError(
            "incomplete selection artifact state: train-set JSON and round log must either both exist "
            "or both be absent; inspect manually, no overwrite attempted"
        )
    log_ids = [r.get("trajectory_id") for r in existing_round]
    if len(existing_round) != len(pool_ids) or len(log_ids) != len(set(log_ids)) or set(log_ids) != set(pool_ids):
        raise RuntimeError(f"incomplete or duplicated round log coverage: {len(existing_round)}/{len(pool_ids)} pool records")
    train = json.loads(a.out.read_text(encoding="utf-8"))
    if train.get("pool_sha256") != sha256_file(a.pool) or train.get("config_sha256") != sha256_file(a.config):
        raise RuntimeError("existing train set pool/config hash differs from current inputs")
    if a.scores and train.get("scores_sha256") != sha256_file(a.scores):
        raise RuntimeError("existing train set score hash differs from current scores")
    selected_log = [r["trajectory_id"] for r in existing_round if r.get("selected")]
    if train.get("method") != method or train.get("round") != a.round or train.get("training_seed") != a.seed:
        raise RuntimeError("existing train set metadata does not match requested method/round/seed")
    if train.get("trajectory_ids") != selected_log:
        raise RuntimeError("existing train set and selection log disagree; inspect manually")
    print(f"[RESUME] Reusing completed selection: {a.out}")
    return True


def run(method, strategy, a):
    cfg = json.loads(a.config.read_text(encoding="utf-8"))
    if not 0 <= a.round < int(cfg["schedule"]["rounds_M"]):
        raise ValueError("round outside configured schedule")
    budget = int(a.budget if a.budget is not None else cfg["budget"]["beta_round_tokens"])
    if budget <= 0:
        raise ValueError("budget must be positive")

    pool = load_pool(a.pool)
    byid = {r["trajectory_id"]: r for r in pool}
    if len(byid) != len(pool):
        raise ValueError("duplicate trajectory_id in verified pool")

    # Budget A: trajectory response only. n_supervised includes <|im_end|>; n_traj excludes it.
    tok = load_tokenizer(cfg["student"]["model"], cfg["student"]["revision"])
    lengths = {}
    for r in pool:
        enc = encode_example(tok, r["question"], r["raw_generation"], add_eos=False)
        n = int(enc["n_traj"])
        if n <= 0:
            raise ValueError(f"zero-length response trajectory: {r['trajectory_id']}")
        lengths[r["trajectory_id"]] = n

    scores = {}
    if method in ("B4", "B5"):
        if not a.scores or not a.scores.exists():
            raise ValueError(f"{method} requires an existing full-pool --scores file")
        for row in read_jsonl(a.scores):
            tid = row.get("trajectory_id")
            if not tid or tid in scores:
                raise ValueError(f"missing or duplicate trajectory_id in score file: {tid}")
            if tid not in byid:
                raise ValueError(f"score contains trajectory outside verified pool: {tid}")
            try:
                score = float(row["l_proxy"])
                ell = float(row["nll"])
                median = float(row["ell_star"])
                sigma = float(row["sigma"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"incomplete learnability score for {tid}: {exc}") from exc
            if not all(math.isfinite(x) for x in (score, ell, median, sigma)):
                raise ValueError(f"non-finite learnability value for {tid}")
            if not 0.0 <= score <= 1.0 or sigma <= 0:
                raise ValueError(f"invalid L_proxy/sigma for {tid}: {score}/{sigma}")
            scores[tid] = row
        missing = set(byid) - set(scores)
        extra = set(scores) - set(byid)
        if missing or extra:
            raise ValueError(f"score coverage mismatch: missing={len(missing)}, extra={len(extra)}")

    source = a.source_checkpoint or (f"student_ckpt_{a.round:03d}" if method == "B5" else "student_ckpt_000")
    if method in ("B4", "B5"):
        wrong = [tid for tid in byid if scores[tid].get("checkpoint") != source]
        if wrong:
            raise ValueError(f"score checkpoint mismatch; expected {source}, first IDs={wrong[:3]}")
    if method == "B4" and source != "student_ckpt_000":
        raise ValueError("B4 must use S0 scores")
    if method == "B5" and source != f"student_ckpt_{a.round:03d}":
        raise ValueError("B5 source checkpoint must match the current round")

    hist = read_jsonl(a.log)
    if _resume_if_complete(method, a, set(byid), hist):
        return
    prior = [r for r in hist if r.get("record_type") == "selection" and r.get("method") == method
             and int(r.get("training_seed", -1)) == a.seed]
    prev_selected = {r["trajectory_id"] for r in prior if r.get("selected")}
    used_problems = {r["problem_id"] for r in prior if int(r.get("round", -1)) == a.round and r.get("selected")}

    if strategy == "random":
        candidates = list(pool)
        random.Random(a.seed * 100 + a.round).shuffle(candidates)
    elif strategy == "shortest":
        best = {}
        for r in pool:
            key = (lengths[r["trajectory_id"]], r["trajectory_id"])
            if r["problem_id"] not in best or key < best[r["problem_id"]][0]:
                best[r["problem_id"]] = (key, r)
        candidates = [item[1] for item in best.values()]
        random.Random(a.seed).shuffle(candidates)
    else:
        # Deterministic tie-break: trajectory_id ascending.
        candidates = rank_by_learnability(pool, scores)

    selected, events, spent = fill_budget(
        candidates, lengths, budget, used_problems,
        prev_selected if method in ("B3", "B4") else set()
    )
    logrows = []
    reason_map = {"B2": "random", "B3": "shortest_correct", "B4": "top_l_proxy_static",
                  "B5": "top_l_proxy_dynamic"}
    for event, row in zip(events, candidates):
        rank, tid, pid, n_tokens = event["rank"], event["trajectory_id"], event["problem_id"], event["tokens"]
        score_row = scores.get(tid, {})
        choose = event["selected"]
        reason = reason_map[method] if choose else event["reason"]
        logrows.append({
            "record_type": "selection", "method": method, "round": a.round,
            "source_checkpoint": source, "training_seed": a.seed,
            "problem_id": pid, "trajectory_id": tid, "tokens": n_tokens,
            "nll": score_row.get("nll"), "ell_star": score_row.get("ell_star"),
            "sigma": score_row.get("sigma"), "l_proxy": score_row.get("l_proxy"),
            "score": score_row.get("l_proxy") if method in ("B4", "B5") else None,
            "rank": rank if method in ("B3", "B4", "B5") else None,
            "selected": choose, "criterion": reason, "outcome": None,
            "config_hash": sha256_file(a.config),
        })
    if not selected:
        raise RuntimeError("empty selection; inspect budget, n_cap, scores and history")

    try:
        pool_rel = str(a.pool.resolve().relative_to(MANUAL_DIR.resolve())).replace("\\", "/")
    except ValueError as exc:
        raise ValueError("pool must be located inside manual/ for train_round.py") from exc
    train = {
        "method": method, "round": a.round, "training_seed": a.seed,
        "source_checkpoint": source, "pool": pool_rel, "pool_sha256": sha256_file(a.pool),
        "trajectory_ids": [r["trajectory_id"] for r in selected],
        "n_trajectories": len(selected), "trajectory_tokens": spent,
        "trajectory_token_budget": budget,
        "budget_unit": "Student-tokenized trajectory response tokens; excludes <|im_end|> (Budget A)",
        "config_sha256": sha256_file(a.config),
        "scores_sha256": sha256_file(a.scores) if a.scores else None,
    }
    if a.out.exists():
        raise RuntimeError(f"refusing to overwrite existing train set: {a.out}")
    if a.log.exists() and any(r.get("record_type") == "selection" and r.get("method") == method
                              and int(r.get("training_seed", -1)) == a.seed
                              and int(r.get("round", -1)) == a.round for r in hist):
        raise RuntimeError("round log records exist but are not a complete resumable artifact")

    # Commit train set first; if append is interrupted, the next run fails closed for manual review.
    atomic_json(a.out, train)
    a.log.parent.mkdir(parents=True, exist_ok=True)
    with a.log.open("a", encoding="utf-8") as f:
        for row in logrows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        f.flush()
    print(f"[PASS] {method} round={a.round} seed={a.seed}: {len(selected)} trajectories, {spent}/{budget} Budget-A tokens")
    print(f"[OUT] {a.out}")


if __name__ == "__main__":
    raise SystemExit("Import run() from a method-specific selector")
