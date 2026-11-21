"""Fixture checks for G6, G7, and G8 analysis contracts."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_capability_learning_dynamics import canonicalize, mapped_checkpoint_path, SidecarRejected, validate_one
from build_p1p2_analysis_figures import draw, figure_data, observed, row_sources, selection_composition
from p1p2_paths import legacy_root
from select_checkpoint_on_dev import choose_checkpoint, score, select, verified_prediction
import test_p1p2_capability_state as state_fixture


class AnalysisTests(unittest.TestCase):
    def test_g6_maps_only_the_expected_external_g4_archive(self):
        with tempfile.TemporaryDirectory() as temp:
            p2 = Path(temp).resolve()
            manual = p2 / "experiments/week2September/manual"
            source = legacy_root("D:/Pipeline/P2/experiments/week2September/manual")
            checkpoint = "integration_staging/G4_CHECKPOINT_AUDIT/extracted_checkpoints/B4_seed13/S1"
            self.assertEqual(mapped_checkpoint_path(manual, f"D:/Pipeline/P2/{checkpoint}", source),
                             p2 / checkpoint)
            with self.assertRaises(ValueError):
                mapped_checkpoint_path(manual, "D:/Pipeline/P2/unknown/adapter", source)

    def test_g6_canonicalizes_exact_duplicates_and_blocks_conflicts(self):
        row = {"method": "B4", "seed": 13, "checkpoint": "S1", "valid": True,
               "prediction_sha256": "prediction", "checkpoint_sha256": "adapter", "fingerprint": "fp"}
        first = {**row, "sidecar_source": "a", "reasons": []}
        duplicate = {**row, "sidecar_source": "b", "reasons": []}
        self.assertEqual(canonicalize([first, duplicate]), {"a"})
        self.assertTrue(duplicate["duplicate"])
        alternate = {**row, "sidecar_source": "c", "prediction_sha256": "other", "reasons": []}
        self.assertEqual(canonicalize([first, alternate], {("B4", 13, "S1"): ("prediction", "adapter")}), {"a"})
        self.assertTrue(alternate["alternate_provenance"])
        self.assertEqual(canonicalize([first, alternate]), set())

    def test_g6_rejects_malformed_manifest_and_sidecar_mutations(self):
        for mutation in ("manifest", "missing_gold", "fingerprint", "capability", "lineage"):
            with self.subTest(mutation=mutation):
                fixture = state_fixture.CapabilityStateTests()
                fixture.setUp()
                try:
                    sidecar = fixture.sidecar
                    manifest = sidecar / "student_capability_evaluation_manifest.json"
                    if mutation == "manifest":
                        manifest.write_text("{", encoding="utf-8")
                        with self.assertRaises(json.JSONDecodeError):
                            validate_one(sidecar)
                        continue
                    filename = {
                        "missing_gold": "prediction_coverage_report.json", "fingerprint": "input_fingerprint.json",
                        "capability": "capability_metrics.jsonl", "lineage": "checkpoint_lineage.json",
                    }[mutation]
                    path = sidecar / filename
                    expected = {
                        "missing_gold": "gold_or_dev_coverage_mismatch", "fingerprint": "fingerprint_digest_mismatch",
                        "capability": "capability_rows_not_exactly_seven", "lineage": "manifest_lineage_identity_mismatch",
                    }[mutation]
                    if mutation == "capability":
                        path.write_text("\n".join(path.read_text().splitlines()[:-1]), encoding="utf-8")
                    else:
                        key, value = {"missing_gold": ("gold_matched_prediction_ids", 84),
                                      "fingerprint": ("fingerprint", "tampered"),
                                      "lineage": ("method", "B4")}[mutation]
                        state_fixture.write_json(path, {**json.loads(path.read_text()), key: value})
                    fixture._refresh_manifest_output(filename)
                    with self.assertRaisesRegex(SidecarRejected, expected):
                        validate_one(sidecar)
                finally:
                    fixture.tearDown()

    def test_g7_strict_scoring_extra_and_missing_ids_ties_and_duplicates(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "prediction.jsonl"
            rows = [{"problem_id": "in", "status": "valid"}, {"problem_id": "extra", "status": "valid"}]
            path.write_text("\n".join(map(json.dumps, rows)))
            self.assertEqual(score(path, {"in", "missing"})["accuracy"], .5)
            self.assertEqual(score(path, {"in", "missing"})["missing"], 1)
            self.assertEqual(choose_checkpoint([{"checkpoint": "S3", "correct": 1},
                                                {"checkpoint": "S0", "correct": 1}]), "S0")
            path.write_text("\n".join(map(json.dumps, rows + rows)))
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                score(path, {"in"})

    def test_g7_rejects_foreign_lineage_before_prediction(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            sidecar = root / "reports/p1p2_integration/capability_sidecars/P1P2_seed13_S2"
            sidecar.mkdir(parents=True)
            state_fixture.write_json(sidecar / "checkpoint_lineage.json", {"method": "P1P2", "seed": 13, "round": 1})
            with self.assertRaisesRegex(ValueError, "lineage identity mismatch"):
                verified_prediction(root, "P1P2", 2)

    def test_g7_partial_outputs_one_shared_s0_and_never_selects(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            split = root / "splits/p1p2_vfinal_2026-11-16"
            split.mkdir(parents=True)
            ids = [str(i) for i in range(500)]
            dev = split.parent / "d_dev_ids.txt"
            dev.write_text("\n".join(ids), encoding="utf-8")
            selected = split / "d_dev_select_ids.txt"
            selected.write_text("\n".join(ids[:415]), encoding="utf-8")
            digest = state_fixture.file_metadata(selected)["sha256"]
            state_fixture.write_json(split / "split_manifest.json", {"files": {selected.name: {"sha256": digest}}})
            prediction = root / "prediction.jsonl"
            prediction.write_text("\n".join(json.dumps({"problem_id": i, "status": "valid"}) for i in ids),
                                  encoding="utf-8")

            def verify(_root, method, checkpoint):
                if method == "P1P2" and checkpoint > 1:
                    raise FileNotFoundError("fixture S2/S3 incomplete")
                return prediction, {"fixture": True}

            with patch("select_checkpoint_on_dev.verified_prediction", side_effect=verify), \
                 patch("select_checkpoint_on_dev.publish_pair_no_overwrite") as publish:
                select(root, partial=True)
            manifest = json.loads(publish.call_args.args[3])
            self.assertEqual(manifest["status"], "PARTIAL")
            self.assertEqual(len(manifest["missing_checkpoints"]), 2)
            self.assertEqual(sum(row["checkpoint"] == "S0" for row in manifest["rows"]), 1)
            self.assertTrue(all(row["selected_checkpoint"] is None for row in manifest["rows"]))

    def test_g8_composition_and_isolated_renderer(self):
        counts = selection_composition([{"a", "b"}, {"b", "c"}, {"a", "b", "d"}])
        self.assertEqual(counts[-1], {"new": 1, "retained": 1, "readmitted": 1})
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaises(FileNotFoundError):
                figure_data(root, "selection_jaccard")
            self.assertEqual(list(root.iterdir()), [])
            output = root / "fixture.png"
            draw(output, "selection_composition", [{"method": "P1P2", "round": r, **row}
                                                     for r, row in enumerate(counts, 1)])
            self.assertEqual(output.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")

    def test_g8_partial_accepts_only_missing_artifacts(self):
        def missing_file():
            raise FileNotFoundError("checkpoint absent")

        missing = {}
        self.assertIsNone(observed(missing_file, missing, "P1P2 S2"))
        self.assertIn("checkpoint absent", missing["P1P2 S2"])
        with self.assertRaises(FileNotFoundError):
            observed(missing_file, None, "P1P2 S2")
        with self.assertRaises(ValueError):
            observed(lambda: int("bad fingerprint"), missing, "B4 S1")

    def test_g8_jaccard_csv_sources_resolve_historical_zero_based_rounds(self):
        first = "runs/main/B4_seed13/round_000/train_set.json"
        third = "runs/main/B4_seed13/round_002/train_set.json"
        second = "runs/main/B4_seed13/round_001/train_set.json"
        inputs = {first: "first", second: "second", third: "third"}
        row = {"method": "B4", "first_round": 1, "second_round": 3}
        self.assertEqual(row_sources("selection_jaccard", row, inputs), {first: "first", third: "third"})
