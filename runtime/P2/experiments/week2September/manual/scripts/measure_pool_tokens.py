"""
Measure token lengths of verified trajectories under the Student tokenizer (Task 5, decision #12).

Two counts per trajectory, because whether prompt tokens count toward the training budget is not decided:
  response_tokens = tokens of the Teacher response (raw_generation: "REASONING: ... ANSWER: ...")
  total_tokens    = tokens of chat_template(user = prompt v1 with question) + response

Prompt v1 = PROMPT_TEMPLATE of scripts/generate_teacher_trajectories_batch.py (read from the file, not copied).
Only tokenization is done; no model weights are downloaded.

Usage:
  python scripts/measure_pool_tokens.py [--pool ...verified.jsonl] [--model Qwen/Qwen2.5-1.5B-Instruct]
                                        [--revision SHA] [--out reports/task5/pool_token_stats.json]
"""

from pathlib import Path
import argparse
import ast
import collections
import json
import statistics

from transformers import AutoTokenizer


BASE = Path(__file__).resolve().parents[1]
DEFAULT_POOL = BASE / "trajectory" / "pool" / "batch_100_teacher_verified.jsonl"
GENERATOR = BASE / "scripts" / "generate_teacher_trajectories_batch.py"


def load_prompt_template():
    tree = ast.parse(GENERATOR.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "PROMPT_TEMPLATE" for t in node.targets):
            return ast.literal_eval(node.value)
    raise RuntimeError("PROMPT_TEMPLATE not found")


def describe(values):
    q = statistics.quantiles(values, n=4)
    return {
        "n": len(values),
        "sum": sum(values),
        "mean": round(statistics.mean(values), 2),
        "median": statistics.median(values),
        "q1": q[0],
        "q3": q[2],
        "min": min(values),
        "max": max(values),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pool", type=Path, default=DEFAULT_POOL)
    parser.add_argument("--model", default="Qwen/Qwen2.5-1.5B-Instruct")
    parser.add_argument("--revision", default=None)
    parser.add_argument("--out", type=Path, default=BASE / "reports" / "task5" / "pool_token_stats.json")
    args = parser.parse_args()

    template = load_prompt_template()
    tokenizer = AutoTokenizer.from_pretrained(args.model, revision=args.revision)

    records = [json.loads(l) for l in args.pool.open(encoding="utf-8") if l.strip()]
    records = [r for r in records if r["metadata"].get("verification_status") == "valid"]

    response, total, teacher = [], [], []
    shortest_per_problem = {}

    for r in records:
        resp = r["raw_generation"]
        messages = [
            {"role": "user", "content": template.format(question=r["question"])},
            {"role": "assistant", "content": resp},
        ]
        n_resp = len(tokenizer(resp, add_special_tokens=False)["input_ids"])
        chat_text = tokenizer.apply_chat_template(messages, tokenize=False)
        n_total = len(tokenizer(chat_text, add_special_tokens=False)["input_ids"])
        response.append(n_resp)
        total.append(n_total)
        teacher.append(r["metadata"]["token_length"])
        pid = r["problem_id"]
        best = shortest_per_problem.get(pid)
        if best is None or (n_resp, r["trajectory_id"]) < best:
            shortest_per_problem[pid] = (n_resp, r["trajectory_id"])

    stats = {
        "pool": str(args.pool.relative_to(BASE)),
        "student_tokenizer": args.model,
        "tokenizer_revision": args.revision,
        "prompt_source": "scripts/generate_teacher_trajectories_batch.py:PROMPT_TEMPLATE",
        "n_problems": len({r["problem_id"] for r in records}),
        "response_tokens": describe(response),
        "total_tokens_with_prompt": describe(total),
        "teacher_token_length_metadata": describe(teacher),
        "teacher_minus_response_tokens": dict(sorted(collections.Counter(b - a for a, b in zip(response, teacher)).items())),
        "b3_shortest_per_problem_response_tokens": describe([v[0] for v in shortest_per_problem.values()]),
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(stats, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(stats, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
