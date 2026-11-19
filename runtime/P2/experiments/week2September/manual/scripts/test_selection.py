#!/usr/bin/env python3
"""
Unit tests for learnability.py and selection.py (Task 7), no GPU needed.

Usage (from experiments/week2September/manual/):
  python scripts/test_selection.py
"""
import math
import random
import statistics
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from learnability import band_parameters, l_proxy, score_checkpoint  # noqa: E402
from selection import (  # noqa: E402
    ABLATION_SEED_OFFSET, b3_order, fill_budget, probe_groups, rank_by_score, select, shortest_per_problem,
    shuffled_scores, static_round,
)


def synthetic_pool(n_problems=300, k=5, seed=1):
    """problems, tokens and ell of a pool shaped like pool v1 (79-512 tokens, up to 5 per problem)."""
    rng = random.Random(seed)
    problems, tokens, ell = {}, {}, {}
    for p in range(n_problems):
        for j in range(rng.randint(1, k)):
            tid = f"gsm8k_train_{p:05d}_traj_{j + 1:03d}"
            problems[tid] = f"gsm8k_train_{p:05d}"
            tokens[tid] = rng.randint(79, 512)
            ell[tid] = rng.gauss(0.3, 0.08)
    return problems, tokens, ell


class TestLearnability(unittest.TestCase):
    def test_band_parameters(self):
        vals = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]
        star, sigma = band_parameters(vals)
        q = statistics.quantiles(vals, n=4)
        self.assertEqual(star, 4.0)
        self.assertAlmostEqual(sigma, (q[2] - q[0]) / 1.349)

    def test_l_proxy_peak_and_one_sigma(self):
        self.assertEqual(l_proxy(0.3, 0.3, 0.1), 1.0)
        self.assertAlmostEqual(l_proxy(0.4, 0.3, 0.1), math.exp(-0.5))
        self.assertAlmostEqual(l_proxy(0.2, 0.3, 0.1), l_proxy(0.4, 0.3, 0.1))

    def test_rejects_undefined_band(self):
        with self.assertRaises(ValueError):
            band_parameters([0.3] * 10)
        with self.assertRaises(ValueError):
            band_parameters([0.1, float("nan"), 0.3])

    def test_reference_set_excludes_trained_but_all_are_scored(self):
        """T7-3: trained trajectories leave the median/IQR but still get L_proxy."""
        ell = {f"t{i}": 0.1 * i for i in range(1, 11)}
        ell["trained_a"] = 0.001
        ell["trained_b"] = 0.002
        out = score_checkpoint(ell, ["trained_a", "trained_b"])
        star, sigma = band_parameters([0.1 * i for i in range(1, 11)])
        self.assertEqual(out["n_reference"], 10)
        self.assertAlmostEqual(out["ell_star"], star)
        self.assertAlmostEqual(out["sigma"], sigma)
        self.assertEqual(set(out["l_proxy"]), set(ell))

    def test_trained_id_must_be_in_pool(self):
        with self.assertRaises(ValueError):
            score_checkpoint({"a": 0.1, "b": 0.2, "c": 0.3}, ["zzz"])


class TestFillBudget(unittest.TestCase):
    def setUp(self):
        self.problems = {"a1": "a", "a2": "a", "b1": "b", "c1": "c", "d1": "d"}
        self.tokens = {"a1": 100, "a2": 50, "b1": 100, "c1": 100, "d1": 10}

    def test_never_exceeds_budget_and_stops_at_first_overflow(self):
        selected, reasons, used, stopped = fill_budget(["a1", "b1", "c1", "d1"], self.problems, self.tokens, 250, 1)
        self.assertEqual(selected, ["a1", "b1"])
        self.assertEqual(used, 200)
        self.assertTrue(stopped)
        self.assertEqual(reasons["c1"], "budget_exhausted")
        self.assertEqual(reasons["d1"], "budget_exhausted", "must not top up with a later, shorter trajectory")

    def test_exact_budget_is_allowed(self):
        selected, _, used, _ = fill_budget(["a1", "b1", "c1"], self.problems, self.tokens, 200, 1)
        self.assertEqual((selected, used), (["a1", "b1"], 200))

    def test_n_cap_skips_without_stopping(self):
        selected, reasons, _, _ = fill_budget(["a1", "a2", "b1"], self.problems, self.tokens, 1000, 1)
        self.assertEqual(selected, ["a1", "b1"])
        self.assertEqual(reasons["a2"], "n_cap_reached")

    def test_reports_when_budget_did_not_stop_the_walk(self):
        self.assertFalse(fill_budget(["a1"], self.problems, self.tokens, 1000, 1)[3])


class TestRanking(unittest.TestCase):
    def test_ties_by_trajectory_id(self):
        self.assertEqual(rank_by_score({"b": 0.5, "a": 0.5, "c": 0.9}), ["c", "a", "b"])

    def test_shuffled_scores_keep_the_values(self):
        scores = {f"t{i}": i / 100 for i in range(100)}
        out = shuffled_scores(scores, 7)
        self.assertEqual(sorted(out.values()), sorted(scores.values()))
        self.assertNotEqual(out, scores)
        self.assertEqual(out, shuffled_scores(scores, 7))


class TestStaticSchedules(unittest.TestCase):
    def test_n_cap_skip_stays_available_next_round(self):
        """T7-1: a trajectory skipped by n_cap in one round can be used in a later round."""
        problems = {"a1": "a", "a2": "a", "b1": "b", "c1": "c"}
        tokens = dict.fromkeys(problems, 100)
        order = ["a1", "a2", "b1", "c1"]
        r0 = static_round(order, problems, tokens, 250, 1, 0)
        r1 = static_round(order, problems, tokens, 250, 1, 1)
        self.assertEqual(r0[0], ["a1", "b1"])
        self.assertEqual(r0[1]["a2"], "n_cap_reached")
        self.assertEqual(r1[0], ["a2", "c1"])
        self.assertEqual(r1[1]["a1"], "already_trained")

    def test_budget_stopper_opens_the_next_round(self):
        problems = {"a1": "a", "b1": "b", "c1": "c"}
        tokens = {"a1": 100, "b1": 200, "c1": 100}
        order = ["a1", "b1", "c1"]
        self.assertEqual(static_round(order, problems, tokens, 250, 1, 0)[0], ["a1"])
        self.assertEqual(static_round(order, problems, tokens, 250, 1, 1)[0], ["b1"])

    def test_shortest_per_problem(self):
        problems = {"p_traj_002": "p", "p_traj_001": "p", "p_traj_003": "p", "q_traj_001": "q"}
        tokens = {"p_traj_002": 90, "p_traj_001": 90, "p_traj_003": 120, "q_traj_001": 300}
        self.assertEqual(shortest_per_problem(problems, tokens), {"p": "p_traj_001", "q": "q_traj_001"})

    def test_b3_order_depends_on_seed_only(self):
        problems, tokens, _ = synthetic_pool()
        self.assertEqual(b3_order(problems, tokens, 13), b3_order(problems, tokens, 13))
        self.assertNotEqual(b3_order(problems, tokens, 13), b3_order(problems, tokens, 42))


class TestSelect(unittest.TestCase):
    BUDGET = 8000
    ROUNDS = 3

    @classmethod
    def setUpClass(cls):
        cls.problems, cls.tokens, cls.ell = synthetic_pool()

    def run_method(self, method, seed=13):
        """Three rounds; B5 and the ablation see ell shifted a little each round, like a changing Student."""
        trained, out = set(), []
        for t in range(self.ROUNDS):
            ell = None
            if method == "B4":
                ell = self.ell
            elif method in ("B5", "ablation_shuffled_scores"):
                rng = random.Random(1000 * seed + t)
                ell = {k: v + (0 if t == 0 else rng.gauss(0, 0.05)) - 0.1 * (k in trained) for k, v in self.ell.items()}
            res = select(method, t, seed, self.problems, self.tokens, self.BUDGET, 1, ell, sorted(trained))
            out.append(res)
            trained |= set(res["selected"])
        return out

    def test_every_method_respects_budget_and_n_cap_every_round(self):
        longest = max(self.tokens.values())
        for method in ("B2", "B3", "B4", "B5", "ablation_shuffled_scores"):
            for res in self.run_method(method):
                pids = [self.problems[t] for t in res["selected"]]
                self.assertEqual(len(pids), len(set(pids)), method)
                self.assertLessEqual(res["tokens_used"], self.BUDGET, method)
                self.assertGreater(res["tokens_used"], self.BUDGET - longest, method)
                self.assertEqual(res["tokens_used"], sum(self.tokens[t] for t in res["selected"]))

    def test_b3_b4_never_repeat(self):
        for method in ("B3", "B4"):
            seen = set()
            for res in self.run_method(method):
                self.assertFalse(seen & set(res["selected"]), method)
                seen |= set(res["selected"])

    def test_same_seed_same_result(self):
        for method in ("B2", "B3", "B4", "B5", "ablation_shuffled_scores"):
            self.assertEqual([r["selected"] for r in self.run_method(method)],
                             [r["selected"] for r in self.run_method(method)], method)

    def test_b4_identical_across_seeds(self):
        """T7-1: required for the test-retest runs of T7-6."""
        self.assertEqual([r["selected"] for r in self.run_method("B4", 13)],
                         [r["selected"] for r in self.run_method("B4", 2026)])

    def test_b2_differs_by_seed_and_round(self):
        r13, r42 = self.run_method("B2", 13), self.run_method("B2", 42)
        self.assertNotEqual(r13[0]["selected"], r42[0]["selected"])
        self.assertNotEqual(r13[0]["selected"], r13[1]["selected"])

    def test_b4_b5_identical_in_round_0(self):
        """Same signal at S_0: this is why B5 can reuse B4's S_1 (task7_decisions.md)."""
        self.assertEqual(self.run_method("B4")[0]["selected"], self.run_method("B5")[0]["selected"])

    def test_b4_keeps_s0_band_b5_recomputes(self):
        b4, b5 = self.run_method("B4"), self.run_method("B5")
        self.assertEqual({r["ell_star"] for r in b4}, {b4[0]["ell_star"]})
        self.assertEqual(b4[2]["n_reference"], len(self.problems))
        self.assertEqual(b5[1]["n_reference"], len(self.problems) - len(b5[0]["selected"]))
        self.assertNotEqual(b5[0]["ell_star"], b5[1]["ell_star"])

    def test_b5_may_reselect(self):
        """Decision #22 forbids nothing here: a trajectory may be chosen again by B5."""
        ell = dict(self.ell)
        first = select("B5", 0, 13, self.problems, self.tokens, self.BUDGET, 1, ell)
        second = select("B5", 1, 13, self.problems, self.tokens, self.BUDGET, 1, ell, first["selected"])
        self.assertTrue(set(first["selected"]) & set(second["selected"]))

    def test_ablation_uses_its_own_seed(self):
        ell = dict(self.ell)
        res = select("ablation_shuffled_scores", 1, 13, self.problems, self.tokens, self.BUDGET, 1, ell)
        true_scores = score_checkpoint(ell)["l_proxy"]
        expected = shuffled_scores(true_scores, 13 * 100 + 1 + ABLATION_SEED_OFFSET)
        self.assertEqual({r["trajectory_id"]: r["score"] for r in res["rows"]}, expected)
        self.assertEqual({r["trajectory_id"]: r["l_proxy"] for r in res["rows"]}, true_scores)
        b2 = select("B2", 1, 13, self.problems, self.tokens, self.BUDGET, 1)
        self.assertNotEqual(res["selected"], b2["selected"])

    def test_log_rows_cover_the_pool_and_match_selected(self):
        for method in ("B2", "B3", "B4", "B5", "ablation_shuffled_scores"):
            res = self.run_method(method)[1]
            self.assertEqual({r["trajectory_id"] for r in res["rows"]}, set(self.problems), method)
            self.assertEqual({r["trajectory_id"] for r in res["rows"] if r["selected"]}, set(res["selected"]), method)

    def test_exhausted_pool_is_an_error(self):
        with self.assertRaises(ValueError):
            select("B2", 0, 13, self.problems, self.tokens, 10 ** 9, 1)

    def test_nll_must_cover_the_pool(self):
        partial = dict(list(self.ell.items())[:10])
        with self.assertRaises(ValueError):
            select("B5", 0, 13, self.problems, self.tokens, self.BUDGET, 1, partial)
        with self.assertRaises(ValueError):
            select("B5", 0, 13, self.problems, self.tokens, self.BUDGET, 1, None)


class TestProbeGroups(unittest.TestCase):
    def test_bins_are_ordered_by_length_and_deterministic(self):
        _, tokens, _ = synthetic_pool()
        groups = probe_groups(tokens, 50, 363636)
        self.assertEqual(groups, probe_groups(tokens, 50, 363636))
        self.assertEqual([len(g) for g in groups], [50] * 5)
        self.assertEqual(len({t for g in groups for t in g}), 250)
        means = [statistics.mean(tokens[t] for t in g) for g in groups]
        self.assertEqual(means, sorted(means))


if __name__ == "__main__":
    unittest.main()
