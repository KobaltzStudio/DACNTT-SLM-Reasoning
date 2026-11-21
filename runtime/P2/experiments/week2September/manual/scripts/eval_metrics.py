#!/usr/bin/env python3
"""
Per-problem scoring and summary metrics of a Student evaluation (analysis_plan.md section 6). No torch.

Strict accuracy (primary), lenient accuracy (registered secondary, T7-5) and format compliance are always
reported together. Accuracy per capability uses the manual labels, which exist only for the 85 supplement
problems of D_dev (task5_decisions.md, consequence of #7).
"""
from answer_utils import answers_match, evaluate_output


def score_output(problem, tag, text, n_output_tokens, max_new_tokens):
    return {
        "problem_id": problem["problem_id"],
        "checkpoint": tag,
        "status": evaluate_output(text, problem["ground_truth"]),
        "lenient_correct": answers_match(text, problem["ground_truth"]),
        "ground_truth": problem["ground_truth"],
        "n_output_tokens": n_output_tokens,
        "hit_max_tokens": n_output_tokens >= max_new_tokens,
        "raw_output": text,
    }


def _rates(results):
    n = len(results)
    return {
        "n_problems": n,
        "accuracy": sum(r["status"] == "valid" for r in results) / n,
        "lenient_accuracy": sum(r["lenient_correct"] for r in results) / n,
        "format_compliance": sum(r["status"] != "invalid_format" for r in results) / n,
    }


def summarize(results, capability_labels=None):
    if not results:
        raise ValueError("no results to summarize")
    n = len(results)
    summary = {
        **_rates(results),
        # same value as lenient_accuracy, under the key the Task 5 smoke summaries use
        "lenient_accuracy_exploratory": sum(r["lenient_correct"] for r in results) / n,
        "n_valid": sum(r["status"] == "valid" for r in results),
        "n_invalid_answer": sum(r["status"] == "invalid_answer" for r in results),
        "n_invalid_format": sum(r["status"] == "invalid_format" for r in results),
        "mean_output_tokens": sum(r["n_output_tokens"] for r in results) / n,
        "n_hit_max_tokens": sum(r["hit_max_tokens"] for r in results),
    }
    if capability_labels:
        labelled = [r for r in results if r["problem_id"] in capability_labels]
        capabilities = sorted({c for r in labelled for c in capability_labels[r["problem_id"]]})
        summary["n_problems_with_capability_labels"] = len(labelled)
        summary["by_capability"] = {
            c: _rates([r for r in labelled if c in capability_labels[r["problem_id"]]]) for c in capabilities
        }
    return summary
