#!/usr/bin/env python3
"""Regenerate only non-valid trajectories in a Task-4 raw JSONL file.

The input raw file is never modified. New generations are written to a retry
JSONL, and a merged raw JSONL is written separately, replacing records by
trajectory_id while preserving the original record order.
"""
import argparse
import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, set_seed

PROMPT_TEMPLATE = """Solve this GSM8K math problem carefully. Keep the reasoning concise and complete.

Problem:
{question}

Follow this output format exactly. Do not use Markdown headings. Do not add text before or after these two sections. In ANSWER, write only the final numeric answer, with no explanation or units.

REASONING:
<concise step-by-step reasoning>
ANSWER:
<one final numeric answer>"""


def read_jsonl(path):
    records = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in {path}, line {line_no}: {e}") from e
    return records


def write_jsonl(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            f.flush()


def build_prompt(tokenizer, question):
    content = PROMPT_TEMPLATE.format(question=question)
    messages = [{"role": "user", "content": content}]
    if getattr(tokenizer, "chat_template", None):
        return tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
    return content


def split_response(text):
    """Parse labels on their own lines; tolerate accidental Markdown markers."""
    text = (text or "").strip()
    pattern = (
        r"(?ims)^\s*(?:#{1,6}\s*)?(?:\*\*)?REASONING(?:\*\*)?\s*:\s*"
        r"(.*?)^\s*(?:#{1,6}\s*)?(?:\*\*)?ANSWER(?:\*\*)?\s*:\s*(.*?)\s*$"
    )
    match = re.search(pattern, text)
    if not match:
        return text, "", "invalid_format"
    reasoning = match.group(1).strip()
    answer_block = match.group(2).strip()
    if not reasoning or not answer_block:
        return reasoning, answer_block, "invalid_format"

    # The retry prompt requests a single numeric answer. Use the first
    # non-empty line so explanatory numbers later in a response cannot replace it.
    answer_lines = [line.strip() for line in answer_block.splitlines() if line.strip()]
    while answer_lines and re.fullmatch(r"[*_`#\s-]+", answer_lines[0]):
        answer_lines.pop(0)
    if not answer_lines:
        return reasoning, "", "invalid_format"
    answer = answer_lines[0].strip().strip("*_` ")
    return reasoning, answer, "parsed" if answer else "invalid_format"


def numeric_value(value):
    """Canonicalize a numeric answer, including values such as 36 and 36.00."""
    text = str(value or "").replace(",", "").replace("$", "").replace("%", "").strip()
    # Ground-truth values in this GSM8K batch are expected to be numeric.
    match = re.search(r"[-+]?\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return format(Decimal(match.group(0)).normalize(), "f")
    except InvalidOperation:
        return None


def count_steps(reasoning):
    lines = [line.strip() for line in reasoning.splitlines() if line.strip()]
    numbered = [line for line in lines if re.match(r"^(?:step\s*)?\d+[.)\s]", line, re.I)]
    if numbered:
        return max(1, len(numbered))
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", reasoning) if s.strip()]
    return max(1, len(sentences)) if reasoning else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, required=True, help="Current raw trajectory JSONL")
    parser.add_argument("--problems", type=Path, required=True, help="Original batch_100.jsonl")
    parser.add_argument("--retry-output", type=Path, required=True, help="New failed-only generations JSONL")
    parser.add_argument("--merged-output", type=Path, required=True, help="Merged JSONL; input raw is not overwritten")
    parser.add_argument("--model", default="Qwen/Qwen2.5-3B-Instruct")
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--max-new-tokens", type=int, default=768)
    parser.add_argument("--seed-offset", type=int, default=100000)
    parser.add_argument("--checkpoint", default="ckpt_000")
    args = parser.parse_args()

    raw_records = read_jsonl(args.raw)
    problems = read_jsonl(args.problems)
    problem_map = {str(p["problem_id"]): p for p in problems}

    seen_ids = [r.get("trajectory_id") for r in raw_records]
    if any(not x for x in seen_ids):
        raise ValueError("Raw file contains a record without trajectory_id")
    if len(set(seen_ids)) != len(seen_ids):
        raise ValueError("Raw file contains duplicate trajectory_id values; fix these before retrying")

    failed = [r for r in raw_records if r.get("metadata", {}).get("verification_status") != "valid"]
    if not failed:
        print("No non-valid trajectories found; nothing to regenerate.")
        write_jsonl(args.merged_output, raw_records)
        return

    for r in failed:
        if str(r.get("problem_id")) not in problem_map:
            raise ValueError(f"Problem not found in input batch: {r.get('problem_id')}")

    print(f"Raw trajectories: {len(raw_records)}", flush=True)
    print(f"Trajectories selected for retry: {len(failed)}", flush=True)
    print("Valid trajectories will not be regenerated.", flush=True)

    tokenizer = AutoTokenizer.from_pretrained(args.model)
    dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32
    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        torch_dtype=dtype,
        device_map="auto",
    )
    model.eval()

    retry_records = []
    args.retry_output.parent.mkdir(parents=True, exist_ok=True)
    # Write each retry immediately so a later interruption does not lose
    # already completed generations.
    with args.retry_output.open("w", encoding="utf-8", newline="\n") as retry_file:
        for index, old in enumerate(failed, 1):
          problem = problem_map[str(old["problem_id"])]
          prompt = build_prompt(tokenizer, problem["question"])
          inputs = tokenizer(prompt, return_tensors="pt")
          input_device = next(model.parameters()).device
          inputs = {key: value.to(input_device) for key, value in inputs.items()}
  
          old_meta = old.get("metadata", {})
          seed = int(old_meta.get("generation_seed", 20261009)) + args.seed_offset + index
          set_seed(seed)
          print(
              f"[START] retry {index}/{len(failed)}: {old['trajectory_id']} "
              f"(previous={old_meta.get('verification_status')})",
              flush=True,
          )
          with torch.no_grad():
              output_ids = model.generate(
                  **inputs,
                  do_sample=True,
                  temperature=args.temperature,
                  max_new_tokens=args.max_new_tokens,
                  pad_token_id=tokenizer.eos_token_id,
              )
          generated_ids = output_ids[0][inputs["input_ids"].shape[1]:]
          raw_text = tokenizer.decode(generated_ids, skip_special_tokens=True).strip()
          reasoning, answer, parse_status = split_response(raw_text)
  
          if parse_status != "parsed":
              verification = "invalid_format"
          elif numeric_value(answer) is None:
              verification = "invalid_format"
          elif numeric_value(answer) == numeric_value(problem["ground_truth"]):
              verification = "valid"
          else:
              verification = "invalid_answer"
  
          record = {
              "problem_id": old["problem_id"],
              "teacher_model": args.model,
              "trajectory_id": old["trajectory_id"],
              "checkpoint": old.get("checkpoint", args.checkpoint),
              "question": problem["question"],
              "reasoning_trace": reasoning,
              "answer": answer,
              "ground_truth": problem["ground_truth"],
              "metadata": {
                  "num_steps": count_steps(reasoning),
                  "token_length": len(generated_ids),
                  "generation_seed": seed,
                  "temperature": args.temperature,
                  "max_new_tokens": args.max_new_tokens,
                  "verification_status": verification,
                  "retry_attempt": int(old_meta.get("retry_attempt", 0)) + 1,
                  "replaced_status": old_meta.get("verification_status"),
              },
              "raw_generation": raw_text,
          }
          retry_records.append(record)
          retry_file.write(json.dumps(record, ensure_ascii=False) + "\n")
          retry_file.flush()
          print(f"[SAVED] {index}/{len(failed)} status={verification}", flush=True)
  
    retry_by_id = {r["trajectory_id"]: r for r in retry_records}
    merged = [retry_by_id.get(r["trajectory_id"], r) for r in raw_records]
    write_jsonl(args.merged_output, merged)

    status_counts = {}
    for record in merged:
        status = record.get("metadata", {}).get("verification_status", "missing")
        status_counts[status] = status_counts.get(status, 0) + 1
    print(f"Retry output: {args.retry_output}")
    print(f"Merged output: {args.merged_output}")
    print(f"Merged status counts: {json.dumps(status_counts, ensure_ascii=False, sort_keys=True)}")
    print("Original raw file was not modified.")


if __name__ == "__main__":
    main()
