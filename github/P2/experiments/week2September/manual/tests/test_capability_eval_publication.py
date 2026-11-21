from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import capability_eval as evaluator


class EvaluatorPublicationTests(unittest.TestCase):
    def test_publish_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            stage, target = root / ".stage", root / "final"
            stage.mkdir()
            (stage / "payload.txt").write_text("ok", encoding="utf-8")
            evaluator.publish_staged_directory(stage, target)
            self.assertTrue(target.is_dir())
            self.assertFalse(stage.exists())

    def test_collision_preserves_stage(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            stage, target = root / ".stage", root / "final"
            stage.mkdir()
            target.mkdir()
            marker = stage / "marker"
            marker.write_text("preserve", encoding="utf-8")
            with self.assertRaisesRegex(FileExistsError, "OUTPUT_COLLISION"):
                evaluator.publish_staged_directory(stage, target)
            self.assertTrue(marker.is_file())

    def test_transient_permission_error_retries(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            stage, target = root / ".stage", root / "final"
            stage.mkdir()
            real_rename = evaluator.os.rename
            calls = {"n": 0}

            def flaky(src, dst):
                calls["n"] += 1
                if calls["n"] == 1:
                    raise PermissionError(5, "transient")
                return real_rename(src, dst)

            with patch.object(evaluator.os, "rename", side_effect=flaky):
                with patch.object(evaluator.time, "sleep", return_value=None):
                    evaluator.publish_staged_directory(stage, target)
            self.assertEqual(calls["n"], 2)
            self.assertTrue(target.is_dir())

    def test_persistent_permission_error_keeps_stage(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            stage, target = root / ".stage", root / "final"
            stage.mkdir()
            marker = stage / "marker"
            marker.write_text("preserve", encoding="utf-8")
            with patch.object(
                evaluator.os, "rename",
                side_effect=PermissionError(5, "persistent"),
            ):
                with patch.object(evaluator.time, "sleep", return_value=None):
                    with self.assertRaisesRegex(
                        RuntimeError, "PUBLICATION_FAILED_AFTER_RETRIES"
                    ):
                        evaluator.publish_staged_directory(stage, target)
            self.assertTrue(marker.is_file())
            self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
