#!/usr/bin/env python3
"""
Unit tests for the post-run analysis helpers (run_layout.py, build_figures.py). No GPU, no torch.

Usage (from experiments/week2September/manual/):
  python scripts/test_analysis.py
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_figures import mcnemar_exact, mean_sd  # noqa: E402
from run_layout import RUN_NAME, jaccard, spearman  # noqa: E402


class TestHelpers(unittest.TestCase):
    def test_mcnemar_exact(self):
        self.assertAlmostEqual(mcnemar_exact(0, 6), 2 / 64)       # all 6 discordant pairs one way
        self.assertEqual(mcnemar_exact(0, 0), 1.0)
        self.assertEqual(mcnemar_exact(5, 5), 1.0)                # capped at 1
        self.assertAlmostEqual(mcnemar_exact(3, 7), mcnemar_exact(7, 3))

    def test_jaccard(self):
        self.assertEqual(jaccard({"a", "b"}, {"b", "c"}), 1 / 3)
        self.assertEqual(jaccard([], []), 1.0)

    def test_spearman(self):
        self.assertAlmostEqual(spearman([1, 2, 3], [10, 20, 30]), 1)
        self.assertAlmostEqual(spearman([1, 2, 3], [3, 2, 1]), -1)

    def test_mean_sd_single_value(self):
        m, sd = mean_sd([0.5])
        self.assertEqual(m, 0.5)
        self.assertNotEqual(sd, sd)  # NaN with one seed

    def test_run_name(self):
        m = RUN_NAME.match("ablation_shuffled_scores_seed2026")
        self.assertEqual((m["method"], m["seed"]), ("ablation_shuffled_scores", "2026"))
        self.assertIsNone(RUN_NAME.match("S0"))


if __name__ == "__main__":
    unittest.main()
