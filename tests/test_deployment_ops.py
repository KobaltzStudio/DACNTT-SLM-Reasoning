"""Deployment safety checks with temporary data; no model calls."""
import argparse
import contextlib
import io
import tempfile
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "deployment"))
import ops


class DeploymentSafetyTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        self.package = self.root / "sealed"
        self.work = self.root / "work"
        self.package.mkdir()
        self.work.mkdir()

    def test_manual_live_approval_is_required_before_touching_package(self):
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as error:
                ops.main(["run", "P1-DEFICIT", "2", "--execute", "--work", str(self.work),
                          "--package", str(self.package), "--approve", "P1P2:13:S3"])
        self.assertEqual(error.exception.code, 2)
        self.assertEqual(list(self.work.iterdir()), [])

    def test_a_s2_training_and_foreign_eval_split_rejected(self):
        with self.assertRaisesRegex(ValueError, "cannot retrain"):
            ops.guard_plan("P1-DEFICIT", 2, [{"stage": "train_x", "command": []}])
        with self.assertRaisesRegex(ValueError, "must be D_dev"):
            ops.guard_plan("P1P2", 2, [{"stage": "eval", "command": ["python", "eval_student.py", "--split", "test"]}])

    def test_p1p2_must_use_parent_checkpoint_nll(self):
        with self.assertRaisesRegex(ValueError, "learnability checkpoint"):
            ops.guard_plan("P1P2", 3, [{"stage": "compute_nll", "command": ["--tag", "S0"]}])
        ops.guard_plan("P1P2", 3, [{"stage": "compute_nll", "command": ["--tag", "S2"]}])

    def test_traversal_and_case_collision_rejected(self):
        for name in ("../a", "/a", "a/file:stream", "a/../b", r"a\b"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                ops.relative(name)
        sums = self.root / "sums.txt"
        sums.write_text(f"{'a'*64}  dir/A\n{'b'*64}  dir/a\n", encoding="utf8")
        with self.assertRaisesRegex(ValueError, "Invalid SHA row"):
            ops.read_sums(sums)

    def test_append_only_prefix_allowed_and_overwrite_rejected(self):
        original = self.package / ops.A_S2_PREFIX
        target = self.work / ops.A_S2_PREFIX
        for path in (original, target):
            path.parent.mkdir(parents=True)
            path.write_bytes(b"old\r\n")
        target.write_bytes(b"old\r\nnew\n")
        ops.verify_work(self.package, self.work, {ops.A_S2_PREFIX: ops.sha(original)})
        self.assertEqual(original.read_bytes(), b"old\r\n")
        target.write_bytes(b"changed\nold\r\n")
        with self.assertRaisesRegex(ValueError, "prefix differs"):
            ops.verify_work(self.package, self.work, {ops.A_S2_PREFIX: ops.sha(original)})

    def test_windows_receipt_cannot_authorize_linux_run(self):
        record = {"status": "PASS", "platform": "win32", "package": str(self.package), "work": str(self.work),
                  "index_sha256": ops.INDEX_PIN, "python": sys.executable, "actions": [0,0,4,16]}
        with self.assertRaisesRegex(ValueError, "real Linux"):
            ops.receipt_matches(record, self.package, self.work)
        ops.receipt_matches(dict(record, platform="linux"), self.package, self.work)

    def test_collect_verify_then_block_overwrite_and_tamper(self):
        name = (ops.MANUAL / "runs/p1p2_integration/P1P2_seed13/S2/eval_dev.jsonl").as_posix()
        fixture = self.work / name
        fixture.parent.mkdir(parents=True)
        fixture.write_bytes(b"synthetic")
        logs = self.root / "logs"
        logs.mkdir()
        for internal in ("execution.log", "intent.json", "exit_code.txt"):
            (logs / internal).write_text("synthetic")
        receipt = logs / "execution.json"
        ops.write_json(receipt, {"schema": "p1p2.handoff.execution.v1", "scope": "P1P2:13:S2",
                                 "work": str(self.work), "status": "PASS", "index_sha256": ops.INDEX_PIN,
                                 "exit_code": 0, "outputs": {name: {"bytes": 9, "sha256": ops.sha(fixture)}}})
        result = self.root / "results"
        args = argparse.Namespace(receipt=receipt, output=result, package=self.package)
        ops.collect(args)
        pin = ops.sha(result / "RESULTS_SHA256SUMS.txt")
        ops.verify_results(result, pin)
        with self.assertRaises(FileExistsError):
            ops.collect(args)
        (result / name).write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "SHA mismatch"):
            ops.verify_results(result, pin)
