#!/usr/bin/env python3
"""
Run one method and one training seed through the Task 7 schedule (analysis_plan.md section 3).

  S_0 (shared by all runs): eval D_dev, eval D_test, NLL of the pool
  t = 0..M-1: select B_t -> train S_t + B_t -> S_{t+1} -> eval D_dev, eval D_test -> NLL when needed

NLL per method: B4, B5 and the ablation at S_1 and S_2 (selection and/or T7-6, T7-7); B2 too when
--b2-nll is given (sensitivity analysis of T7-7); B0 and B3 never beyond S_0. S_3 is never scored.

Each step is one subprocess, so GPU memory is released between steps. A finished step leaves a marker in
<run-dir>/.done/ with its command and duration; re-running the same command skips finished steps and redoes
the interrupted one (eval_student.py also resumes inside a step). Durations are appended to
<runs-dir>/timing.jsonl, which is what the cost estimate of the main run comes from.

B4 and B5 select the same B_0 at S_0, so with the same seed S_1 is shared (task7_decisions.md): when the
other method's round 0 is finished and its trajectory list is identical, its adapter, evaluations and NLL
are copied, and the marker records the source.

Layout:
  <runs-dir>/S0/{eval_dev,eval_test,nll}.jsonl
  <runs-dir>/<method>_seed<seed>/round_NNN/{train_set.json,selection_log.jsonl}
  <runs-dir>/<method>_seed<seed>/S<t>/{adapter/,eval_dev.jsonl,eval_test.jsonl,nll.jsonl}
  <runs-dir>/<method>_seed<seed>/checkpoint_log.jsonl

--pilot is for testing the pipeline only: --pilot-problems builds a small pool from the first problems of the
official pool, with a smaller budget and evaluation limit. Keep --runs-dir apart from the main runs.

Usage (from experiments/week2September/manual/):
  python scripts/run_experiment.py --method B5 --seed 13 --runs-dir runs/main
  python scripts/run_experiment.py --method B5 --seed 13 --runs-dir runs/main --dry-run
"""
import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from selection import METHODS as SELECTION_METHODS  # noqa: E402
from select_round import DEFAULT_TOKENS, round_dir  # noqa: E402
from student_common import CONFIG_PATH, POOL_VERIFIED, load_config, read_jsonl, sha256_file  # noqa: E402

SCRIPTS = Path(__file__).resolve().parent
METHODS = ("B0",) + SELECTION_METHODS
SHARED_ROUND0 = {"B4": "B5", "B5": "B4"}


class Runner:
    """Runs steps once, keeps markers and timing."""

    def __init__(self, runs_dir, dry_run=False):
        self.runs_dir = Path(runs_dir)
        self.dry_run = dry_run

    def marker(self, scope_dir, step):
        return Path(scope_dir) / ".done" / f"{step}.json"

    def is_done(self, scope_dir, step):
        return self.marker(scope_dir, step).exists()

    def mark(self, scope_dir, step, info):
        path = self.marker(scope_dir, step)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def run(self, scope_dir, step, cmd):
        printable = " ".join(shlex.quote(str(c)) for c in cmd)
        if self.is_done(scope_dir, step):
            print(f"[skip] {scope_dir}/{step}")
            return
        print(f"[run] {scope_dir}/{step}\n      {printable}", flush=True)
        if self.dry_run:
            return
        t0 = time.time()
        subprocess.run([str(c) for c in cmd], check=True)
        elapsed = round(time.time() - t0, 1)
        self.mark(scope_dir, step, {"command": printable, "elapsed_seconds": elapsed})
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        with (self.runs_dir / "timing.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps({"scope": str(scope_dir), "step": step, "elapsed_seconds": elapsed}) + "\n")


def needs_nll_at(method, t, b2_nll):
    """NLL at S_{t}, t >= 1 (S_0 is always scored in the shared directory)."""
    if t not in (1, 2):
        return False
    return method in ("B4", "B5", "ablation_shuffled_scores") or (method == "B2" and b2_nll)


def build_pilot_pool(args, runs_dir, model_args):
    """Pool of the first problems of the official pool, and its token table."""
    pool_path = runs_dir / "pilot_pool.jsonl"
    tokens_path = runs_dir / "pilot_tokens.jsonl"
    if args.dry_run or tokens_path.with_suffix(".summary.json").exists():
        return pool_path, tokens_path
    runs_dir.mkdir(parents=True, exist_ok=True)
    keep, lines = set(), []
    with POOL_VERIFIED.open(encoding="utf-8") as f:
        for line in f:
            pid = json.loads(line)["problem_id"]
            if pid not in keep and len(keep) == args.pilot_problems:
                break
            keep.add(pid)
            lines.append(line)
    pool_path.write_text("".join(lines), encoding="utf-8")
    subprocess.run([sys.executable, SCRIPTS / "build_pool_tokens.py", "--pool", pool_path, "--out", tokens_path,
                    *model_args], check=True)
    return pool_path, tokens_path


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--method", required=True, choices=METHODS)
    ap.add_argument("--seed", required=True, type=int)
    ap.add_argument("--runs-dir", required=True, type=Path)
    ap.add_argument("--backend", default="vllm", choices=["hf", "vllm"], help="evaluation backend")
    ap.add_argument("--eval-batch", type=int, default=None)
    ap.add_argument("--nll-batch", type=int, default=16)
    ap.add_argument("--micro-batch", type=int, default=8)
    ap.add_argument("--b2-nll", action="store_true", help="score S_1, S_2 for B2 too (T7-7 sensitivity)")
    ap.add_argument("--dry-run", action="store_true", help="print the steps without running them")
    ap.add_argument("--pilot", action="store_true")
    ap.add_argument("--pilot-problems", type=int, default=60)
    ap.add_argument("--pilot-budget", type=int, default=2000)
    ap.add_argument("--pilot-eval-limit", type=int, default=20)
    ap.add_argument("--model", default=None, help="pilot only")
    ap.add_argument("--revision", default=None, help="pilot only")
    ap.add_argument("--dtype", default="auto", choices=["auto", "bf16", "fp32", "fp16"])
    args = ap.parse_args()

    cfg = load_config()
    if not args.pilot:
        if args.model:
            raise SystemExit("--model needs --pilot")
        if args.seed not in cfg["seeds"]["training_seeds"] + cfg["seeds"]["optional_extra_seeds"]:
            raise SystemExit(f"seed {args.seed} is not in the config")

    runs_dir = args.runs_dir.resolve()
    model_args = (["--model", args.model] + (["--revision", args.revision] if args.revision else [])) if args.model else []
    gpu_args = model_args + ["--dtype", args.dtype]
    eval_args = ["--backend", args.backend] + gpu_args
    if args.eval_batch:
        eval_args += ["--batch-size", args.eval_batch]
    select_args = []
    pool, tokens = POOL_VERIFIED, DEFAULT_TOKENS
    if args.pilot:
        pool, tokens = build_pilot_pool(args, runs_dir, model_args)
        eval_args += ["--limit", args.pilot_eval_limit]
        select_args = ["--pilot", "--budget", args.pilot_budget]
    elif not args.dry_run and not tokens.exists():
        raise SystemExit(f"{tokens} is missing: run scripts/build_pool_tokens.py first")

    runner = Runner(runs_dir, args.dry_run)
    py = sys.executable
    tag_run = f"{args.method}_seed{args.seed}"
    run_dir = runs_dir / tag_run
    s0 = runs_dir / "S0"
    n_pool = 0 if args.dry_run else len(read_jsonl(tokens))
    M = cfg["schedule"]["rounds_M"]
    ckpt = cfg["schedule"]["checkpoint_name"]
    config_hash = sha256_file(CONFIG_PATH)

    def evaluate(scope, ckpt_dir, tag, adapter):
        for split in ("dev", "test"):
            cmd = [py, SCRIPTS / "eval_student.py", "--tag", tag, "--split", split,
                   "--out", ckpt_dir / f"eval_{split}.jsonl", *eval_args]
            runner.run(scope, f"eval_{split}_{tag}", cmd + (["--adapter", adapter] if adapter else []))

    def score(scope, ckpt_dir, tag, adapter):
        cmd = [py, SCRIPTS / "compute_nll.py", "--tag", tag, "--out", ckpt_dir / "nll.jsonl", "--pool", pool,
               "--batch-size", args.nll_batch, *gpu_args]
        runner.run(scope, f"nll_{tag}", cmd + (["--adapter", adapter] if adapter else []))

    evaluate(s0, s0, "S0", None)
    score(s0, s0, "S0", None)

    if args.method == "B0":
        print("B0 is S_0 itself: nothing to train.")
        return

    def write_checkpoint_record(t, selected, parent, cumulative_tokens, cumulative_steps):
        row = {"record_type": "checkpoint", "checkpoint": ckpt.format(t=t), "parent_checkpoint": parent,
               "round": t, "method": args.method, "training_seed": args.seed, "data_order_seed": args.seed,
               "cumulative_training_tokens": cumulative_tokens, "cumulative_optimization_steps": cumulative_steps,
               "selected_trajectory_ids": selected,
               "beta_est_forward_passes": n_pool if t == 0 or needs_nll_at(args.method, t, args.b2_nll) else 0,
               "config_hash": config_hash}
        rows = [r for r in read_jsonl(log_path) if r["checkpoint"] != row["checkpoint"]] if log_path.exists() else []
        log_path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows + [row]), encoding="utf-8")

    log_path = run_dir / "checkpoint_log.jsonl"
    if not args.dry_run:
        run_dir.mkdir(parents=True, exist_ok=True)
        write_checkpoint_record(0, [], None, 0, 0)

    def try_reuse_round0():
        """Copy S_1 from the other of B4/B5 when its B_0 is identical. True when copied."""
        other = SHARED_ROUND0.get(args.method)
        if other is None or runner.is_done(run_dir, "train_0"):
            return False
        other_dir = runs_dir / f"{other}_seed{args.seed}"
        other_tag = f"{other}_seed{args.seed}_S1"
        steps = ["train_0", f"eval_dev_{other_tag}", f"eval_test_{other_tag}", f"nll_{other_tag}"]
        if not all(runner.is_done(other_dir, s) for s in steps):
            return False
        own = json.loads((round_dir(run_dir, 0) / "train_set.json").read_text(encoding="utf-8"))
        theirs = json.loads((round_dir(other_dir, 0) / "train_set.json").read_text(encoding="utf-8"))
        if own["trajectory_ids"] != theirs["trajectory_ids"]:
            raise RuntimeError(f"{args.method} and {other} differ at round 0: the shared S_1 assumption fails")
        shutil.copytree(other_dir / "S1", run_dir / "S1", dirs_exist_ok=True)
        tag = f"{tag_run}_S1"
        info = {"reused_from": str(other_dir / "S1"), "reason": "identical B_0 and seed (task7_decisions.md)"}
        for step in ("train_0", f"eval_dev_{tag}", f"eval_test_{tag}", f"nll_{tag}"):
            runner.mark(run_dir, step, info)
        print(f"[reuse] S_1 of {tag_run} copied from {other_dir.name}")
        return True

    cumulative_tokens, cumulative_steps = 0, 0
    for t in range(M):
        nll = s0 / "nll.jsonl" if t == 0 or args.method == "B4" else run_dir / f"S{t}" / "nll.jsonl"
        cmd = [py, SCRIPTS / "select_round.py", "--method", args.method, "--seed", args.seed, "--round", t,
               "--run-dir", run_dir, "--pool", pool, "--tokens", tokens, *select_args]
        if args.method in ("B4", "B5", "ablation_shuffled_scores"):
            cmd += ["--nll", nll]
        runner.run(run_dir, f"select_{t}", cmd)
        runner.run(run_dir, f"validate_log_{t}",
                   [sys.executable, "-c",
                    "import subprocess,sys;r=subprocess.run([sys.executable,sys.argv[1],sys.argv[2]],"
                    "capture_output=True,text=True);print(r.stdout.splitlines()[-1]);sys.exit(r.returncode)",
                    SCRIPTS / "validate_selection_log.py", round_dir(run_dir, t) / "selection_log.jsonl"])

        ckpt_dir = run_dir / f"S{t + 1}"
        adapter = ckpt_dir / "adapter"
        tag = f"{tag_run}_S{t + 1}"
        if not args.dry_run and t == 0:
            try_reuse_round0()
        train_cmd = [py, SCRIPTS / "train_round.py", "--seed", args.seed,
                     "--train-set", round_dir(run_dir, t) / "train_set.json", "--adapter-dir", adapter,
                     "--micro-batch", args.micro_batch, *gpu_args]
        if t > 0:
            train_cmd += ["--init-adapter", run_dir / f"S{t}" / "adapter"]
        runner.run(run_dir, f"train_{t}", train_cmd)
        evaluate(run_dir, ckpt_dir, tag, adapter)
        if needs_nll_at(args.method, t + 1, args.b2_nll):
            score(run_dir, ckpt_dir, tag, adapter)

        if not args.dry_run:
            train_log = json.loads((adapter / "train_log.json").read_text(encoding="utf-8"))
            cumulative_tokens += train_log["cumulative_training_tokens"]
            cumulative_steps += train_log["steps"]
            selected = json.loads((round_dir(run_dir, t) / "train_set.json").read_text(encoding="utf-8"))["trajectory_ids"]
            write_checkpoint_record(t + 1, selected, ckpt.format(t=t), cumulative_tokens, cumulative_steps)

    print(f"{tag_run} finished -> {run_dir}")


if __name__ == "__main__":
    os.chdir(SCRIPTS.parent)
    main()
