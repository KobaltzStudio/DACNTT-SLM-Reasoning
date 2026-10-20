#!/usr/bin/env python3
"""
Evaluate a Student checkpoint on D_dev with the frozen evaluation protocol.

Protocol (config/experiment_config.json "evaluation"): prompt v1, greedy decoding,
max_new_tokens 512, answers scored by answer_utils.evaluate_output
(invalid_format counts as incorrect; format compliance reported separately).

Greedy is enforced explicitly: the Qwen generation_config ships sampling defaults and
repetition_penalty 1.05, which would otherwise still apply under do_sample=False.

Also records lenient_correct (last number anywhere in the output, format ignored). It is a
diagnostic that separates learning the output format from learning to reason; it does not
replace the frozen metric.

Output (resumable: problem_ids already in --out are skipped):
  --out           one JSON line per problem
  --summary       accuracy, format compliance, output length, timing, memory

Usage (from experiments/week2September/manual/):
  python scripts/eval_student.py --tag S0 --out reports/task5/smoke_test/eval_S0_dev.jsonl
  python scripts/eval_student.py --tag S1_seed13 --adapter <adapter_dir> \
      --out reports/task5/smoke_test/eval_S1_dev_seed13.jsonl
"""
import argparse
import sys
import time
from pathlib import Path

import torch
from transformers import GenerationConfig

sys.path.insert(0, str(Path(__file__).resolve().parent))
from answer_utils import answers_match, evaluate_output  # noqa: E402
from student_common import (  # noqa: E402
    add_model_args, append_jsonl, build_prompt, check_prompt_template, end_of_turn_id,
    environment_info, load_config, load_dev_rows, load_model, load_tokenizer, pick_dtype,
    read_jsonl, student_from_args, write_json,
)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tag", required=True, help="checkpoint label, e.g. S0 or S1_seed13")
    ap.add_argument("--adapter", default=None, help="LoRA adapter directory (omit for S_0)")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--summary", type=Path, default=None, help="default: <out>.summary.json")
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--limit", type=int, default=None, help="first N problems only (pipeline tests)")
    add_model_args(ap)
    args = ap.parse_args()

    check_prompt_template()
    cfg = load_config()
    ev = cfg["evaluation"]
    if ev["decoding"] != "greedy":
        raise ValueError("config evaluation.decoding is not greedy")
    model_name, revision = student_from_args(args, cfg)
    dtype = pick_dtype(torch, args.dtype)

    rows = load_dev_rows()
    if args.limit:
        rows = rows[: args.limit]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    done = {r["problem_id"] for r in read_jsonl(args.out)} if args.out.exists() else set()
    todo = [r for r in rows if r["problem_id"] not in done]
    print(f"[{args.tag}] {len(rows)} problems, {len(done)} already done, {len(todo)} to run, dtype={dtype}")

    tok = load_tokenizer(model_name, revision)
    model = load_model(model_name, revision, dtype, adapter=args.adapter)
    gen_cfg = GenerationConfig(
        do_sample=False,
        max_new_tokens=ev["max_new_tokens"],
        repetition_penalty=1.0,
        eos_token_id=[end_of_turn_id(tok), tok.eos_token_id],
        pad_token_id=tok.pad_token_id,
    )

    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
    t0 = time.time()
    for i in range(0, len(todo), args.batch_size):
        batch = todo[i: i + args.batch_size]
        prompts = [build_prompt(tok, r["question"]) for r in batch]
        enc = tok(prompts, return_tensors="pt", padding=True, add_special_tokens=False).to(model.device)
        with torch.no_grad():
            out = model.generate(**enc, generation_config=gen_cfg)
        new = out[:, enc["input_ids"].shape[1]:]
        for r, ids in zip(batch, new):
            ids = ids.tolist()
            n_out = len(ids)
            while n_out and ids[n_out - 1] == tok.pad_token_id:
                n_out -= 1
            text = tok.decode(ids[:n_out], skip_special_tokens=True)
            append_jsonl(args.out, {
                "problem_id": r["problem_id"],
                "checkpoint": args.tag,
                "status": evaluate_output(text, r["ground_truth"]),
                # diagnostic only: last number anywhere in the output, ignoring the REASONING/ANSWER format
                "lenient_correct": answers_match(text, r["ground_truth"]),
                "ground_truth": r["ground_truth"],
                "n_output_tokens": n_out,
                "hit_max_tokens": n_out >= ev["max_new_tokens"],
                "raw_output": text,
            })
        print(f"[{args.tag}] {min(i + args.batch_size, len(todo))}/{len(todo)}  {time.time() - t0:.0f}s", flush=True)
    elapsed = time.time() - t0

    results = [r for r in read_jsonl(args.out) if r["problem_id"] in {x["problem_id"] for x in rows}]
    n = len(results)
    summary = {
        "checkpoint": args.tag,
        "model": model_name,
        "revision": revision,
        "adapter": args.adapter,
        "dtype": str(dtype).replace("torch.", ""),
        "n_problems": n,
        "accuracy": sum(r["status"] == "valid" for r in results) / n,
        "format_compliance": sum(r["status"] != "invalid_format" for r in results) / n,
        "lenient_accuracy_exploratory": sum(r["lenient_correct"] for r in results) / n,
        "n_valid": sum(r["status"] == "valid" for r in results),
        "n_invalid_answer": sum(r["status"] == "invalid_answer" for r in results),
        "n_invalid_format": sum(r["status"] == "invalid_format" for r in results),
        "mean_output_tokens": sum(r["n_output_tokens"] for r in results) / n,
        "n_hit_max_tokens": sum(r["hit_max_tokens"] for r in results),
        "decoding": {"do_sample": False, "max_new_tokens": ev["max_new_tokens"], "repetition_penalty": 1.0,
                     "prompt_version": ev["prompt_version"]},
        "batch_size": args.batch_size,
        "limit": args.limit,
        "elapsed_seconds_this_run": round(elapsed, 1),
        "problems_this_run": len(todo),
        "peak_gpu_memory_gb": round(torch.cuda.max_memory_allocated() / 2**30, 2) if torch.cuda.is_available() else None,
        "environment": environment_info(torch),
    }
    summary_path = args.summary or args.out.with_suffix(".summary.json")
    write_json(summary_path, summary)
    print(f"[{args.tag}] accuracy {summary['accuracy']:.4f}  format {summary['format_compliance']:.4f}  "
          f"mean_len {summary['mean_output_tokens']:.1f}  -> {summary_path}")


if __name__ == "__main__":
    main()
