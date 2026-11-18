#!/usr/bin/env python3
"""
Generate K Teacher reasoning trajectories per problem for the Task-4 batch.

This creates RAW teacher data. It deliberately does not ask the Teacher to
self-label capabilities. Capability labels are produced later by the
rule-based extractor.

Input JSONL fields:
  problem_id, question, ground_truth

Output JSONL fields:
  problem_id, teacher_model, trajectory_id, checkpoint,
  question, reasoning_trace, answer, ground_truth,
  metadata, raw_generation

Usage:
  python generate_teacher_trajectories_batch.py \
      data/batch_100/batch_100.jsonl \
      trajectory/pool/batch_100_teacher_raw.jsonl

Requires: torch, transformers
"""
import argparse
import json
import re
from pathlib import Path
import time
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, set_seed

PROMPT_TEMPLATE = """Solve the following math problem.

Provide a concise but complete reasoning trace followed by the final answer.

Problem:
{question}

Return exactly:

REASONING:
<step-by-step reasoning>

ANSWER:
<final answer>"""


def load_jsonl(path):
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if line.strip():
                row = json.loads(line)
                for key in ("problem_id", "question", "ground_truth"):
                    if key not in row:
                        raise ValueError(f"Missing {key} at line {line_no}")
                rows.append(row)
    return rows


def split_response(text):
    text = (text or "").strip()

    m = re.search(
        r"REASONING\s*:\s*(.*?)\s*ANSWER\s*:\s*(.*?)\s*$",
        text,
        re.IGNORECASE | re.DOTALL,
    )

    if not m:
        return text, "", "invalid_format"

    reasoning = m.group(1).strip()
    answer = m.group(2).strip()

    if not reasoning or not answer:
        return reasoning, answer, "invalid_format"

    return reasoning, answer, "parsed"


def normalize_answer(value):
    value = str(value or "").replace(",", "").strip().lower()
    value = value.replace("$", "").replace("%", "")
    nums = re.findall(r"[-+]?\d+(?:\.\d+)?", value)
    return nums[-1] if nums else value


def verify_answer(answer, ground_truth):
    if not answer:
        return "invalid_format"
    return "valid" if normalize_answer(answer) == normalize_answer(ground_truth) else "invalid_answer"


def count_steps(reasoning):
    lines = [x.strip() for x in reasoning.splitlines() if x.strip()]
    numbered = [x for x in lines if re.match(r"^(?:step\s*)?\d+[.)\s]", x, re.I)]
    if numbered:
        return max(1, len(numbered))
    sentences = [x for x in re.split(r"(?<=[.!?])\s+", reasoning) if x.strip()]
    return max(1, len(sentences))


def build_prompt(tokenizer, question):
    user_prompt = PROMPT_TEMPLATE.format(question=question)
    messages = [{"role": "user", "content": user_prompt}]
    if hasattr(tokenizer, "apply_chat_template") and tokenizer.chat_template:
        return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    return user_prompt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--model", default="Qwen/Qwen2.5-3B-Instruct")
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--max-new-tokens", type=int, default=512)
    parser.add_argument("--generation-seed", type=int, default=20261009)
    parser.add_argument("--checkpoint", default="ckpt_000")
    args = parser.parse_args()

    rows = load_jsonl(args.input)
    if not rows:
        raise ValueError("Input is empty")
    if args.k < 1:
        raise ValueError("--k must be >= 1")

    tokenizer = AutoTokenizer.from_pretrained(args.model)
    dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32
    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        torch_dtype=dtype,
        device_map="auto",
    )
    model.eval()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    generated = 0
    with args.output.open("w", encoding="utf-8") as fout:
        start_time = time.time()
        print(
            f"Starting generation: {len(rows)} problems x {args.k} trajectories",
            flush=True,
        )
        print(f"CUDA available: {torch.cuda.is_available()}", flush=True)
        for problem_index, row in enumerate(rows):
            prompt = build_prompt(tokenizer, row["question"])
            inputs = tokenizer(prompt, return_tensors="pt")
            input_device = next(model.parameters()).device
            inputs = {k: v.to(input_device) for k, v in inputs.items()}

            for k in range(args.k):
                seed = args.generation_seed + problem_index * args.k + k
                set_seed(seed)
                with torch.no_grad():
                    print(
                        f"[START] problem {problem_index + 1}/{len(rows)}, "
                        f"trajectory {k + 1}/{args.k}",
                        flush=True,
                    )
                    trajectory_start = time.time()
                    output_ids = model.generate(
                        **inputs,
                        do_sample=True,
                        temperature=args.temperature,
                        max_new_tokens=args.max_new_tokens,
                        pad_token_id=tokenizer.eos_token_id,
                    )
                    print(
                        f"[GENERATED] problem {problem_index + 1}/{len(rows)}, "
                        f"trajectory {k + 1}/{args.k}, "
                        f"elapsed={time.time() - trajectory_start:.1f}s",
                        flush=True,
                    )
                generated_ids = output_ids[0][inputs["input_ids"].shape[1]:]
                raw_text = tokenizer.decode(generated_ids, skip_special_tokens=True).strip()
                reasoning, answer, parse_status = split_response(raw_text)
                verification = verify_answer(answer, row["ground_truth"])
                if parse_status != "parsed":
                    verification = "invalid_format"

                record = {
                    "problem_id": row["problem_id"],
                    "teacher_model": args.model,
                    "trajectory_id": f"{row['problem_id']}_traj_{k+1:03d}",
                    "checkpoint": args.checkpoint,
                    "question": row["question"],
                    "reasoning_trace": reasoning,
                    "answer": answer,
                    "ground_truth": row["ground_truth"],
                    "metadata": {
                        "num_steps": count_steps(reasoning) if reasoning else 0,
                        "token_length": len(generated_ids),
                        "generation_seed": seed,
                        "temperature": args.temperature,
                        "max_new_tokens": args.max_new_tokens,
                        "verification_status": verification,
                    },
                    "raw_generation": raw_text,
                }
                fout.write(json.dumps(record, ensure_ascii=False) + "\n")
                fout.flush()
                print(
                    f"[SAVED] {generated + 1}/{len(rows) * args.k}",
                    flush=True,
                )
                generated += 1

    print(f"Problems: {len(rows)}")
    print(f"Expected trajectories: {len(rows) * args.k}")
    print(f"Generated trajectories: {generated}")
    print(f"Created: {args.output}")


if __name__ == "__main__":
    main()
