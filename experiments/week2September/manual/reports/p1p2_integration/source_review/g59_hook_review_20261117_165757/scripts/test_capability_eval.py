#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import capability_eval as adapter


class CapabilityEvalIntegrationTests(unittest.TestCase):

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

        self.inputs = self.root / "inputs"
        self.inputs.mkdir()

        self.out_root = self.root / "sidecars"

        self.dev_ids = [
            f"dev_{index:04d}" for index in range(500)
        ]
        self.gold_ids = self.dev_ids[:85]

        self.dev_ids_path = self.inputs / "d_dev_ids.txt"
        self.dev_ids_path.write_text(
            "\n".join(self.dev_ids) + "\n",
            encoding="utf-8",
        )

        self.gold_path = self.inputs / "gold.jsonl"
        self.approval_path = self.inputs / "approval.csv"
        self.prediction_path = self.inputs / "predictions.jsonl"
        self.manifest_path = self.inputs / "gold_manifest.json"
        self.config_path = self.inputs / "experiment_config.json"

        self.checkpoint_path = self.inputs / "checkpoint"
        self.checkpoint_path.mkdir()
        (self.checkpoint_path / "adapter_model.safetensors").write_bytes(
            b"synthetic-test-checkpoint"
        )

        self.config_path.write_text(
            json.dumps({"test_fixture": True}),
            encoding="utf-8",
        )

        self.manifest_path.write_text(
            json.dumps({
                "gold_version": "vFinal",
                "supplement_count": 85,
            }),
            encoding="utf-8",
        )

        self._write_gold()
        self._write_approval()
        self._write_predictions()

        self.run_id = "B4_seed13_S1"

    def tearDown(self):
        self.temp.cleanup()

    def _write_gold(self):
        support = adapter.EXPECTED_SUPPORT

        rows = {
            problem_id: {
                "problem_id": problem_id,
                "capabilities_manual": [],
                "difficulty_manual": "medium",
            }
            for problem_id in self.gold_ids
        }

        cursor = 0

        for capability, count in support.items():
            for offset in range(count):
                index = (cursor + offset) % len(self.gold_ids)
                problem_id = self.gold_ids[index]
                rows[problem_id]["capabilities_manual"].append(capability)

            cursor = (cursor + count) % len(self.gold_ids)

        if any(not row["capabilities_manual"] for row in rows.values()):
            raise AssertionError(
                "Test fixture produced a Gold record without labels"
            )

        observed = {
            capability: sum(
                capability in row["capabilities_manual"]
                for row in rows.values()
            )
            for capability in support
        }

        if observed != support:
            raise AssertionError(
                f"Fixture support mismatch: {observed} != {support}"
            )

        with self.gold_path.open("w", encoding="utf-8") as stream:
            for row in rows.values():
                stream.write(json.dumps(row, ensure_ascii=False))
                stream.write(chr(10))

    def _write_approval(self, ids=None):
        ids = ids or self.gold_ids

        with self.approval_path.open(
            "w", encoding="utf-8-sig", newline=""
        ) as stream:
            writer = csv.DictWriter(
                stream,
                fieldnames=[
                    "problem_id",
                    "review_status",
                    "human_approval",
                ],
            )
            writer.writeheader()

            for problem_id in ids:
                writer.writerow({
                    "problem_id": problem_id,
                    "review_status": "APPROVED_NO_LABEL_CHANGE",
                    "human_approval": "APPROVED_BY_USER_TEST",
                })

    def _write_predictions(self, make_first_valid=True):
        with self.prediction_path.open(
            "w", encoding="utf-8"
        ) as stream:
            for index, problem_id in enumerate(self.dev_ids):
                status = "invalid_answer"

                if make_first_valid and index == 0:
                    status = "valid"

                row = {
                    "problem_id": problem_id,
                    "status": status,
                }
                stream.write(json.dumps(row) + "\n")

    def _args(self):
        return [
            "capability_eval.py",
            "--run-id", self.run_id,
            "--method", "B4",
            "--seed", "13",
            "--round", "1",
            "--checkpoint", str(self.checkpoint_path),
            "--dev-predictions", str(self.prediction_path),
            "--gold-manifest", str(self.manifest_path),
            "--gold-labels", str(self.gold_path),
            "--approval-csv", str(self.approval_path),
            "--dev-ids", str(self.dev_ids_path),
            "--config", str(self.config_path),
            "--out-root", str(self.out_root),
        ]

    def _run_adapter(self):
        with patch("sys.argv", self._args()):
            adapter.main()

    def test_wilson_interval(self):
        low, high = adapter.wilson_interval(5, 10)

        self.assertIsNotNone(low)
        self.assertIsNotNone(high)
        self.assertLessEqual(low, 0.5)
        self.assertGreaterEqual(high, 0.5)
        self.assertLessEqual(low, high)

    def test_strict_status_policy(self):
        self.assertTrue(
            adapter.strict_correct({"status": "valid"})
        )
        self.assertFalse(
            adapter.strict_correct({"status": "invalid_answer"})
        )
        self.assertFalse(
            adapter.strict_correct({"status": "invalid_format"})
        )

        with self.assertRaises(ValueError):
            adapter.strict_correct({"status": "unknown"})

        # A lenient-only field must not be accepted as strict evidence.
        with self.assertRaises(ValueError):
            adapter.strict_correct({"lenient_correct": True})

    def test_sidecar_creation_and_outputs(self):
        self._run_adapter()

        out_dir = self.out_root / self.run_id
        self.assertTrue(out_dir.is_dir())

        for name in adapter.REQUIRED_OUTPUTS:
            self.assertTrue(
                (out_dir / name).is_file(),
                f"Missing output: {name}",
            )

        rows = adapter.read_jsonl(
            out_dir / "capability_metrics.jsonl"
        )
        self.assertEqual(len(rows), 7)

        actual_support = {
            row["capability"]: row["n_support"]
            for row in rows
        }
        self.assertEqual(
            actual_support,
            adapter.EXPECTED_SUPPORT,
        )

        coverage = adapter.read_json(
            out_dir / "prediction_coverage_report.json"
        )
        self.assertEqual(coverage["status"], "PASS")
        self.assertEqual(coverage["prediction_records"], 500)
        self.assertEqual(coverage["gold_records"], 85)
        self.assertEqual(
            coverage["strict_correctness_policy"],
            "status == valid",
        )

    def test_identical_rerun_reuses_without_modification(self):
        self._run_adapter()

        out_dir = self.out_root / self.run_id
        manifest_before = adapter.read_json(
            out_dir / "student_capability_evaluation_manifest.json"
        )

        hashes_before = {
            name: adapter.sha256_file(out_dir / name)
            for name in adapter.REQUIRED_OUTPUTS
        }

        output = StringIO()
        with redirect_stdout(output):
            self._run_adapter()

        self.assertIn("REUSE: PASS", output.getvalue())

        hashes_after = {
            name: adapter.sha256_file(out_dir / name)
            for name in adapter.REQUIRED_OUTPUTS
        }

        self.assertEqual(hashes_before, hashes_after)

        manifest_after = adapter.read_json(
            out_dir / "student_capability_evaluation_manifest.json"
        )
        self.assertEqual(
            manifest_before["input_hashes"],
            manifest_after["input_hashes"],
        )

    def test_changed_prediction_rejected_for_existing_run_id(self):
        self._run_adapter()

        self._write_predictions(make_first_valid=False)

        with self.assertRaisesRegex(
            RuntimeError,
            "INPUT_FINGERPRINT_MISMATCH",
        ):
            self._run_adapter()

    def test_approval_id_mismatch_rejected(self):
        bad_ids = self.gold_ids[:-1]
        self._write_approval(ids=bad_ids)

        with self.assertRaisesRegex(
            ValueError,
            "Approval/Gold ID set mismatch",
        ):
            self._run_adapter()

    def test_approved_source_clarification_is_accepted(self):
        with self.approval_path.open(
            "r", encoding="utf-8-sig", newline=""
        ) as stream:
            rows = list(csv.DictReader(stream))

        rows[0]["review_status"] = "APPROVED_WITH_SOURCE_CLARIFICATION"

        with self.approval_path.open(
            "w", encoding="utf-8-sig", newline=""
        ) as stream:
            writer = csv.DictWriter(
                stream,
                fieldnames=[
                    "problem_id",
                    "review_status",
                    "human_approval",
                ],
            )
            writer.writeheader()
            writer.writerows(rows)

        self._run_adapter()

        out_dir = self.out_root / self.run_id
        self.assertTrue(
            (out_dir / "student_capability_evaluation_manifest.json").is_file()
        )

    def test_unapproved_review_status_is_rejected(self):
        with self.approval_path.open(
            "r", encoding="utf-8-sig", newline=""
        ) as stream:
            rows = list(csv.DictReader(stream))

        rows[0]["review_status"] = "PENDING_HUMAN_REVIEW"

        with self.approval_path.open(
            "w", encoding="utf-8-sig", newline=""
        ) as stream:
            writer = csv.DictWriter(
                stream,
                fieldnames=[
                    "problem_id",
                    "review_status",
                    "human_approval",
                ],
            )
            writer.writeheader()
            writer.writerows(rows)

        with self.assertRaisesRegex(
            ValueError,
            "Gold review status is not approved",
        ):
            self._run_adapter()

    def test_no_overwrite_of_partial_sidecar(self):
        out_dir = self.out_root / self.run_id
        out_dir.mkdir(parents=True)

        marker = out_dir / "do_not_overwrite.txt"
        marker.write_text("preserve-me", encoding="utf-8")

        with self.assertRaisesRegex(
            RuntimeError,
            "EXISTING_PARTIAL_SIDECAR",
        ):
            self._run_adapter()

        self.assertEqual(
            marker.read_text(encoding="utf-8"),
            "preserve-me",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
