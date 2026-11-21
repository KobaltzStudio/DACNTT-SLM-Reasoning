#!/usr/bin/env python3
"""
Independent check of a finished (or partly finished) runs directory, after the fact. No GPU, no torch
unless --retokenize. It re-derives everything from the files on disk instead of trusting the selector:

per round (round_NNN/train_set.json)
  pool and config hashes match the files; trajectory ids unique and in the pool; every problem in D_pool
  and none in D_dev/D_test; n_cap; token total recomputed from the token table (and, with --retokenize,
  from the Student tokenizer) equals tokens_used and stays within the budget; the budget is the frozen
  beta_round (main runs); selection_log selected ids = train set; source checkpoint (B4: S_0, B5: S_t);
  the NLL file named in the train set still has its recorded hash
per training round (S<t+1>/adapter/train_log.json)
  n_examples = n_selected; trajectory_tokens = tokens_used; cumulative_training_tokens = tokens_used +
  n_selected (one <|im_end|> per example, T7-9a); checkpoint lineage (round 0 from S_0, round t from S_t)
per run
  B3/B4 never repeat a trajectory across rounds (T7-1, T7-2); evaluations complete
across runs
  B4 and B5 of the same seed select the same B_0
optional
  --compare RUN:ROUND=FILE   ids of another implementation's train set (JSON with "trajectory_ids", or a
                             selection log with "selected" records) against this run's round

Usage (from experiments/week2September/manual/):
  python scripts/validate_runs.py runs/main
  python scripts/validate_runs.py runs/main --retokenize --out reports/task7/validation_main.json
  python scripts/validate_runs.py runs/main --compare B4_seed13:0=../nghi/B4_seed13_round0_train_set.json
Exit code 1 when any check fails.
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_layout import Run, discover, load_eval  # noqa: E402
from select_round import DEFAULT_TOKENS  # noqa: E402
from student_common import (  # noqa: E402
    CONFIG_PATH, DEV_IDS, MANUAL_DIR, POOL_VERIFIED, TEST_IDS, load_config, read_jsonl, sha256_file,
)

POOL_IDS = MANUAL_DIR / "splits" / "d_pool_ids.txt"
EXPECTED_EVAL = {"dev": 500, "test": 1319}


class Report:
    def __init__(self):
        self.checks = []

    def add(self, scope, name, ok, detail=""):
        self.checks.append({"scope": scope, "check": name, "ok": bool(ok), "detail": detail})

    @property
    def failed(self):
        return [c for c in self.checks if not c["ok"]]


def read_ids(path):
    return set(Path(path).read_text(encoding="utf-8").split())


def resolve(path):
    p = Path(path)
    return p if p.is_absolute() else MANUAL_DIR / p


def token_table(pool_path):
    """{trajectory_id: response_tokens} of the token table that belongs to pool_path, or None."""
    candidates = [DEFAULT_TOKENS] if pool_path.resolve() == POOL_VERIFIED.resolve() else []
    candidates.append(pool_path.with_name("pilot_tokens.jsonl"))
    for tokens in candidates:
        summary = tokens.with_suffix(".summary.json")
        if tokens.exists() and summary.exists():
            if json.loads(summary.read_text(encoding="utf-8"))["pool_sha256"] == sha256_file(pool_path):
                return {r["trajectory_id"]: r["response_tokens"] for r in read_jsonl(tokens)}
    return None


class Retokenizer:
    """Counts trajectory tokens with the Student tokenizer, as the budget does (no <|im_end|>)."""

    def __init__(self):
        from student_common import encode_example, load_tokenizer
        cfg = load_config()
        self.encode = encode_example
        self.tok = load_tokenizer(cfg["student"]["model"], cfg["student"]["revision"])

    def count(self, row):
        return self.encode(self.tok, row["question"], row["raw_generation"], add_eos=False)["n_traj"]


def ids_from_file(path):
    path = Path(path)
    if path.suffix == ".jsonl":
        return [r["trajectory_id"] for r in read_jsonl(path) if r.get("selected")]
    data = json.loads(path.read_text(encoding="utf-8"))
    return list(data["trajectory_ids"])


def check_round(rep, run, t, ts, ctx):
    scope = f"{run.name}/round_{t:03d}"
    pool_path = resolve(ts["pool"])
    pool_sha = ctx["sha"].setdefault(pool_path, sha256_file(pool_path))
    rep.add(scope, "pool_sha256", ts["pool_sha256"] == pool_sha, ts["pool"])
    rep.add(scope, "config_sha256", ts["config_sha256"] == ctx["config_sha"],
            "" if ts["config_sha256"] == ctx["config_sha"] else f"run {ts['config_sha256'][:12]} vs now {ctx['config_sha'][:12]}")
    pool = ctx["pools"].setdefault(pool_path, {r["trajectory_id"]: r for r in read_jsonl(pool_path)})

    ids = ts["trajectory_ids"]
    rep.add(scope, "ids_unique", len(ids) == len(set(ids)))
    rep.add(scope, "n_selected", ts["n_selected"] == len(ids), f"{ts['n_selected']} vs {len(ids)}")
    missing = [x for x in ids if x not in pool]
    rep.add(scope, "ids_in_pool", not missing, ", ".join(missing[:3]))
    problems = [pool[x]["problem_id"] for x in ids if x in pool]
    outside = sorted(set(problems) - ctx["pool_ids"])
    leaked = sorted(set(problems) & ctx["held_out"])
    rep.add(scope, "problems_in_D_pool", not outside, ", ".join(outside[:3]))
    rep.add(scope, "no_D_dev_D_test", not leaked, ", ".join(leaked[:3]))
    per_problem = max(Counter(problems).values(), default=0)
    rep.add(scope, "n_cap", per_problem <= ts["n_cap"] == ctx["n_cap"], f"max {per_problem} per problem, n_cap {ts['n_cap']}")

    table = ctx["tables"].setdefault(pool_path, token_table(pool_path))
    if table is None:
        rep.add(scope, "tokens_table", False, f"no token table for {ts['pool']} (use --retokenize)")
    else:
        total = sum(table[x] for x in ids if x in table)
        rep.add(scope, "tokens_used", total == ts["tokens_used"], f"recomputed {total}, stored {ts['tokens_used']}")
    if ctx["retok"]:
        total = sum(ctx["retok"].count(pool[x]) for x in ids if x in pool)
        rep.add(scope, "tokens_retokenized", total == ts["tokens_used"], f"tokenizer {total}, stored {ts['tokens_used']}")
    rep.add(scope, "within_budget", ts["tokens_used"] <= ts["beta_round_tokens"], f"{ts['tokens_used']}/{ts['beta_round_tokens']}")
    if not ts.get("pilot"):
        rep.add(scope, "budget_is_frozen_value", ts["beta_round_tokens"] == ctx["beta_round"],
                f"{ts['beta_round_tokens']} vs config {ctx['beta_round']}")

    log = run.selection_log(t)
    if log is None:
        rep.add(scope, "selection_log", False, "missing")
    else:
        selected = sorted(r["trajectory_id"] for r in log if r.get("selected"))
        rep.add(scope, "selection_log_matches", selected == sorted(ids), f"{len(selected)} selected records")

    expected_source = "student_ckpt_000" if run.method == "B4" else f"student_ckpt_{t:03d}"
    if run.method in ("B4", "B5"):
        rep.add(scope, "source_checkpoint", ts["source_checkpoint"] == expected_source, ts["source_checkpoint"])
    if ts.get("nll_file"):
        nll = resolve(ts["nll_file"])
        ok = nll.exists() and sha256_file(nll) == ts["nll_sha256"]
        rep.add(scope, "nll_sha256", ok, ts["nll_file"])

    log_t = run.train_log(t)
    if log_t is None:
        rep.add(scope, "train_log", False, f"S{t + 1}/adapter/train_log.json missing (round not trained yet?)")
        return
    n = len(ids)
    rep.add(scope, "train_n_examples", log_t["n_examples"] == n, f"{log_t['n_examples']} vs {n}")
    rep.add(scope, "train_trajectory_tokens", log_t["trajectory_tokens"] == ts["tokens_used"],
            f"{log_t['trajectory_tokens']} vs {ts['tokens_used']}")
    rep.add(scope, "train_supervised_tokens", log_t["cumulative_training_tokens"] == ts["tokens_used"] + n,
            f"{log_t['cumulative_training_tokens']} = {ts['tokens_used']} + {n} <|im_end|>")
    parent = str(log_t["checkpoint_parent"])
    ok = parent == "student_ckpt_000" if t == 0 else parent.rstrip("/").endswith(f"S{t}/adapter")
    rep.add(scope, "lineage", ok, parent)
    rep.add(scope, "train_pool_sha256", log_t["pool_sha256"] == pool_sha)


def check_run(rep, run, runs_dir, ctx):
    rounds = run.rounds()
    rep.add(run.name, "rounds_present", len(rounds) == ctx["rounds_M"], f"{len(rounds)}/{ctx['rounds_M']}")
    sets = []
    for t in rounds:
        ts = run.train_set(t)
        sets.append(ts["trajectory_ids"])
        check_round(rep, run, t, ts, ctx)
    if run.method in ("B3", "B4"):
        all_ids = [x for s in sets for x in s]
        rep.add(run.name, "no_repeat_across_rounds", len(all_ids) == len(set(all_ids)),
                f"{len(all_ids) - len(set(all_ids))} repeats")
    for t in range(1, len(rounds) + 1):
        for split in ("dev", "test"):
            rows, summary = load_eval(run.checkpoint_dir(t, runs_dir), split)
            scope = f"{run.name}/S{t}"
            if rows is None:
                rep.add(scope, f"eval_{split}", False, "missing")
                continue
            ok = summary["n_problems"] == len(rows) == len({r["problem_id"] for r in rows})
            if not summary.get("limit"):
                ok = ok and len(rows) == EXPECTED_EVAL[split]
            rep.add(scope, f"eval_{split}", ok, f"{len(rows)} problems, accuracy {summary['accuracy']:.4f}")
    return sets


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs_dir", type=Path)
    ap.add_argument("--retokenize", action="store_true", help="also recount tokens with the Student tokenizer")
    ap.add_argument("--compare", action="append", default=[], metavar="RUN:ROUND=FILE")
    ap.add_argument("--out", type=Path, help="write the full report as JSON")
    args = ap.parse_args()

    cfg = load_config()
    ctx = {
        "config_sha": sha256_file(CONFIG_PATH), "beta_round": cfg["budget"]["beta_round_tokens"],
        "n_cap": cfg["selection"]["n_cap"], "rounds_M": cfg["schedule"]["rounds_M"],
        "pool_ids": read_ids(POOL_IDS), "held_out": read_ids(DEV_IDS) | read_ids(TEST_IDS),
        "sha": {}, "pools": {}, "tables": {}, "retok": Retokenizer() if args.retokenize else None,
    }
    rep = Report()
    for split in ("dev", "test"):
        rows, summary = load_eval(args.runs_dir / "S0", split)
        rep.add("S0", f"eval_{split}", rows is not None, "" if rows is None else f"accuracy {summary['accuracy']:.4f}")
    rep.add("S0", "nll", (args.runs_dir / "S0" / "nll.jsonl").exists())

    runs = discover(args.runs_dir)
    sets = {run.name: check_run(rep, run, args.runs_dir, ctx) for run in runs}
    for run in runs:
        if run.method == "B4" and f"B5_seed{run.seed}" in sets:
            a, b = sets[run.name], sets[f"B5_seed{run.seed}"]
            if a and b:
                rep.add(f"seed{run.seed}", "B4_B5_same_B0", a[0] == b[0], f"{len(a[0])} vs {len(b[0])} trajectories")

    for spec in args.compare:
        target, path = spec.split("=", 1)
        name, t = target.rsplit(":", 1)
        mine = Run(args.runs_dir / name).train_set(int(t))["trajectory_ids"]
        other = ids_from_file(path)
        detail = (f"identical ({len(mine)} trajectories)" if sorted(mine) == sorted(other) else
                  f"this {len(mine)}, other {len(other)}, common {len(set(mine) & set(other))}")
        rep.add(f"compare {target}", "same_selection", sorted(mine) == sorted(other), detail)

    width = max((len(c["scope"]) for c in rep.checks), default=10)
    for c in rep.checks:
        if not c["ok"] or c["check"] in ("same_selection", "B4_B5_same_B0", "rounds_present"):
            print(f"{'PASS' if c['ok'] else 'FAIL'}  {c['scope']:<{width}}  {c['check']:<26} {c['detail']}")
    print(f"\n{len(rep.checks) - len(rep.failed)}/{len(rep.checks)} checks passed over {len(runs)} runs")
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps({"runs_dir": str(args.runs_dir), "checks": rep.checks}, indent=2) + "\n",
                            encoding="utf-8")
    sys.exit(1 if rep.failed else 0)


if __name__ == "__main__":
    main()
