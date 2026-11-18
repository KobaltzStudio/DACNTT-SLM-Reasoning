#!/usr/bin/env python3
"""
Token table of a verified pool under the Student tokenizer: the unit of the selection budget.

response_tokens = tokens of raw_generation.strip() without the end-of-turn token (same count as L_bar and
as n_tokens in compute_nll.py; select_round.py checks that the two agree).

Outputs:
  --out                  one JSON line per trajectory: trajectory_id, problem_id, response_tokens
  <out>.summary.json     pool SHA-256, tokenizer, totals

Usage (from experiments/week2September/manual/):
  python scripts/build_pool_tokens.py
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from student_common import (  # noqa: E402
    POOL_VERIFIED, add_model_args, encode_example, load_config, load_pool, load_tokenizer, sha256_file,
    student_from_args, write_json,
)

DEFAULT_OUT = POOL_VERIFIED.with_name("pool_v1_tokens.jsonl")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pool", type=Path, default=POOL_VERIFIED)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    add_model_args(ap)
    args = ap.parse_args()

    cfg = load_config()
    model_name, revision = student_from_args(args, cfg)
    tok = load_tokenizer(model_name, revision)
    pool = sorted(load_pool(args.pool), key=lambda r: r["trajectory_id"])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    with args.out.open("w", encoding="utf-8") as f:
        for r in pool:
            n = encode_example(tok, r["question"], r["raw_generation"], add_eos=False)["n_traj"]
            total += n
            f.write(json.dumps({"trajectory_id": r["trajectory_id"], "problem_id": r["problem_id"],
                                "response_tokens": n}) + "\n")
    write_json(args.out.with_suffix(".summary.json"), {
        "pool": str(args.pool), "pool_sha256": sha256_file(args.pool),
        "tokenizer": model_name, "tokenizer_revision": revision,
        "n_trajectories": len(pool), "response_tokens_sum": total,
    })
    print(f"{len(pool)} trajectories, {total} response tokens -> {args.out}")


if __name__ == "__main__":
    main()
