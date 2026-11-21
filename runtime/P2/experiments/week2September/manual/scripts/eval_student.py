#!/usr/bin/env python3
"""
Evaluate a Student checkpoint on D_dev or D_test with the frozen evaluation protocol.

Protocol (config/experiment_config.json "evaluation"): prompt v1, greedy decoding,
max_new_tokens 512, answers scored by answer_utils.evaluate_output
(invalid_format counts as incorrect; format compliance reported separately).

Greedy is enforced explicitly: the Qwen generation_config ships sampling defaults and
repetition_penalty 1.05, which would otherwise still apply under do_sample=False.

Also records lenient_correct (last number anywhere in the output, format ignored): the registered
secondary metric of T7-5, always reported with strict accuracy and format compliance. Accuracy per
capability is added on D_dev, over the problems with manual labels.

Backends:
  hf    transformers generate (default; used by the Task 5 smoke test)
  vllm  vLLM with the same greedy settings; needs a bf16 GPU (L4/A100). A LoRA adapter is merged into a
        temporary model directory first, exactly as the hf backend merges it before generating.

Output (resumable: problem_ids already in --out are skipped):
  --out           one JSON line per problem
  --summary       accuracy, format compliance, output length, timing, memory

Usage (from experiments/week2September/manual/):
  python scripts/eval_student.py --tag S0 --out reports/task5/smoke_test/eval_S0_dev.jsonl
  python scripts/eval_student.py --tag S1_seed13 --adapter <adapter_dir> \
      --out reports/task5/smoke_test/eval_S1_dev_seed13.jsonl
  python scripts/run_final_d_test.py --help  # G7-gated final D_test
"""
import argparse
import gc
import os
import sys
import tempfile
import time
from pathlib import Path

# Deterministic scheduling in offline mode (vLLM docs, Reproducibility); must be set before importing vllm.
os.environ.setdefault("VLLM_ENABLE_V1_MULTIPROCESSING", "0")

import torch  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eval_metrics import score_output, summarize  # noqa: E402
from student_common import (  # noqa: E402
    add_model_args, append_jsonl, build_prompt, check_prompt_template, end_of_turn_id,
    environment_info, load_capability_labels, load_config, load_dev_rows, load_model, load_test_rows,
    load_tokenizer, pick_dtype, read_jsonl_resumable, student_from_args, write_json,
)


def generate_hf(todo, tok, model_name, revision, dtype, adapter, max_new_tokens, batch_size):
    """Yields lists of (row, text, n_output_tokens), one list per batch."""
    from transformers import GenerationConfig
    model = load_model(model_name, revision, dtype, adapter=adapter)
    gen_cfg = GenerationConfig(
        do_sample=False,
        max_new_tokens=max_new_tokens,
        repetition_penalty=1.0,
        eos_token_id=[end_of_turn_id(tok), tok.eos_token_id],
        pad_token_id=tok.pad_token_id,
    )
    for i in range(0, len(todo), batch_size):
        batch = todo[i: i + batch_size]
        prompts = [build_prompt(tok, r["question"]) for r in batch]
        enc = tok(prompts, return_tensors="pt", padding=True, add_special_tokens=False).to(model.device)
        with torch.no_grad():
            out = model.generate(**enc, generation_config=gen_cfg)
        results = []
        for r, ids in zip(batch, out[:, enc["input_ids"].shape[1]:]):
            ids = ids.tolist()
            n_out = len(ids)
            while n_out and ids[n_out - 1] == tok.pad_token_id:
                n_out -= 1
            results.append((r, tok.decode(ids[:n_out], skip_special_tokens=True), n_out))
        yield results


def generate_vllm(todo, tok, model_name, revision, adapter, max_new_tokens, batch_size, gpu_memory_utilization):
    """Same contract as generate_hf. batch_size here is the number of problems per generate() call."""
    from vllm import LLM, SamplingParams
    if not torch.cuda.is_available() or not torch.cuda.is_bf16_supported():
        raise SystemExit("the vllm backend needs a GPU with bf16 (T6-5)")
    stop_ids = sorted({end_of_turn_id(tok), tok.eos_token_id})
    params = SamplingParams(n=1, temperature=0.0, top_p=1.0, repetition_penalty=1.0,
                            max_tokens=max_new_tokens, stop_token_ids=stop_ids)
    with tempfile.TemporaryDirectory(prefix="merged_student_") as merged:
        if adapter:
            model = load_model(model_name, revision, torch.bfloat16, adapter=adapter)
            model.save_pretrained(merged)
            tok.save_pretrained(merged)
            del model
            gc.collect()
            torch.cuda.empty_cache()
            llm = LLM(model=merged, dtype="bfloat16", generation_config="vllm",
                      gpu_memory_utilization=gpu_memory_utilization)
        else:
            llm = LLM(model=model_name, revision=revision, tokenizer_revision=revision, dtype="bfloat16",
                      generation_config="vllm", gpu_memory_utilization=gpu_memory_utilization)
        for i in range(0, len(todo), batch_size):
            batch = todo[i: i + batch_size]
            outputs = llm.generate([build_prompt(tok, r["question"]) for r in batch], params, use_tqdm=False)
            yield [(r, o.outputs[0].text, len(o.outputs[0].token_ids)) for r, o in zip(batch, outputs)]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tag", required=True, help="checkpoint label, e.g. S0 or S1_seed13")
    ap.add_argument("--adapter", default=None, help="LoRA adapter directory (omit for S_0)")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--summary", type=Path, default=None, help="default: <out>.summary.json")
    ap.add_argument("--split", default="dev", choices=["dev", "test"])
    ap.add_argument("--backend", default="hf", choices=["hf", "vllm"])
    ap.add_argument("--batch-size", type=int, default=None, help="default: 16 for hf, 200 for vllm")
    ap.add_argument("--gpu-memory-utilization", type=float, default=0.85, help="vllm backend only")
    ap.add_argument("--limit", type=int, default=None, help="first N problems only (pipeline tests)")
    add_model_args(ap)
    args = ap.parse_args()
    if args.split == "test":
        ap.error("Final D_test must use run_final_d_test.py with a frozen FINAL G7 manifest")
    evaluate(args)


def evaluate(args):
    check_prompt_template()
    cfg = load_config()
    ev = cfg["evaluation"]
    if ev["decoding"] != "greedy":
        raise ValueError("config evaluation.decoding is not greedy")
    model_name, revision = student_from_args(args, cfg)
    dtype = pick_dtype(torch, args.dtype)
    batch_size = args.batch_size or (200 if args.backend == "vllm" else 16)

    rows = load_dev_rows() if args.split == "dev" else load_test_rows()
    if args.limit:
        rows = rows[: args.limit]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    done = {r["problem_id"] for r in read_jsonl_resumable(args.out)}
    todo = [r for r in rows if r["problem_id"] not in done]
    print(f"[{args.tag}] {args.split}: {len(rows)} problems, {len(done)} already done, {len(todo)} to run, "
          f"backend={args.backend}, dtype={dtype}")

    tok = load_tokenizer(model_name, revision)
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
    t0 = time.time()
    n_done = 0
    if todo:
        if args.backend == "vllm":
            batches = generate_vllm(todo, tok, model_name, revision, args.adapter, ev["max_new_tokens"], batch_size,
                                    args.gpu_memory_utilization)
        else:
            batches = generate_hf(todo, tok, model_name, revision, dtype, args.adapter, ev["max_new_tokens"], batch_size)
        for batch in batches:
            for r, text, n_out in batch:
                append_jsonl(args.out, score_output(r, args.tag, text, n_out, ev["max_new_tokens"]))
            n_done += len(batch)
            print(f"[{args.tag}] {n_done}/{len(todo)}  {time.time() - t0:.0f}s", flush=True)
    elapsed = time.time() - t0

    wanted = {x["problem_id"] for x in rows}
    results = [r for r in read_jsonl_resumable(args.out) if r["problem_id"] in wanted]
    if len(results) != len(rows):
        raise RuntimeError(f"{args.out} has {len(results)} of {len(rows)} problems")
    labels = load_capability_labels() if args.split == "dev" else None
    summary = {
        "checkpoint": args.tag,
        "split": args.split,
        "backend": args.backend,
        "model": model_name,
        "revision": revision,
        "adapter": args.adapter,
        "dtype": "bfloat16" if args.backend == "vllm" else str(dtype).replace("torch.", ""),
        **summarize(results, labels),
        "decoding": {"do_sample": False, "max_new_tokens": ev["max_new_tokens"], "repetition_penalty": 1.0,
                     "prompt_version": ev["prompt_version"]},
        "batch_size": batch_size,
        "limit": args.limit,
        "elapsed_seconds_this_run": round(elapsed, 1),
        "problems_this_run": len(todo),
        "peak_gpu_memory_gb": round(torch.cuda.max_memory_allocated() / 2**30, 2) if torch.cuda.is_available() else None,
        "environment": environment_info(torch),
    }
    summary_path = args.summary or args.out.with_suffix(".summary.json")
    write_json(summary_path, summary)
    print(f"[{args.tag}] accuracy {summary['accuracy']:.4f}  lenient {summary['lenient_accuracy']:.4f}  "
          f"format {summary['format_compliance']:.4f}  mean_len {summary['mean_output_tokens']:.1f}  -> {summary_path}")


if __name__ == "__main__":
    main()
