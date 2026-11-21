#!/usr/bin/env python3
"""
Unit tests for eval_metrics.py, compare_eval_backends.compare, read_jsonl_resumable and the L_emp report. No GPU.

Usage (from experiments/week2September/manual/):
  python scripts/test_eval_metrics.py
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from compare_eval_backends import compare  # noqa: E402
from eval_metrics import score_output, summarize  # noqa: E402
from probe_lemp import average_ranks, report_groups, spearman  # noqa: E402
from student_common import load_capability_labels, load_test_rows, read_jsonl_resumable  # noqa: E402

GOOD = "REASONING:\n2 + 3 = 5\n\nANSWER:\n5"
WRONG = "REASONING:\n2 + 3 = 6\n\nANSWER:\n6"
NO_FORMAT = "2 + 3 = 5, so the result is 5"


def row(pid, text, n_out=10):
    return score_output({"problem_id": pid, "ground_truth": "5"}, "S0", text, n_out, 512)


class TestScoring(unittest.TestCase):
    def test_statuses(self):
        self.assertEqual(row("a", GOOD)["status"], "valid")
        self.assertEqual(row("a", WRONG)["status"], "invalid_answer")
        self.assertEqual(row("a", NO_FORMAT)["status"], "invalid_format")

    def test_invalid_format_is_wrong_but_can_be_lenient_correct(self):
        r = row("a", NO_FORMAT)
        self.assertTrue(r["lenient_correct"])
        s = summarize([r])
        self.assertEqual(s["accuracy"], 0)
        self.assertEqual(s["lenient_accuracy"], 1)
        self.assertEqual(s["format_compliance"], 0)

    def test_hit_max_tokens(self):
        self.assertTrue(row("a", GOOD, 512)["hit_max_tokens"])
        self.assertFalse(row("a", GOOD, 511)["hit_max_tokens"])

    def test_summary_rates(self):
        s = summarize([row("a", GOOD), row("b", WRONG), row("c", NO_FORMAT), row("d", GOOD)])
        self.assertEqual(s["accuracy"], 0.5)
        self.assertEqual(s["lenient_accuracy"], 0.75)
        self.assertEqual(s["format_compliance"], 0.75)
        self.assertEqual((s["n_valid"], s["n_invalid_answer"], s["n_invalid_format"]), (2, 1, 1))

    def test_by_capability_uses_labelled_problems_only(self):
        labels = {"a": ["addition"], "b": ["addition", "division"]}
        s = summarize([row("a", GOOD), row("b", WRONG), row("c", GOOD)], labels)
        self.assertEqual(s["n_problems_with_capability_labels"], 2)
        self.assertEqual(s["by_capability"]["addition"]["accuracy"], 0.5)
        self.assertEqual(s["by_capability"]["division"]["accuracy"], 0)
        self.assertEqual(s["by_capability"]["addition"]["n_problems"], 2)

    def test_empty_results_rejected(self):
        with self.assertRaises(ValueError):
            summarize([])


class TestData(unittest.TestCase):
    def test_test_split(self):
        rows = load_test_rows()
        self.assertEqual(len(rows), 1319)
        self.assertTrue(all(r["problem_id"].startswith("gsm8k_test_") for r in rows))

    def test_labels_are_the_85_supplement_problems(self):
        self.assertEqual(len(load_capability_labels()), 85)


class TestResumable(unittest.TestCase):
    def test_drops_only_a_truncated_last_line(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.jsonl"
            p.write_text('{"a": 1}\n{"a": 2}\n{"a"', encoding="utf-8")
            self.assertEqual(read_jsonl_resumable(p), [{"a": 1}, {"a": 2}])
            self.assertEqual(p.read_text(encoding="utf-8"), '{"a": 1}\n{"a": 2}\n')

    def test_corrupt_middle_line_raises(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.jsonl"
            p.write_text('{"a": 1}\n{"a"\n{"a": 2}\n', encoding="utf-8")
            with self.assertRaises(ValueError):
                read_jsonl_resumable(p)

    def test_missing_file_is_empty(self):
        self.assertEqual(read_jsonl_resumable("/nonexistent/x.jsonl"), [])


class TestCompare(unittest.TestCase):
    def test_rates(self):
        a = [row("a", GOOD), row("b", GOOD), row("only_a", GOOD)]
        b = [row("a", GOOD), row("b", WRONG), row("only_b", GOOD)]
        c = compare(a, b)
        self.assertEqual((c["n_common"], c["n_only_a"], c["n_only_b"]), (2, 1, 1))
        self.assertEqual(c["identical_output_rate"], 0.5)
        self.assertEqual((c["accuracy_a"], c["accuracy_b"]), (1, 0.5))


class TestLempReport(unittest.TestCase):
    def test_ranks_with_ties(self):
        self.assertEqual(average_ranks([10, 20, 20, 30]), [1, 2.5, 2.5, 4])

    def test_spearman_monotonic(self):
        self.assertAlmostEqual(spearman([1, 2, 3, 4, 5], [1, 4, 9, 16, 25]), 1)
        self.assertAlmostEqual(spearman([1, 2, 3, 4, 5], [5, 4, 3, 2, 1]), -1)

    def test_l_emp_is_change_over_b(self):
        groups = [["x", "y"]]
        out = report_groups(groups, {"x": 0.2, "y": 0.4}, 0.70, {(0, 13): 0.72, (0, 42): 0.74}, 7)
        self.assertAlmostEqual(out[0]["mean_acc_change"], 0.03)
        self.assertAlmostEqual(out[0]["l_emp"], 0.03 / 7)
        self.assertAlmostEqual(out[0]["mean_l_proxy_S0"], 0.3)


if __name__ == "__main__":
    unittest.main()
