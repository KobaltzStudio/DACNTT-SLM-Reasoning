#!/usr/bin/env python3
"""
Selection rules of B2, B3, B4, B5 and the shuffled-scores ablation (analysis_plan.md section 5,
task7_decisions.md T7-1, T7-2, T7-3). Pure Python: no torch, no files; select_round.py does the I/O.

Budget filling (protocol section 16.1, tokens(B_t) <= beta_round): walk the order and stop at the first
trajectory that would exceed the budget. Later, shorter trajectories are not used to top up, because that
would favour short trajectories over the method's own order. B3 and B4 keep the stopping trajectory for
the next round.

Tokens are response tokens under the Student tokenizer without the end-of-turn token, the unit of L_bar
and therefore of beta_round.

Seeds fixed by the config: B2 random.Random(training_seed * 100 + round); B3 random.Random(training_seed).
The ablation's seed is not in the config; ABLATION_SEED_OFFSET keeps it apart from B2.
"""
import random
from collections import Counter

from learnability import score_checkpoint

METHODS = ("B2", "B3", "B4", "B5", "ablation_shuffled_scores")
NEEDS_NLL = ("B4", "B5", "ablation_shuffled_scores")
ABLATION_SEED_OFFSET = 50
SELECTED_CRITERION = {"B2": "random", "B3": "shortest_correct", "B4": "top_score", "B5": "top_score",
                      "ablation_shuffled_scores": "shuffled_score"}


def fill_budget(order, problems, tokens, budget, n_cap, unavailable=()):
    """Returns (selected ids in order, {id: reason}, tokens used, whether the budget stopped the walk)."""
    unavailable = set(unavailable)
    selected, reasons, per_problem = [], {}, Counter()
    used, stopped = 0, False
    for tid in order:
        if tid in unavailable:
            reasons[tid] = "already_trained"
        elif stopped:
            reasons[tid] = "budget_exhausted"
        elif per_problem[problems[tid]] >= n_cap:
            reasons[tid] = "n_cap_reached"
        elif used + tokens[tid] > budget:
            stopped = True
            reasons[tid] = "budget_exhausted"
        else:
            selected.append(tid)
            reasons[tid] = "selected"
            per_problem[problems[tid]] += 1
            used += tokens[tid]
    return selected, reasons, used, stopped


def rank_by_score(scores):
    """Descending score, ties by trajectory_id ascending (decision #23)."""
    return sorted(scores, key=lambda tid: (-scores[tid], tid))


def random_order(ids, seed):
    order = sorted(ids)
    random.Random(seed).shuffle(order)
    return order


def shuffled_scores(scores, seed):
    """The same score values assigned to trajectories at random."""
    ids = sorted(scores)
    values = [scores[tid] for tid in ids]
    random.Random(seed).shuffle(values)
    return dict(zip(ids, values))


def shortest_per_problem(problems, tokens):
    """Decision #24: per problem the shortest trajectory, ties by smallest trajectory_id."""
    best = {}
    for tid in sorted(problems):
        pid = problems[tid]
        if pid not in best or tokens[tid] < tokens[best[pid]]:
            best[pid] = tid
    return best


def b3_order(problems, tokens, training_seed):
    """B3 order: the shortest trajectory of each problem, problems shuffled once [T7-2]."""
    best = shortest_per_problem(problems, tokens)
    return [best[pid] for pid in random_order(best, training_seed)]


def static_round(order, problems, tokens, budget, n_cap, round_index):
    """
    Round round_index of a once-computed order (B3, B4): walk it without repeating a trajectory; a
    trajectory skipped by n_cap or by the budget stays available for later rounds [T7-1, T7-2].
    """
    used_before = set()
    for r in range(round_index + 1):
        selected, reasons, used, stopped = fill_budget(order, problems, tokens, budget, n_cap, used_before)
        if r < round_index:
            used_before |= set(selected)
    return selected, reasons, used, stopped


def select(method, round_index, training_seed, problems, tokens, budget, n_cap, ell_by_id=None, trained_ids=()):
    """
    One round's selection over the eligible pool. Returns the selected ids, tokens used, band parameters
    and one log entry per eligible trajectory (fields of selection_log_schema.json, null where unused).
    ell_by_id: ell at S_t for B5 and the ablation, at S_0 for B4 in every round.
    trained_ids: trained in this run before this round (reference set of B5 and the ablation [T7-3]).
    """
    if method not in METHODS:
        raise ValueError(f"unknown method {method}")
    scoring, scores = None, None
    if method in NEEDS_NLL:
        if ell_by_id is None or set(ell_by_id) != set(problems):
            raise ValueError(f"{method} needs ell for exactly the eligible pool")
        # B4 ranks at S_0, where nothing has been trained: the reference set is the whole eligible pool.
        scoring = score_checkpoint(ell_by_id, () if method == "B4" else trained_ids)
        scores = scoring["l_proxy"]

    if method == "B2":
        order = random_order(problems, training_seed * 100 + round_index)
        selected, reasons, used, stopped = fill_budget(order, problems, tokens, budget, n_cap)
    elif method == "B3":
        order = b3_order(problems, tokens, training_seed)
        selected, reasons, used, stopped = static_round(order, problems, tokens, budget, n_cap, round_index)
    elif method == "B4":
        order = rank_by_score(scores)
        selected, reasons, used, stopped = static_round(order, problems, tokens, budget, n_cap, round_index)
    else:
        if method == "ablation_shuffled_scores":
            scores = shuffled_scores(scores, training_seed * 100 + round_index + ABLATION_SEED_OFFSET)
        order = rank_by_score(scores)
        selected, reasons, used, stopped = fill_budget(order, problems, tokens, budget, n_cap)
    if not stopped:
        raise ValueError(f"{method} round {round_index}: order exhausted before the budget ({used}/{budget} tokens)")

    ranks = {tid: i for i, tid in enumerate(order, start=1)}
    has_rank = method != "B2"
    rows = []
    for tid in sorted(problems):
        reason = reasons.get(tid, "not_shortest")
        rows.append({
            "problem_id": problems[tid],
            "trajectory_id": tid,
            "tokens": tokens[tid],
            "nll": ell_by_id[tid] if scoring else None,
            "ell_star": scoring["ell_star"] if scoring else None,
            "sigma": scoring["sigma"] if scoring else None,
            "l_proxy": scoring["l_proxy"][tid] if scoring else None,
            "score": scores[tid] if scores else None,
            "rank": ranks.get(tid) if has_rank else None,
            "selected": reason == "selected",
            "criterion": SELECTED_CRITERION[method] if reason == "selected" else reason,
            "outcome": None,
        })
    return {
        "selected": selected,
        "tokens_used": used,
        "ell_star": scoring["ell_star"] if scoring else None,
        "sigma": scoring["sigma"] if scoring else None,
        "n_reference": scoring["n_reference"] if scoring else None,
        "rows": rows,
    }


def probe_groups(tokens, group_size, seed, n_bins=5):
    """
    L_emp groups (config budget.l_emp_groups): token-length quintile bins of the eligible pool, group_size
    trajectories sampled per bin. n_cap is not applied: the rule does not ask for it.
    """
    ordered = sorted(tokens, key=lambda tid: (tokens[tid], tid))
    bins = [ordered[i * len(ordered) // n_bins: (i + 1) * len(ordered) // n_bins] for i in range(n_bins)]
    rng = random.Random(seed)
    return [sorted(rng.sample(b, group_size)) for b in bins]
