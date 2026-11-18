#!/usr/bin/env python3
"""
Select B_t for one method, seed and round; writes the train set and the selection log (selection.py has the rules).

Reads:
  --tokens          token table of the pool (build_pool_tokens.py)
  --nll             compute_nll.py output: at S_t for B5 and the ablation, at S_0 for B4 in every round
  <run-dir>/round_NNN/train_set.json of earlier rounds (trajectories already trained in this run, T7-3)

Writes (atomically):
  <run-dir>/round_NNN/train_set.json       input of train_round.py
  <run-dir>/round_NNN/selection_log.jsonl  one record per eligible trajectory (selection_log_schema.json)

--pilot allows a smaller budget and seeds outside the config; the output is marked and is not a result.

Usage (from experiments/week2September/manual/):
  python scripts/select_round.py --method B5 --seed 13 --round 1 --run-dir runs/main/B5_seed13 \
      --nll runs/main/B5_seed13/S1/nll.jsonl
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from selection import METHODS, NEEDS_NLL, select  # noqa: E402
from student_common import CONFIG_PATH, MANUAL_DIR, POOL_VERIFIED, load_config, read_jsonl, sha256_file  # noqa: E402

DEFAULT_TOKENS = POOL_VERIFIED.with_name("pool_v1_tokens.jsonl")


def round_dir(run_dir, t):
    return Path(run_dir) / f"round_{t:03d}"


def rel(path):
    resolved = Path(path).resolve()
    return str(resolved.relative_to(MANUAL_DIR)) if resolved.is_relative_to(MANUAL_DIR) else str(resolved)


def write_atomic(path, text):
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def load_tokens(tokens_path, pool_path):
    summary = json.loads(Path(tokens_path).with_suffix(".summary.json").read_text(encoding="utf-8"))
    if summary["pool_sha256"] != sha256_file(pool_path):
        raise ValueError(f"{tokens_path} was built from another pool")
    rows = read_jsonl(tokens_path)
    return {r["trajectory_id"]: r["problem_id"] for r in rows}, {r["trajectory_id"]: r["response_tokens"] for r in rows}


def load_ell(nll_path, tokens):
    """ell by trajectory; the NLL file must cover the pool with the token counts of the budget."""
    rows = read_jsonl(nll_path)
    ell = {r["trajectory_id"]: r["ell"] for r in rows}
    if len(ell) != len(rows) or set(ell) != set(tokens):
        raise ValueError(f"{nll_path} does not cover exactly the eligible pool")
    wrong = [r["trajectory_id"] for r in rows if r["n_tokens"] != tokens[r["trajectory_id"]]]
    if wrong:
        raise ValueError(f"{len(wrong)} token counts in {nll_path} differ from the token table: {wrong[:3]}")
    return ell


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--method", required=True, choices=METHODS)
    ap.add_argument("--seed", required=True, type=int)
    ap.add_argument("--round", required=True, type=int)
    ap.add_argument("--run-dir", required=True, type=Path)
    ap.add_argument("--pool", type=Path, default=POOL_VERIFIED)
    ap.add_argument("--tokens", type=Path, default=DEFAULT_TOKENS)
    ap.add_argument("--nll", type=Path, default=None)
    ap.add_argument("--budget", type=int, default=None, help="pilot only (default: config beta_round_tokens)")
    ap.add_argument("--pilot", action="store_true")
    args = ap.parse_args()

    cfg = load_config()
    if not args.pilot:
        if args.seed not in cfg["seeds"]["training_seeds"] + cfg["seeds"]["optional_extra_seeds"]:
            raise SystemExit(f"seed {args.seed} is not in the config")
        if args.budget is not None:
            raise SystemExit("--budget needs --pilot")
    if not 0 <= args.round < cfg["schedule"]["rounds_M"]:
        raise SystemExit(f"round must be in 0..{cfg['schedule']['rounds_M'] - 1}")
    if args.method in NEEDS_NLL and args.nll is None:
        raise SystemExit(f"{args.method} needs --nll")
    budget = args.budget or cfg["budget"]["beta_round_tokens"]
    n_cap = cfg["selection"]["n_cap"]

    problems, tokens = load_tokens(args.tokens, args.pool)
    trained = []
    for t in range(args.round):
        trained += json.loads((round_dir(args.run_dir, t) / "train_set.json").read_text(encoding="utf-8"))["trajectory_ids"]
    ell = load_ell(args.nll, tokens) if args.method in NEEDS_NLL else None

    res = select(args.method, args.round, args.seed, problems, tokens, budget, n_cap, ell, sorted(set(trained)))

    config_hash = sha256_file(CONFIG_PATH)
    source_t = 0 if args.method == "B4" else args.round  # B4 is ranked at S_0 in every round
    source = cfg["schedule"]["checkpoint_name"].format(t=source_t)
    out_dir = round_dir(args.run_dir, args.round)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_atomic(out_dir / "selection_log.jsonl", "".join(
        json.dumps({"record_type": "selection", "method": args.method, "round": args.round,
                    "source_checkpoint": source, "training_seed": args.seed, **row, "config_hash": config_hash},
                   ensure_ascii=False) + "\n"
        for row in res["rows"]))
    write_atomic(out_dir / "train_set.json", json.dumps({
        "pilot": args.pilot,
        "method": args.method, "round": args.round, "training_seed": args.seed, "source_checkpoint": source,
        "pool": rel(args.pool), "pool_sha256": sha256_file(args.pool),
        "config_sha256": config_hash,
        "nll_file": rel(args.nll) if ell else None,
        "nll_sha256": sha256_file(args.nll) if ell else None,
        "ell_star": res["ell_star"], "sigma": res["sigma"], "n_reference": res["n_reference"],
        "n_eligible": len(problems), "n_trained_before": len(set(trained)),
        "beta_round_tokens": budget, "n_cap": n_cap,
        "tokens_used": res["tokens_used"], "n_selected": len(res["selected"]),
        "trajectory_ids": res["selected"],
    }, ensure_ascii=False, indent=2) + "\n")
    print(f"[{args.method} seed {args.seed} round {args.round}] {len(res['selected'])} trajectories, "
          f"{res['tokens_used']}/{budget} tokens -> {out_dir}")


if __name__ == "__main__":
    main()
