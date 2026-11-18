from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import p1p2_artifact_manager as manager


class ArtifactManagerTests(unittest.TestCase):
    def test_sha256_file_matches_hashlib(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.bin"
            path.write_bytes(b"abc")
            self.assertEqual(manager.sha256_file(path), hashlib.sha256(b"abc").hexdigest())

    def test_canonical_json_is_key_order_independent(self):
        self.assertEqual(manager.sha256_json({"a": 1, "b": 2}), manager.sha256_json({"b": 2, "a": 1}))

    def test_fingerprint_and_verify_source_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            a, b = root / "a.txt", root / "b.txt"
            a.write_text("alpha", encoding="utf-8")
            b.write_text("beta", encoding="utf-8")
            fp = manager.fingerprint_files({"a": a, "b": b})
            self.assertTrue(manager.verify_fingerprint(fp))
            self.assertTrue(manager.verify_fingerprint_files(fp))

    def test_fingerprint_detects_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.txt"
            path.write_text("before", encoding="utf-8")
            fp = manager.fingerprint_files({"input": path})
            path.write_text("after", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "mismatch"):
                manager.verify_fingerprint_files(fp)

    def test_fingerprint_rejects_missing_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                manager.fingerprint_files({"missing": Path(tmp) / "missing.txt"})

    def test_fingerprint_rejects_duplicate_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "same.txt"
            path.write_text("x", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Duplicate fingerprint path"):
                manager.fingerprint_files({"one": path, "two": path})

    def test_ensure_no_overwrite_rejects_existing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "existing.txt"
            path.write_text("protected", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                manager.ensure_no_overwrite([path])
            self.assertEqual(path.read_text(encoding="utf-8"), "protected")

    def test_publish_bytes_creates_file_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested" / "artifact.bin"
            manager.publish_bytes_no_overwrite(path, b"first")
            self.assertEqual(path.read_bytes(), b"first")
            with self.assertRaises(FileExistsError):
                manager.publish_bytes_no_overwrite(path, b"second")
            self.assertEqual(path.read_bytes(), b"first")

    def test_publish_json_is_valid_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "manifest.json"
            manager.publish_json_no_overwrite(path, {"ok": True, "value": 3})
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"ok": True, "value": 3})

    def test_publish_pair_creates_both_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first, second = root / "a.bin", root / "b.bin"
            manager.publish_pair_no_overwrite(first, b"A", second, b"B")
            self.assertEqual(first.read_bytes(), b"A")
            self.assertEqual(second.read_bytes(), b"B")

    def test_publish_pair_refuses_overwrite_without_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first, second = root / "a.bin", root / "b.bin"
            first.write_bytes(b"protected")
            with self.assertRaises(FileExistsError):
                manager.publish_pair_no_overwrite(first, b"new-A", second, b"new-B")
            self.assertEqual(first.read_bytes(), b"protected")
            self.assertFalse(second.exists())

    def test_publish_pair_rolls_back_first_if_second_publish_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first, second = root / "a.bin", root / "b.bin"
            real_link = manager.os.link
            calls = {"n": 0}
            def controlled_link(source, destination):
                calls["n"] += 1
                if calls["n"] == 2:
                    raise OSError("simulated second publication failure")
                return real_link(source, destination)
            with mock.patch.object(manager.os, "link", side_effect=controlled_link):
                with self.assertRaisesRegex(OSError, "simulated"):
                    manager.publish_pair_no_overwrite(first, b"A", second, b"B")
            self.assertFalse(first.exists())
            self.assertFalse(second.exists())
            self.assertEqual(list(root.glob("*.tmp")), [])

    def test_publish_manifest_attaches_fingerprint(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.json"
            source.write_text('{"x":1}', encoding="utf-8")
            target = root / "manifest.json"
            manager.publish_manifest_no_overwrite(target, {"run_id": "test"}, {"source": source})
            payload = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(payload["run_id"], "test")
            self.assertTrue(manager.verify_fingerprint(payload["input_fingerprint"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
