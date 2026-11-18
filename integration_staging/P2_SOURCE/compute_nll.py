#!/usr/bin/env python3
"""
Score every verified pool trajectory under a Student checkpoint (one forward pass, no backward).

Per trajectory tau (trajectory tokens only, the end-of-turn token excluded):
  nll_sum    = sum_t -log p(tau_t | x, tau_<t)
  ell        = nll_sum / n_tokens            (length-normalized NLL; input of L_proxy, config "learnability")
  brier_sum  = sum_t || pi_t - onehot(tau_t) ||^2
               (Brier residual; stored so the LARK score, arXiv 2605.30651 Eq. 7, can be computed
                later without another pass. Exploratory, not part of the frozen L_proxy.)

L_proxy itself is not computed here: it needs ell over the whole pool (median / IQR rule) and
is derived in the analysis step.

--pool defaults to the official pool v1 (trajectory/pool/pool_v1_verified.jsonl). The Task 5 smoke test
scored the preliminary pool; reproduce it with --pool trajectory/pool/batch_100_teacher_verified.jsonl.

Usage (from experiments/week2September/manual/):
  python scripts/compute_nll.py --tag S0 --out reports/task5/smoke_test/nll_pool_S0.jsonl \
      --pool trajectory/pool/batch_100_teacher_verified.jsonl
  python scripts/compute_nll.py --tag S1_seed13 --adapter <adapter_dir> \
      --out reports/task5/smoke_test/nll_pool_S1_seed13.jsonl --pool trajectory/pool/batch_100_teacher_verified.jsonl
"""
import argparse
import json
import sys
import time
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from student_common import (  # noqa: E402
    IGNORE_INDEX, POOL_VERIFIED, add_model_args, check_prompt_template, encode_example, environment_info,
    load_config, load_model, load_pool, load_tokenizer, pick_dtype, sha256_file, student_from_args, write_json,
)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tag", required=True)
    ap.add_argument("--adapter", default=None)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--batch-size", type=int, default=4)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--pool", type=Path, default=POOL_VERIFIED, help="verified pool to score (default: pool v1)")
    add_model_args(ap)
    args = ap.parse_args()

    check_prompt_template()
    cfg = load_config()
    model_name, revision = student_from_args(args, cfg)
    dtype = pick_dtype(torch, args.dtype)
    pool = sorted(load_pool(args.pool), key=lambda r: r["trajectory_id"])
    if args.limit:
        pool = pool[: args.limit]

    tok = load_tokenizer(model_name, revision)
    model = load_model(model_name, revision, dtype, adapter=args.adapter)
    examples = [encode_example(tok, r["question"], r["raw_generation"], add_eos=False) for r in pool]

    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
    t0 = time.time()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as f:
        for i in range(0, len(examples), args.batch_size):
            batch = examples[i: i + args.batch_size]
            width = max(len(e["input_ids"]) for e in batch)
            ids = torch.tensor([e["input_ids"] + [tok.pad_token_id] * (width - len(e["input_ids"])) for e in batch])
            mask = torch.tensor([[1] * len(e["input_ids"]) + [0] * (width - len(e["input_ids"])) for e in batch])
            labels = torch.tensor([e["labels"] + [IGNORE_INDEX] * (width - len(e["labels"])) for e in batch])
            ids, mask, labels = ids.to(model.device), mask.to(model.device), labels.to(model.device)
            with torch.no_grad():
                logits = model(input_ids=ids, attention_mask=mask).logits[:, :-1]
            tgt = labels[:, 1:]
            for b, e in enumerate(batch):
                sel = tgt[b] != IGNORE_INDEX
                lp = torch.log_softmax(logits[b][sel].float(), dim=-1)
                y = tgt[b][sel]
                lp_y = lp.gather(1, y[:, None]).squeeze(1)
                p = lp.exp()
                brier = (p.pow(2).sum(-1) - 2 * lp_y.exp() + 1).sum().item()
                nll_sum = -lp_y.sum().item()
                r = pool[i + b]
                f.write(json.dumps({
                    "trajectory_id": r["trajectory_id"], "problem_id": r["problem_id"], "checkpoint": args.tag,
                    "n_tokens": int(sel.sum()), "nll_sum": nll_sum, "ell": nll_sum / int(sel.sum()),
                    "brier_sum": brier,
                }) + "\n")
            print(f"[{args.tag}] {min(i + args.batch_size, len(examples))}/{len(examples)}  {time.time() - t0:.0f}s",
                  flush=True)
    elapsed = time.time() - t0
    write_json(args.out.with_suffix(".summary.json"), {
        "checkpoint": args.tag, "adapter": args.adapter, "model": model_name, "revision": revision,
        "dtype": str(dtype).replace("torch.", ""), "n_trajectories": len(examples),
        "pool": str(args.pool), "pool_sha256": sha256_file(args.pool),
        "forward_passes": len(examples), "elapsed_seconds": round(elapsed, 1),
        "peak_gpu_memory_gb": round(torch.cuda.max_memory_allocated() / 2**30, 2) if torch.cuda.is_available() else None,
        "environment": environment_info(torch),
    })
    print(f"[{args.tag}] scored {len(examples)} trajectories in {elapsed:.0f}s -> {args.out}")


if __name__ == "__main__":
    main()
