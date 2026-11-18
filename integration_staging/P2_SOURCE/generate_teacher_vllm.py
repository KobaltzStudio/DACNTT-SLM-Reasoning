#!/usr/bin/env python3
"""
Generate the official Task 6 Teacher pool with vLLM (task6_decisions.md T6-5).

Frozen settings come from config/experiment_config.json (teacher model, revision, K, temperature,
max_new_tokens, seed rule). The sampling settings HF `generate` applied implicitly from the model's
generation_config for the preliminary pool are declared explicitly here, because vLLM's own defaults
differ (top_p 1.0, top_k off, repetition_penalty 1.0).

  - prompt v1 via student_common.build_prompt (Qwen chat template), guarded by check_prompt_template;
  - one request per trajectory with its own seed: generation_seed_base + problem_index * K + k;
  - --start-index / --end-index select rows of pool_v1_input.jsonl by problem_index;
  - resumable: rows are appended per chunk and trajectory_ids already in --out are skipped;
  - scored with answer_utils (I1); capabilities are added later by the extractor.

Output rows follow the preliminary pool format (problem_id, teacher_model, trajectory_id, checkpoint,
question, reasoning_trace, answer, ground_truth, metadata, raw_generation). A run summary is written
next to --out as <out>.run_<start>_<end>.json.

Usage (on the GPU pod, from experiments/week2September/manual/, after `source scripts/setup_pod.sh`):
  python scripts/generate_teacher_vllm.py --start-index 0 --end-index 100      # parity check (batch_100)
  python scripts/generate_teacher_vllm.py --start-index 100 --end-index 1100   # new problems
  python scripts/generate_teacher_vllm.py --start-index 0 --end-index 3 --dry-run   # no GPU needed
"""
import argparse
import os
import sys
import time
from pathlib import Path

# Deterministic scheduling in offline mode (vLLM docs, Reproducibility); must be set before importing vllm.
os.environ.setdefault("VLLM_ENABLE_V1_MULTIPROCESSING", "0")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from answer_utils import evaluate_output, split_response  # noqa: E402
from student_common import (  # noqa: E402
    MANUAL_DIR, append_jsonl, build_prompt, check_prompt_template, end_of_turn_id, load_config,
    load_tokenizer, read_jsonl, sha256_file, write_json,
)

INPUT_PATH = MANUAL_DIR / "trajectory" / "pool" / "pool_v1_input.jsonl"
OUT_PATH = MANUAL_DIR / "trajectory" / "pool" / "pool_v1_teacher_raw.jsonl"

# HF generation_config of Qwen/Qwen2.5-3B-Instruct @aa8e725, applied implicitly to the preliminary pool
# (task6_decisions.md section 0, finding 5). Temperature and max tokens come from the config.
TOP_P = 0.8
TOP_K = 20
REPETITION_PENALTY = 1.05


def count_steps(reasoning):
    # Same rule as generate_teacher_trajectories_batch.count_steps (kept identical for metadata.num_steps).
    import re
    lines = [x.strip() for x in reasoning.splitlines() if x.strip()]
    numbered = [x for x in lines if re.match(r"^(?:step\s*)?\d+[.)\s]", x, re.I)]
    if numbered:
        return max(1, len(numbered))
    sentences = [x for x in re.split(r"(?<=[.!?])\s+", reasoning) if x.strip()]
    return max(1, len(sentences))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", type=Path, default=INPUT_PATH)
    ap.add_argument("--out", type=Path, default=OUT_PATH)
    ap.add_argument("--start-index", type=int, required=True, help="first problem_index (inclusive)")
    ap.add_argument("--end-index", type=int, required=True, help="last problem_index (exclusive)")
    ap.add_argument("--chunk-problems", type=int, default=100, help="problems per generate() call / append")
    ap.add_argument("--checkpoint", default="ckpt_000", help="checkpoint label stored in each row")
    ap.add_argument("--gpu-memory-utilization", type=float, default=0.85)
    ap.add_argument("--dry-run", action="store_true", help="build prompts and seeds only, no model")
    args = ap.parse_args()

    check_prompt_template()
    cfg = load_config()
    t = cfg["teacher"]
    model_name, revision, K = t["model"], t["revision"], t["K"]
    temperature, max_tokens, seed_base = t["temperature"], t["max_new_tokens"], t["generation_seed_base"]

    rows = read_jsonl(args.input)
    for i, r in enumerate(rows):
        if r["problem_index"] != i:
            raise ValueError(f"{args.input.name}: problem_index must equal row order (row {i})")
    rows = rows[args.start_index: args.end_index]
    if not rows:
        raise SystemExit("empty index range")

    done = {r["trajectory_id"] for r in read_jsonl(args.out)} if args.out.exists() else set()
    requests = []  # (row, k, trajectory_id, seed)
    for r in rows:
        for k in range(K):
            tid = f"{r['problem_id']}_traj_{k + 1:03d}"
            if tid not in done:
                requests.append((r, k, tid, seed_base + r["problem_index"] * K + k))
    print(f"[gen] indices {args.start_index}-{args.end_index - 1}: {len(rows)} problems x K={K}, "
          f"{len(rows) * K - len(requests)} already done, {len(requests)} to run")

    tok = load_tokenizer(model_name, revision)
    # Same stop set as the model's generation_config eos_token_id used by HF: <|im_end|> and <|endoftext|>.
    stop_ids = sorted({end_of_turn_id(tok), tok.convert_tokens_to_ids("<|endoftext|>")})
    if args.dry_run:
        for r, k, tid, seed in requests[:2]:
            print(f"--- {tid} seed={seed} stop_token_ids={stop_ids}\n{build_prompt(tok, r['question'])}")
        return

    from vllm import LLM, SamplingParams
    import vllm
    import torch
    if not torch.cuda.is_bf16_supported():
        raise SystemExit("GPU without bf16: T6-5 forbids running vLLM in fp16 (e.g. on a T4)")
    llm = LLM(model=model_name, revision=revision, tokenizer_revision=revision, dtype="bfloat16",
              gpu_memory_utilization=args.gpu_memory_utilization, generation_config="vllm")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    per_chunk = args.chunk_problems * K
    t0 = time.time()
    for c in range(0, len(requests), per_chunk):
        chunk = requests[c: c + per_chunk]
        prompts = [build_prompt(tok, r["question"]) for r, _, _, _ in chunk]
        params = [SamplingParams(n=1, temperature=temperature, top_p=TOP_P, top_k=TOP_K,
                                 repetition_penalty=REPETITION_PENALTY, max_tokens=max_tokens,
                                 seed=seed, stop_token_ids=stop_ids) for _, _, _, seed in chunk]
        outputs = llm.generate(prompts, params, use_tqdm=False)
        for (r, k, tid, seed), out in zip(chunk, outputs):
            o = out.outputs[0]
            raw = o.text.strip()
            reasoning, answer, parse_status = split_response(raw)
            append_jsonl(args.out, {
                "problem_id": r["problem_id"],
                "teacher_model": model_name,
                "trajectory_id": tid,
                "checkpoint": args.checkpoint,
                "question": r["question"],
                "reasoning_trace": reasoning,
                "answer": answer,
                "ground_truth": r["ground_truth"],
                "metadata": {
                    "num_steps": count_steps(reasoning) if reasoning else 0,
                    "token_length": len(o.token_ids),
                    "generation_seed": seed,
                    "temperature": temperature,
                    "top_p": TOP_P,
                    "top_k": TOP_K,
                    "repetition_penalty": REPETITION_PENALTY,
                    "max_new_tokens": max_tokens,
                    "finish_reason": o.finish_reason,
                    "verification_status": evaluate_output(raw, r["ground_truth"]),
                    "problem_index": r["problem_index"],
                    "source": r["source"],
                    "backend": f"vllm {vllm.__version__}",
                },
                "raw_generation": raw,
            })
        print(f"[gen] {min(c + per_chunk, len(requests))}/{len(requests)}  {time.time() - t0:.0f}s", flush=True)

    rel = lambda p: str(Path(p).resolve().relative_to(MANUAL_DIR))  # noqa: E731
    write_json(args.out.with_name(f"{args.out.name}.run_{args.start_index}_{args.end_index}.json"), {
        "range": [args.start_index, args.end_index],
        "requests_this_run": len(requests),
        "elapsed_seconds_this_run": round(time.time() - t0, 1),
        "teacher": {"model": model_name, "revision": revision, "K": K},
        "sampling": {"temperature": temperature, "top_p": TOP_P, "top_k": TOP_K,
                     "repetition_penalty": REPETITION_PENALTY, "max_tokens": max_tokens,
                     "stop_token_ids": stop_ids, "seed_rule": t["generation_seed_rule"]},
        "input": {rel(args.input): sha256_file(args.input)},
        "config_sha256": sha256_file(MANUAL_DIR / "config" / "experiment_config.json"),
        "environment": {"vllm": vllm.__version__, "torch": torch.__version__,
                        "gpu": torch.cuda.get_device_name(0),
                        "VLLM_ENABLE_V1_MULTIPROCESSING": os.environ.get("VLLM_ENABLE_V1_MULTIPROCESSING")},
    })


if __name__ == "__main__":
    main()
