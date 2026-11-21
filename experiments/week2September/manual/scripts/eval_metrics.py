import sys
from pathlib import Path
from collections import defaultdict
sys.path.insert(0, str(Path(__file__).resolve().parent))
from answer_utils import evaluate_output, split_response, answers_match

def score_output(row, tag, raw_output, n_output_tokens, max_new_tokens=None):
    _, answer, parse_status = split_response(raw_output)
    status = evaluate_output(raw_output, row["ground_truth"])
    return {
        "problem_id": row["problem_id"], "checkpoint": tag,
        "ground_truth": str(row["ground_truth"]), "raw_output": raw_output,
        "parsed_answer": answer, "verification_status": status,
        "correct": status == "valid",
        "lenient_correct": bool(answers_match(raw_output, row["ground_truth"])),
        "format_compliant": parse_status == "parsed",
        "output_tokens": int(n_output_tokens),
        "hit_max_new_tokens": bool(max_new_tokens is not None and int(n_output_tokens) >= int(max_new_tokens)),
    }

def summarize(results, capability_labels=None):
    if not results:
        raise ValueError("Cannot summarize an empty evaluation set")
    n = len(results)
    correct = [bool(r.get("correct", r.get("verification_status") == "valid")) for r in results]
    out = {
        "n_problems": n,
        "accuracy": sum(correct) / n,
        "lenient_accuracy": sum(bool(r.get("lenient_correct", False)) for r in results) / n,
        "format_compliance": sum(bool(r.get("format_compliant", False)) for r in results) / n,
        "mean_output_tokens": sum(int(r.get("output_tokens", 0)) for r in results) / n,
    }
    buckets = defaultdict(list)
    if capability_labels:
        for r, ok in zip(results, correct):
            for cap in capability_labels.get(r["problem_id"], []):
                buckets[cap].append(ok)
    out["capability_accuracy"] = {
        k: {"n": len(v), "accuracy": sum(v) / len(v)}
        for k, v in sorted(buckets.items()) if v
    }
    return out
