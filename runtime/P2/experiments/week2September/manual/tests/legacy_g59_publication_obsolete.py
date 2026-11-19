from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import run_p1p2_post_eval as hook


class PublicationTests(unittest.TestCase):
    def test_publish_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            stage = root / ".stage"
            target = root / "final"
            stage.mkdir()
            (stage / "payload.txt").write_text("ok", encoding="utf-8")

            hook.publish_staged_directory(stage, target)

            self.assertFalse(stage.exists())
            self.assertEqual(
                (target / "payload.txt").read_text(encoding="utf-8"),
                "ok",
            )

    def test_destination_collision_is_rejected_and_stage_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            stage = root / ".stage"
            target = root / "final"
            stage.mkdir()
            target.mkdir()
            marker = stage / "recovery.txt"
            marker.write_text("preserve", encoding="utf-8")

            with self.assertRaisesRegex(FileExistsError, "OUTPUT_COLLISION"):
                hook.publish_staged_directory(stage, target)

            self.assertTrue(marker.is_file())
            self.assertEqual(marker.read_text(encoding="utf-8"), "preserve")

    def test_transient_permission_error_retries(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            stage = root / ".stage"
            target = root / "final"
            stage.mkdir()
            (stage / "payload.txt").write_text("ok", encoding="utf-8")

            real_rename = hook.os.rename
            calls = {"n": 0}

            def flaky_rename(src, dst):
                calls["n"] += 1
                if calls["n"] == 1:
                    raise PermissionError(5, "transient test failure")
                return real_rename(src, dst)

            with patch.object(hook.os, "rename", side_effect=flaky_rename):
                with patch.object(hook.time, "sleep", return_value=None):
                    hook.publish_staged_directory(stage, target)

            self.assertEqual(calls["n"], 2)
            self.assertTrue(target.is_dir())
            self.assertFalse(stage.exists())

    def test_terminal_permission_error_preserves_stage(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            stage = root / ".stage"
            target = root / "final"
            stage.mkdir()
            marker = stage / "recovery.txt"
            marker.write_text("preserve", encoding="utf-8")

            with patch.object(
                hook.os, "rename",
                side_effect=PermissionError(5, "persistent test failure"),
            ):
                with patch.object(hook.time, "sleep", return_value=None):
                    with self.assertRaisesRegex(
                        RuntimeError,
                        "PUBLICATION_FAILED_AFTER_RETRIES",
                    ):
                        hook.publish_staged_directory(stage, target)

            self.assertTrue(marker.is_file())
            self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
