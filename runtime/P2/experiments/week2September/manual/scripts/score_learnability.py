#!/usr/bin/env python3
"""
Write L_proxy next to every NLL file of a runs directory, with the band parameters of that checkpoint.
No GPU, no torch; re-run at any time (outputs are overwritten).

For S_t of a run, the reference set excludes the trajectories trained in that run before S_t (T7-3); at
the shared S_0 nothing is excluded. This is the same computation the selector does for B5, and it adds the
checkpoints the selector never scores (B4 at S_1 and S_2, needed for the H test and epsilon).

Outputs, next to each nll.jsonl:
  learnability.jsonl          trajectory_id, problem_id, n_tokens, ell, l_proxy, in_reference
  learnability.summary.json   checkpoint, run, NLL hash, n_scored, n_reference, ell_star, q1, q3, sigma,
                              quantile method, mean/median/sd of ell and of L_proxy

Quartiles: statistics.quantiles(n=4), method "exclusive", as learnability.py and the Task 5 smoke analysis.
The method changes sigma slightly but never the ranking (L_proxy order depends only on |ell - ell*|).

Usage (from experiments/week2September/manual/):
  python scripts/score_learnability.py runs/main
"""
import argparse
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from learnability import score_checkpoint  # noqa: E402
from run_layout import discover  # noqa: E402
from student_common import read_jsonl, sha256_file, write_json  # noqa: E402


def describe(values):
    return {"mean": statistics.mean(values), "median": statistics.median(values), "sd": statistics.stdev(values)}


def score_file(nll_path, checkpoint, run_name, trained):
    rows = read_jsonl(nll_path)
    ell = {r["trajectory_id"]: r["ell"] for r in rows}
    if len(ell) != len(rows):
        raise ValueError(f"duplicate trajectory ids in {nll_path}")
    res = score_checkpoint(ell, sorted(trained))
    reference = [v for k, v in ell.items() if k not in trained]
    q = statistics.quantiles(reference, n=4)
    out_rows = [{"trajectory_id": r["trajectory_id"], "problem_id": r["problem_id"], "n_tokens": r["n_tokens"],
                 "ell": r["ell"], "l_proxy": res["l_proxy"][r["trajectory_id"]],
                 "in_reference": r["trajectory_id"] not in trained} for r in rows]
    out = nll_path.with_name("learnability.jsonl")
    out.write_text("".join(json.dumps(r) + "\n" for r in out_rows), encoding="utf-8")
    summary = {
        "checkpoint": checkpoint, "run": run_name, "nll_file": str(nll_path), "nll_sha256": sha256_file(nll_path),
        "n_scored": len(out_rows), "n_reference": res["n_reference"], "n_trained_excluded": len(trained),
        "ell_star": res["ell_star"], "q1": q[0], "q3": q[2], "sigma": res["sigma"],
        "quantile_method": "statistics.quantiles(n=4), exclusive",
        "ell": describe(list(ell.values())), "l_proxy": describe([r["l_proxy"] for r in out_rows]),
    }
    write_json(out.with_suffix(".summary.json"), summary)
    return summary


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs_dir", type=Path)
    args = ap.parse_args()

    done = []
    s0 = args.runs_dir / "S0" / "nll.jsonl"
    if s0.exists():
        done.append(score_file(s0, "student_ckpt_000", "S0", set()))
    for run in discover(args.runs_dir):
        trained = set()
        for t in run.rounds():
            trained |= set(run.train_set(t)["trajectory_ids"])
            nll = run.path / f"S{t + 1}" / "nll.jsonl"
            if nll.exists():
                done.append(score_file(nll, f"student_ckpt_{t + 1:03d}", run.name, set(trained)))
    for s in done:
        print(f"{s['run']:<14} {s['checkpoint']}  ref {s['n_reference']:>5}  ell* {s['ell_star']:.4f}  "
              f"sigma {s['sigma']:.4f}  mean L_proxy {s['l_proxy']['mean']:.3f}")
    if not done:
        print(f"no nll.jsonl found under {args.runs_dir}")


if __name__ == "__main__":
    main()
