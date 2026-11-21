"""CPU-only acceptance of the final D_test gate; the evaluator is always a stub."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import run_final_d_test as gate


class FinalDTestTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        self.test_ids = {f"test-{i}" for i in range(1319)}
        digest = lambda x: hashlib.sha256(x).hexdigest()
        data = {}
        for key, ids in (("d_test", self.test_ids), ("d_dev", {"dev"}), ("d_pool", {"pool"})):
            content = ("\n".join(sorted(ids)) + "\n").encode()
            path = f"splits/{key}_ids.txt"
            self.write(path, content.replace(b"\n", b"\r\n"))
            data[key] = {"path": path, "sha256": digest(content)}
        dataset = "".join(json.dumps({"problem_id": i}) + "\n" for i in sorted(self.test_ids)).encode()
        dataset_name = "data/raw/gsm8k_test.jsonl"
        self.write(dataset_name, dataset)
        manifest = {"files": data, "counts": {"d_test": 1319, "d_dev": 1, "d_pool": 1},
                    "sources": {"gsm8k_test": {"path": dataset_name, "sha256": digest(dataset)}}}
        canonical = (json.dumps(manifest) + "\n").encode()
        source = self.write("splits/split_manifest.json", canonical.replace(b"\n", b"\r\n"))
        self.write_json("splits/p1p2_vfinal_2026-11-16/split_manifest.json", {"counts": {"d_test": 1319},
                        "source_split_manifest": {"path": "splits/split_manifest.json", "sha256": gate.sha256(source)}})
        self.student = {"model": "q", "revision": "rev"}
        self.write_json("config/experiment_config.json", {"student": self.student,
                        "splits": {"manifest": "splits/split_manifest.json", "manifest_sha256": digest(canonical)}})
        for relative in gate.EVALUATOR_FILES:
            if not (self.root / relative).exists():
                self.write(relative, b"# fixture")
        self.eval_sha = gate.sha256_json(gate.evaluator_sources(self.root))
        self.adapter = self.write("models/p1p2_integration/P1P2_seed13/student_ckpt_002/weights", b"test adapter").parent
        self.winner = {"method": "P1P2", "checkpoint": "S2", "selected_checkpoint": "S2",
                       "checkpoint_lineage": {"checkpoint_sha256": gate.sha256(self.adapter)}}
        self.selection = self.write_json("G7.json", {"status": "FINAL", "schema_version": gate.VERSION,
                        "policy": gate.SELECTION_POLICY, "rows": [self.winner], "missing_checkpoints": []})

    def write(self, relative, content):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def write_json(self, name, data):
        return self.write(name, json.dumps(data).encode())

    def evaluate_stub(self, args):
        self.assertEqual((args.split, args.tag, args.adapter, args.dtype, args.limit),
                         ("test", "P1P2_seed13_S2", str(self.adapter), "bf16", None))
        rows = [{"problem_id": i, "checkpoint": args.tag, "status": "invalid_answer",
                 "lenient_correct": True} for i in sorted(self.test_ids)]
        rows[0]["status"] = "valid"
        args.out.write_text("".join(json.dumps(row) + "\n" for row in rows))
        args.summary.write_text(json.dumps({**self.student, "checkpoint": args.tag, "split": "test",
                                "n_problems": 1319, "n_valid": 1, "accuracy": 1 / 1319, "adapter": args.adapter}))

    def run_gate(self, evaluator, **changes):
        args = {"root": self.root, "method": "P1P2", "selection": self.selection,
                "selection_sha": gate.sha256(self.selection), "evaluator_sha": self.eval_sha}
        with patch.object(gate, "selection_records", return_value=([self.winner], [])):
            return gate.run(**(args | changes), evaluator=evaluator)

    def test_split_accepts_exact_crlf_and_rejects_tamper(self):
        self.assertEqual(gate.audit_split(self.root)[0], self.test_ids)
        self.write("splits/d_test_ids.txt", b"test-0\n")
        with self.assertRaisesRegex(ValueError, "split fingerprint mismatch"):
            gate.audit_split(self.root)

    def test_hash_pins_and_partial_selection_block_evaluator(self):
        evaluator = Mock()
        for field, pattern in [("evaluator_sha", "evaluator SHA"), ("selection_sha", "manifest SHA")]:
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, pattern):
                self.run_gate(evaluator, **{field: "wrong"})
        data = gate.read_json(self.selection)
        self.write_json("G7.json", {**data, "status": "PARTIAL"})
        with self.assertRaisesRegex(ValueError, "G7 must be FINAL"):
            self.run_gate(evaluator)
        evaluator.assert_not_called()

    def test_g7_and_adapter_mismatch_block_evaluator(self):
        evaluator = Mock()
        data = gate.read_json(self.selection)
        self.write_json("G7.json", {**data, "rows": []})
        with self.assertRaisesRegex(ValueError, "differ from verified"):
            self.run_gate(evaluator)
        self.write_json("G7.json", data)
        (self.adapter / "weights").write_bytes(b"else")
        with self.assertRaisesRegex(ValueError, "checkpoint SHA"):
            self.run_gate(evaluator)
        evaluator.assert_not_called()

    def test_stub_publishes_strict_metrics_and_refuses_conflicting_output(self):
        result = self.run_gate(self.evaluate_stub)
        report = gate.read_json(result / "provenance.json")
        self.assertEqual(report["n_correct"], 1)
        self.assertEqual(report["strict_accuracy"], 1 / 1319)
        self.assertEqual(report["confidence_interval"]["method"], "Wilson")
        self.assertEqual(report["prediction_sha256"], gate.sha256(result / "predictions.jsonl"))
        evaluator = Mock()
        with self.assertRaises(FileExistsError):
            self.run_gate(evaluator)
        evaluator.assert_not_called()

    def test_prediction_validation_rejects_duplicate_and_wrong_tag(self):
        ids = {"x", "y"}
        for rows in ([{"problem_id": "x", "checkpoint": "S1", "status": "valid"}] * 2,
                     [{"problem_id": i, "checkpoint": "S2", "status": "valid"} for i in ids]):
            with self.assertRaisesRegex(ValueError, "coverage, status or tag"):
                gate.summarize_test(rows, ids, "S1", {})
