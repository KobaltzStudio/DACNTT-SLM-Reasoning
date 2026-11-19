#!/usr/bin/env python3
"""
Smoke test only: sample n_round trajectories uniformly from the verified preliminary pool.

Deviation from the frozen selection rules (recorded in the output): n_cap = 1 is NOT applied,
because the preliminary pool covers only 98 problems (< n_round = 200). The main experiment
keeps n_cap = 1 on the official pool (>= 1000 problems).

Rule: random.Random(training_seed).sample(sorted trajectory_ids, n_round).

Usage (from experiments/week2September/manual/):
  python scripts/select_smoke_train_set.py --seed 13
"""
import argparse
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from student_common import POOL_PRELIMINARY, SMOKE_DIR, load_config, load_pool, sha256_file, write_json  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, required=True, help="training seed from config seeds.training_seeds")
    ap.add_argument("--n", type=int, default=None, help="default: config budget.n_round")
    ap.add_argument("--out", type=Path, default=None, help="default: reports/task5/smoke_test/train_set_seed<seed>.json")
    args = ap.parse_args()

    cfg = load_config()
    if args.seed not in cfg["seeds"]["training_seeds"]:
        raise ValueError(f"seed {args.seed} is not in config seeds.training_seeds")
    n = args.n or cfg["budget"]["n_round"]
    pool = load_pool(POOL_PRELIMINARY)  # the smoke test is fixed to the preliminary pool
    ids = sorted(r["trajectory_id"] for r in pool)
    chosen = sorted(random.Random(args.seed).sample(ids, n))

    by_id = {r["trajectory_id"]: r for r in pool}
    per_problem = Counter(by_id[t]["problem_id"] for t in chosen)
    out = args.out or SMOKE_DIR / f"train_set_seed{args.seed}.json"
    write_json(out, {
        "purpose": "Task 5 smoke test (S_0 -> S_1 on D_dev); not a main-experiment selection",
        "rule": "random.Random(seed).sample(sorted(trajectory_id), n)",
        "seed": args.seed,
        "n": n,
        "pool": str(POOL_PRELIMINARY.relative_to(POOL_PRELIMINARY.parents[2])),
        "pool_sha256": sha256_file(POOL_PRELIMINARY),
        "pool_size": len(ids),
        "deviation": "n_cap not applied (preliminary pool has 98 problems < n_round)",
        "n_problems_covered": len(per_problem),
        "max_trajectories_per_problem": max(per_problem.values()),
        "teacher_token_length_sum": sum(by_id[t]["metadata"]["token_length"] for t in chosen),
        "trajectory_ids": chosen,
    })
    print(f"seed {args.seed}: {n} trajectories over {len(per_problem)} problems "
          f"(max {max(per_problem.values())} per problem) -> {out}")


if __name__ == "__main__":
    main()
