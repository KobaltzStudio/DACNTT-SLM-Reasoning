import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("evaluate_student_capabilities.py")

spec = importlib.util.spec_from_file_location(
    "student_capability_evaluator",
    SCRIPT,
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class TestStudentCapabilityEvaluator(unittest.TestCase):

    def test_duplicate_prediction_ids_rejected(self):
        rows = [
            {"problem_id": "p1"},
            {"problem_id": "p1"},
        ]
        with self.assertRaises(ValueError):
            module.assert_unique_ids(rows, "test predictions")

    def test_missing_problem_id_rejected(self):
        with self.assertRaises(ValueError):
            module.assert_unique_ids(
                [{"problem_id": ""}],
                "test predictions",
            )

    def test_unknown_capability_rejected(self):
        with self.assertRaises(ValueError):
            module.parse_capabilities("addition;unknown")

    def test_multilabel_problem_counts_for_each_capability(self):
        rows = [
            {"problem_id": "p1", "capabilities": ["addition", "fraction"]},
            {"problem_id": "p2", "capabilities": ["addition"]},
        ]
        addition = sum("addition" in r["capabilities"] for r in rows)
        fraction = sum("fraction" in r["capabilities"] for r in rows)
        self.assertEqual(addition, 2)
        self.assertEqual(fraction, 1)

    def test_empty_support_returns_no_ci(self):
        self.assertEqual(
            module.wilson_interval(0, 0),
            (None, None),
        )

    def test_missing_prediction_is_reported_not_imputed(self):
        result = module.calculate_coverage(
            gold_ids={"p1", "p2"},
            prediction_ids={"p1"},
            dev_ids={"p1", "p2", "p3"},
        )
        self.assertEqual(result["matched_ids"], ["p1"])
        self.assertEqual(result["missing_prediction_ids"], ["p2"])

    def test_prediction_outside_dev_is_reported(self):
        result = module.calculate_coverage(
            gold_ids={"p1"},
            prediction_ids={"p1", "unknown"},
            dev_ids={"p1", "p2"},
        )
        self.assertEqual(
            result["prediction_ids_outside_d_dev"],
            ["unknown"],
        )

    def test_prediction_without_confirmed_gold_is_not_scored(self):
        result = module.calculate_coverage(
            gold_ids={"p1"},
            prediction_ids={"p1", "p2"},
            dev_ids={"p1", "p2"},
        )
        self.assertEqual(
            result["predictions_without_confirmed_gold"],
            ["p2"],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
