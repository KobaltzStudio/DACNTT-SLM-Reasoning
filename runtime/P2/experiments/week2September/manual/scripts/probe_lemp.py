#!/usr/bin/env python3
"""
Measure L_emp at S_0 (analysis_plan.md section 4, Task.md 2.2) and report the numbers for the I4 decision.

  L_emp(G | S_0) = (Acc_dev(S_0 + train(G)) - Acc_dev(S_0)) / b

G: token-length quintile bins of the eligible pool, 50 trajectories per bin, seed 363636. Each group trains
from S_0 for one epoch (b = 7 steps) with each training seed and is evaluated on D_dev only, never on D_test.

--groups and --seeds run a subset, for the I4 check on 1-2 groups. The report gives per-group changes and
their spread between seeds; it does not decide I4. With all 5 groups it also gives the Spearman correlation
between mean L_proxy per group and mean L_emp; 5 points make this descriptive only (task7_decisions.md).

Needs <runs-dir>/S0/ from run_experiment.py (any method). Resumable like run_experiment.py.

Outputs: <runs-dir>/probe/group_K/{train_set.json,seedS/...}, <runs-dir>/probe/l_emp_report.json

Usage (from experiments/week2September/manual/):
  python scripts/probe_lemp.py --runs-dir runs/main --groups 0 4 --seeds 13 42
  python scripts/probe_lemp.py --runs-dir runs/main
"""
import argparse
import json
import math
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from learnability import score_checkpoint  # noqa: E402
from run_experiment import Runner  # noqa: E402
from select_round import DEFAULT_TOKENS, load_ell, load_tokens, rel  # noqa: E402
from selection import probe_groups  # noqa: E402
from student_common import CONFIG_PATH, POOL_VERIFIED, load_config, sha256_file, write_json  # noqa: E402

SCRIPTS = Path(__file__).resolve().parent
N_GROUPS = 5


def average_ranks(values):
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for k in range(i, j + 1):
            ranks[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return ranks


def spearman(x, y):
    return statistics.correlation(average_ranks(x), average_ranks(y))


def report_groups(groups, scores, s0_acc, acc, b):
    """acc: {(group, seed): accuracy}. One entry per measured group."""
    out = {}
    for g in sorted({key[0] for key in acc}):
        changes = {seed: value - s0_acc for (group, seed), value in acc.items() if group == g}
        values = list(changes.values())
        out[g] = {
            "mean_l_proxy_S0": statistics.mean(scores[t] for t in groups[g]),
            "acc_change_by_seed": {str(s): v for s, v in changes.items()},
            "mean_acc_change": statistics.mean(values),
            "sd_acc_change_between_seeds": statistics.stdev(values) if len(values) > 1 else None,
            "l_emp": statistics.mean(values) / b,
        }
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs-dir", required=True, type=Path)
    ap.add_argument("--groups", type=int, nargs="+", default=list(range(N_GROUPS)))
    ap.add_argument("--seeds", type=int, nargs="+", default=None, help="default: config training seeds")
    ap.add_argument("--backend", default="vllm", choices=["hf", "vllm"])
    ap.add_argument("--micro-batch", type=int, default=8)
    ap.add_argument("--eval-batch", type=int, default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--pilot", action="store_true", help="pipeline test on the pilot pool of --runs-dir")
    ap.add_argument("--pilot-group-size", type=int, default=8)
    ap.add_argument("--pilot-eval-limit", type=int, default=20)
    ap.add_argument("--model", default=None, help="pilot only")
    ap.add_argument("--revision", default=None, help="pilot only")
    ap.add_argument("--dtype", default="auto", choices=["auto", "bf16", "fp32", "fp16"])
    args = ap.parse_args()

    cfg = load_config()
    if args.model and not args.pilot:
        raise SystemExit("--model needs --pilot")
    budget = cfg["budget"]
    b = budget["probe_budget_b_steps"]
    group_size = args.pilot_group_size if args.pilot else budget["probe_group_size"]
    seeds = args.seeds or cfg["seeds"]["training_seeds"]
    runs_dir = args.runs_dir.resolve()
    pool = runs_dir / "pilot_pool.jsonl" if args.pilot else POOL_VERIFIED
    tokens_path = runs_dir / "pilot_tokens.jsonl" if args.pilot else DEFAULT_TOKENS
    s0 = runs_dir / "S0"
    s0_summary = s0 / "eval_dev.summary.json"
    for needed in (s0_summary, s0 / "nll.jsonl"):
        if not needed.exists():
            raise SystemExit(f"{needed} is missing: run run_experiment.py first")

    _, tokens = load_tokens(tokens_path, pool)
    ell = load_ell(s0 / "nll.jsonl", tokens)
    scores = score_checkpoint(ell)["l_proxy"]
    groups = probe_groups(tokens, group_size, cfg["splits"]["split_seed"])

    gpu_args = (["--model", args.model] + (["--revision", args.revision] if args.revision else [])) if args.model else []
    gpu_args += ["--dtype", args.dtype]
    eval_args = ["--backend", args.backend] + gpu_args
    if args.eval_batch:
        eval_args += ["--batch-size", args.eval_batch]
    if args.pilot:
        eval_args += ["--limit", args.pilot_eval_limit]

    runner = Runner(runs_dir, args.dry_run)
    probe_dir = runs_dir / "probe"
    acc = {}
    py = sys.executable
    for g in args.groups:
        group_dir = probe_dir / f"group_{g}"
        group_dir.mkdir(parents=True, exist_ok=True)
        train_set = group_dir / "train_set.json"
        write_json(train_set, {
            "pilot": args.pilot, "purpose": "L_emp probe at S_0", "group": g, "group_rule": budget["l_emp_groups"],
            "pool": rel(pool), "pool_sha256": sha256_file(pool), "config_sha256": sha256_file(CONFIG_PATH),
            "tokens": sum(tokens[t] for t in groups[g]), "trajectory_ids": groups[g],
        })
        for seed in seeds:
            scope = group_dir / f"seed{seed}"
            adapter = scope / "adapter"
            tag = f"probe_g{g}_seed{seed}"
            runner.run(scope, "train", [py, SCRIPTS / "train_round.py", "--seed", seed, "--train-set", train_set,
                                        "--adapter-dir", adapter, "--micro-batch", args.micro_batch, *gpu_args])
            runner.run(scope, "eval_dev", [py, SCRIPTS / "eval_student.py", "--tag", tag, "--split", "dev",
                                           "--out", scope / "eval_dev.jsonl", "--adapter", adapter, *eval_args])
            if args.dry_run:
                continue
            steps = json.loads((adapter / "train_log.json").read_text(encoding="utf-8"))["steps"]
            expected = math.ceil(group_size / cfg["training"]["batch_size"])
            if steps != expected:
                raise RuntimeError(f"{tag}: {steps} training steps, expected {expected}")
            if not args.pilot and steps != b:
                raise RuntimeError(f"{tag}: {steps} training steps differ from config b = {b}")
            acc[(g, seed)] = json.loads((scope / "eval_dev.summary.json").read_text(encoding="utf-8"))["accuracy"]

    if args.dry_run:
        return
    s0_acc = json.loads(s0_summary.read_text(encoding="utf-8"))["accuracy"]
    per_group = report_groups(groups, scores, s0_acc, acc, b)
    report = {
        "pilot": args.pilot, "b_steps": b, "group_size": group_size, "seeds": seeds,
        "acc_dev_S0": s0_acc, "groups": per_group,
        "spearman_mean_l_proxy_vs_l_emp": None,
        "note": "Spearman needs all 5 groups and is descriptive only. Compare mean_acc_change with its spread "
                "between seeds for I4; this script does not decide I4.",
    }
    if len(per_group) == N_GROUPS:
        report["spearman_mean_l_proxy_vs_l_emp"] = spearman([v["mean_l_proxy_S0"] for v in per_group.values()],
                                                            [v["l_emp"] for v in per_group.values()])
    write_json(probe_dir / "l_emp_report.json", report)
    print(json.dumps({"acc_dev_S0": s0_acc, "spearman": report["spearman_mean_l_proxy_vs_l_emp"],
                      "mean_acc_change": {g: round(v["mean_acc_change"], 4) for g, v in per_group.items()}}))


if __name__ == "__main__":
    main()
