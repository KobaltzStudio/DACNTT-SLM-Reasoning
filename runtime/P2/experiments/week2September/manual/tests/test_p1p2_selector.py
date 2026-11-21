from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import p1p2_selector as selector


class SelectorUnitTests(unittest.TestCase):
    def test_percentile_average_ties(self):
        got = selector.average_percentile_ranks({"a": 1.0, "b": 1.0, "c": 3.0})
        self.assertAlmostEqual(got["a"], 0.25)
        self.assertAlmostEqual(got["b"], 0.25)
        self.assertAlmostEqual(got["c"], 1.0)

    def test_percentile_single_item(self):
        self.assertEqual(selector.average_percentile_ranks({"x": 9.0}), {"x": 0.5})

    def test_p1_is_mean_of_tag_deficits(self):
        pool = {"t1": {"capabilities": ["addition", "ratio"]}}
        deficits = {name: 0.2 for name in selector.TAXONOMY}
        deficits["ratio"] = 0.8
        self.assertAlmostEqual(selector.calculate_p1_scores(pool, deficits)["t1"], 0.5)

    def test_pool_rejects_unverified(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pool = root / "pool.jsonl"
            dpool = root / "dpool.txt"
            pool.write_text(json.dumps({"trajectory_id": "t", "problem_id": "p", "metadata": {"verification_status": "pending"}, "capabilities": ["addition"]}) + "\n", encoding="utf-8")
            dpool.write_text("p\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "must be valid"):
                selector.load_pool(pool, dpool)

    def test_previous_train_set_checks_method_seed_round_pool_and_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "train_set.json"
            payload = {"schema_version": "p1p2.train-set.v1", "method": "P1P2", "training_seed": 13,
                       "round": 1, "pool_sha256": "abc", "trajectory_ids": ["t1"]}
            path.write_text(json.dumps(payload), encoding="utf-8")
            got = selector.load_previous_train_ids([path], {"t1": "p1"}, "P1P2", 13, 2, "abc")
            self.assertEqual(got, ["t1"])
            payload["training_seed"] = 42
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "seed mismatch"):
                selector.load_previous_train_ids([path], {"t1": "p1"}, "P1P2", 13, 2, "abc")

    def test_previous_train_set_requires_complete_round_lineage(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "train_set.json"
            path.write_text(json.dumps({"schema_version": "p1p2.train-set.v1", "method": "P1P2",
                                        "training_seed": 13, "round": 1, "pool_sha256": "abc",
                                        "trajectory_ids": ["t1"]}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "rounds incomplete"):
                selector.load_previous_train_ids([path], {"t1": "p1"}, "P1P2", 13, 3, "abc")

    def test_nll_validates_supplied_pool_hash_and_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pool = root / "pool.jsonl"
            pool.write_text('{"x":1}\n', encoding="utf-8")
            nll = root / "nll.jsonl"
            nll.write_text(json.dumps({"trajectory_id": "t1", "checkpoint": "S0", "n_tokens": 5, "ell": 1.2}) + "\n", encoding="utf-8")
            summary = {"checkpoint": "S0", "pool_sha256": hashlib.sha256(pool.read_bytes()).hexdigest(), "n_trajectories": 1}
            nll.with_suffix(".summary.json").write_text(json.dumps(summary), encoding="utf-8")
            values, _ = selector.load_nll(nll, {"t1": 5}, "S0", pool)
            self.assertEqual(values, {"t1": 1.2})
            summary["pool_sha256"] = "wrong"
            nll.with_suffix(".summary.json").write_text(json.dumps(summary), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "supplied pool"):
                selector.load_nll(nll, {"t1": 5}, "S0", pool)

    def test_nll_requires_exact_token_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pool = root / "pool.jsonl"
            pool.write_text("{}\n", encoding="utf-8")
            nll = root / "nll.jsonl"
            nll.write_text(json.dumps({"trajectory_id": "t1", "checkpoint": "S0", "n_tokens": 5, "ell": 1.2}) + "\n", encoding="utf-8")
            nll.with_suffix(".summary.json").write_text(json.dumps({"checkpoint": "S0", "pool_sha256": selector.sha256_file(pool), "n_trajectories": 2}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "does not cover token table"):
                selector.load_nll(nll, {"t1": 5, "t2": 6}, "S0", pool)

    def test_publish_pair_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            train, log = root / "train_set.json", root / "selection_log.jsonl"
            train.write_text("existing", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                selector.publish_pair_no_overwrite(train, log, b"new", b"log")
            self.assertEqual(train.read_text(encoding="utf-8"), "existing")
            self.assertFalse(log.exists())

    def test_publish_pair_creates_both_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            train, log = root / "nested" / "train_set.json", root / "nested" / "selection_log.jsonl"
            selector.publish_pair_no_overwrite(train, log, b'{"ok":true}', b'{"row":1}\n')
            self.assertEqual(train.read_bytes(), b'{"ok":true}')
            self.assertEqual(log.read_bytes(), b'{"row":1}\n')

    def test_cli_does_not_expose_alpha_override(self):
        options = [action.option_strings for action in selector.build_parser()._actions]
        self.assertNotIn(["--alpha"], options)


if __name__ == "__main__":
    unittest.main(verbosity=2)
