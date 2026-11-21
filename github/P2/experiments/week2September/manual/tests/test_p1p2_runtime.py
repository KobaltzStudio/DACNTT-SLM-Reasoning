"""Exercise runtime orchestration with synthetic model subprocesses."""
import contextlib
import io
import json
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from capability_eval import EXPECTED_SUPPORT
from p1p2_controller import Controller, main, sha256
from p1p2_paths import artifact_path, legacy_root


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        self.enterContext(contextlib.redirect_stdout(io.StringIO()))
        self.enterContext(patch.object(Controller, "_validate_root_inputs"))
        self.calls = []
        self.fail = None
        self.controller = Controller(self.root, resume=True, dry_run=False, runner=self.dispatch)
        c = self.controller
        write(c.config, {"student": {"model": "fixture", "revision": "fixture"}})
        jsonl(c.pool, [{"trajectory_id": "t1"}])
        jsonl(c.tokens, [{"trajectory_id": "t1", "response_tokens": 1}])
        self.ids = [f"fixture-{index}" for index in range(500)]
        c.dev_ids.parent.mkdir()
        c.dev_ids.write_text("\n".join(self.ids), encoding="utf-8")
        write(c.gold_manifest, {"gold_version": "vFinal", "supplement_count": 85})
        gold = []
        for index, identifier in enumerate(self.ids[:85]):
            capabilities = [
                cap for cap, count in EXPECTED_SUPPORT.items()
                if (index - (73 if cap == "addition" else 0)) % 85 < count
            ]
            gold.append({"problem_id": identifier, "capabilities_manual": capabilities})
        jsonl(c.gold_labels, gold)
        c.approval.parent.mkdir(parents=True)
        c.approval.write_text("problem_id,review_status,human_approval\n" +
                              "".join(f"{identifier},APPROVED_NO_LABEL_CHANGE,APPROVED_BY_USER_FIXTURE\n"
                                      for identifier in self.ids[:85]), encoding="utf-8")
        write(c.s0_reference, {"fixture": True})
        self.predictions(c.s0_prediction, "S0")
        self.real_script("run_p1p2_post_eval.py", [
            "--method", "SHARED", "--seed", "0", "--round", "0",
            "--prediction", c.s0_prediction, "--checkpoint", c.s0_reference,
            "--output-dir", c.s0_sidecar, "--gold-manifest", c.gold_manifest,
            "--gold-labels", c.gold_labels, "--approval-csv", c.approval,
            "--dev-ids", c.dev_ids, "--config", c.config,
        ])

    def real_script(self, name, arguments):
        result = subprocess.run([sys.executable, "-B", str(SCRIPTS / name), *map(str, arguments)],
                                cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def predictions(self, path, tag):
        jsonl(path, [{"problem_id": identifier, "checkpoint": tag, "status": "valid"} for identifier in self.ids])
        write(path.with_suffix(".summary.json"), {"split": "dev", "n_problems": 500, "checkpoint": tag})

    def dispatch(self, cmd):
        script = Path(cmd[1]).name
        args = dict(zip(cmd[2::2], cmd[3::2]))
        self.calls.append((script, args))
        initial_state = script == "p1p2_capability_state.py" and Path(args["--out"]).name == "selection_round_001.json"
        if self.fail == script and not initial_state:
            raise subprocess.CalledProcessError(71, cmd)
        c = self.controller
        if script == "compute_nll.py":
            out = Path(args["--out"])
            adapter = args.get("--adapter")
            tag = args["--tag"]
            jsonl(out, [{"checkpoint": tag, "trajectory_id": "t1", "n_tokens": 1, "ell": .5}])
            write(out.with_suffix(".summary.json"), {
                "checkpoint": tag, "adapter": adapter, "adapter_sha256": sha256(Path(adapter)) if adapter else None,
                "pool_sha256": sha256(c.pool), "n_trajectories": 1, "model": "fixture", "revision": "fixture",
            })
        elif script == "p1p2_selector.py":
            out = Path(args["--out-dir"])
            seed, round_no = int(args["--seed"]), int(args["--round"])
            method, nll = args["--method"], args.get("--nll")
            identity = {"method": method, "round": round_no, "source_checkpoint": f"S{round_no-1}"}
            write(out / "train_set.json", {
                **identity, "schema_version": "p1p2.train-set.v1", "training_seed": seed,
                "pool_sha256": sha256(c.pool), "tokens_sha256": sha256(c.tokens), "config_sha256": sha256(c.config),
                "state_file": args["--state"], "state_sha256": sha256(Path(args["--state"])),
                "nll_file": nll, "nll_sha256": sha256(Path(nll)) if nll else None, "trajectory_ids": ["t1"],
            })
            jsonl(out / "selection_log.jsonl", [{**identity, "seed": seed, "trajectory_id": "t1", "selected": True}])
        elif script == "train_round.py":
            out = Path(args["--adapter-dir"])
            out.mkdir()
            write(out / "adapter_config.json", {"peft_type": "LORA"})
            (out / "adapter_model.safetensors").write_bytes(b"fixture-weights")
            write(out / "train_log.json", {
                "seed": int(args["--seed"]), "data_order_seed": int(args["--seed"]),
                "train_set_sha256": sha256(Path(args["--train-set"])),
                "config_sha256": sha256(c.config), "pool_sha256": sha256(c.pool),
                "checkpoint_parent": args.get("--init-adapter", "student_ckpt_000"),
                "checkpoint_parent_sha256": sha256(Path(args["--init-adapter"])) if "--init-adapter" in args else None,
            })
        elif script == "eval_student.py":
            self.assertEqual(args["--split"], "dev")
            out = Path(args["--out"])
            if out.exists():
                completed = {json.loads(line)["problem_id"] for line in out.read_text().splitlines()}
                with out.open("a", encoding="utf-8") as stream:
                    for identifier in self.ids:
                        if identifier not in completed:
                            stream.write(json.dumps({"problem_id": identifier, "checkpoint": args["--tag"],
                                                     "status": "valid"}) + "\n")
                write(out.with_suffix(".summary.json"), {"split": "dev", "n_problems": 500, "checkpoint": args["--tag"]})
            else:
                self.predictions(out, args["--tag"])
        else:
            self.assertIn(script, {"run_p1p2_post_eval.py", "p1p2_capability_state.py"})
            self.real_script(script, cmd[2:])

    def test_three_rounds_and_exact_resume(self):
        c = self.controller
        c.run_method_seed("P1P2", 9999, [1, 2, 3])
        stages = [name for name, _ in self.calls]
        self.assertEqual(stages[0], "p1p2_capability_state.py")
        self.assertEqual(stages[1:], ["compute_nll.py", "p1p2_selector.py", "train_round.py",
                                     "eval_student.py", "run_p1p2_post_eval.py", "p1p2_capability_state.py"] * 3)
        train = [args for name, args in self.calls if name == "train_round.py"]
        self.assertNotIn("--init-adapter", train[0])
        self.assertEqual(train[1]["--init-adapter"], train[0]["--adapter-dir"])
        self.assertEqual(train[2]["--init-adapter"], train[1]["--adapter-dir"])
        nll = [args for name, args in self.calls if name == "compute_nll.py"]
        self.assertEqual([args["--tag"] for args in nll], ["S0", "S1", "S2"])
        self.assertEqual(nll[2]["--adapter"], train[1]["--adapter-dir"])
        self.assertIn("p1p2_integration_custom", train[0]["--adapter-dir"])
        self.calls.clear()
        before = [sha256(Path(args["--adapter-dir"])) for args in train]
        c.run_method_seed("P1P2", 9999, [2, 3])
        self.assertEqual(self.calls, [])
        self.assertEqual(before, [sha256(Path(args["--adapter-dir"])) for args in train])
        self.assertFalse((self.root / "models/task7").exists())

    def test_subprocess_failures_stop_and_resume(self):
        for seed, script in enumerate(("compute_nll.py", "p1p2_selector.py", "train_round.py",
                                      "eval_student.py", "run_p1p2_post_eval.py", "p1p2_capability_state.py"), 9000):
            with self.subTest(script=script):
                self.calls.clear()
                self.fail = script
                with self.assertRaises(subprocess.CalledProcessError) as error:
                    self.controller.run_method_seed("P1P2", seed, [1])
                self.assertEqual(error.exception.returncode, 71)
                self.assertEqual(self.calls[-1][0], script)
                if script == "p1p2_capability_state.py":
                    self.assertEqual(self.calls[-2][0], "run_p1p2_post_eval.py")
                self.fail = None
                self.controller.run_method_seed("P1P2", seed, [1])
                self.calls.clear()
                self.controller.run_method_seed("P1P2", seed, [1])
                self.assertEqual(self.calls, [])

    def test_log_publication_failure_does_not_retrain(self):
        c = self.controller
        with patch("p1p2_controller.publish_bytes_no_overwrite", side_effect=OSError("fixture publication failure")):
            with self.assertRaisesRegex(OSError, "fixture publication failure"):
                c.run_method_seed("P1-DEFICIT", 13, [1])
        self.assertEqual(self.calls[-1][0], "eval_student.py")
        self.assertNotIn("compute_nll.py", [name for name, _ in self.calls])
        self.calls.clear()
        c.run_method_seed("P1-DEFICIT", 13, [1])
        self.assertEqual([name for name, _ in self.calls], ["run_p1p2_post_eval.py", "p1p2_capability_state.py"])

    def test_existing_lock_is_preserved(self):
        run = self.root / "runs/p1p2_integration/P1P2_seed13"
        run.mkdir(parents=True)
        lock = run / ".controller.lock"
        lock.write_text("fixture owner")
        with self.assertRaisesRegex(RuntimeError, "Run is locked"):
            main(["--manual-root", str(self.root), "--method", "P1P2", "--seed", "13", "--round", "1"])
        self.assertEqual(lock.read_text(), "fixture owner")

    def test_checkpoint_log_requires_a_line_boundary_before_appending(self):
        self.controller.run_method_seed("P1-DEFICIT", 13, [1])
        run = self.root / "runs/p1p2_integration/P1-DEFICIT_seed13"
        log = run / "checkpoint_log.jsonl"
        original = log.read_bytes().rstrip(b"\r\n")
        log.write_bytes(original)
        with self.assertRaisesRegex(ValueError, "unterminated last record"):
            self.controller._checkpoint_log(run, "P1-DEFICIT", 13, 2, run / "round_001/train_set.json",
                                            self.root / "models/p1p2_integration/P1-DEFICIT_seed13/student_ckpt_001",
                                            self.root / "models/p1p2_integration/P1-DEFICIT_seed13/student_ckpt_001/train_log.json")
        self.assertEqual(log.read_bytes(), original)

    def test_partial_prediction_resumes_without_replacing_existing_rows(self):
        c = self.controller
        self.fail = "eval_student.py"
        with self.assertRaises(subprocess.CalledProcessError):
            c.run_method_seed("P1-DEFICIT", 13, [1])
        prediction = self.root / "runs/p1p2_integration/P1-DEFICIT_seed13/S1/eval_dev.jsonl"
        jsonl(prediction, [{"problem_id": self.ids[0], "checkpoint": "P1-DEFICIT_seed13_S1", "status": "valid"}])
        prefix = prediction.read_bytes()
        self.fail = None
        self.calls.clear()
        c.run_method_seed("P1-DEFICIT", 13, [1])
        self.assertTrue(prediction.read_bytes().startswith(prefix))
        self.assertEqual(self.calls[0][0], "eval_student.py")
        self.assertNotIn("train_round.py", [stage for stage, _ in self.calls])

    @unittest.skipUnless(os.name == "nt", "creates archived Windows paths through the native fixture runner")
    def test_windows_staging_reuses_s1_and_plans_only_remaining_s2_stages(self):
        original = self.controller
        original.run_method_seed("P1P2", 13, [1])
        self.fail = "eval_student.py"
        with self.assertRaises(subprocess.CalledProcessError):
            original.run_method_seed("P1P2", 13, [2])
        run_path = Path("runs/p1p2_integration/P1P2_seed13")
        prefix_path = run_path / "S2/eval_dev.jsonl"
        jsonl(self.root / prefix_path, [{"problem_id": identifier, "checkpoint": "P1P2_seed13_S2", "status": "valid"}
                                       for identifier in self.ids[:75]])
        staging = Path(self.enterContext(tempfile.TemporaryDirectory())) / "staging"
        shutil.copytree(self.root, staging)
        log = staging / run_path / "checkpoint_log.jsonl"
        fingerprint = sha256(log)
        c = Controller(staging, resume=True, dry_run=True, legacy_windows_root=str(self.root),
                       runner=lambda command: self.assertEqual(command, [], "dry-run invoked a subprocess"))
        c.run_method_seed("P1P2", 13, [1])
        self.assertEqual(c.actions, [])
        c.run_method_seed("P1P2", 13, [2])
        stages = [entry["stage"] for entry in c.actions]
        self.assertEqual(stages, ["eval_dev_P1P2_seed13_S2", "checkpoint_log_P1P2_seed13_S2",
                                  "post_eval_P1P2_seed13_S2", "capability_state_P1P2_seed13_selection_3"])
        self.assertEqual(sha256(log), fingerprint)
        self.assertEqual((staging / prefix_path).read_bytes(), (self.root / prefix_path).read_bytes())
        wrong = Controller(staging, resume=True, dry_run=True, legacy_windows_root="Z:/wrong")
        with self.assertRaisesRegex(ValueError, "does not match"):
            wrong.run_method_seed("P1P2", 13, [1])

    def test_legacy_path_mapping_is_explicit_and_rejects_ambiguous_paths(self):
        source = legacy_root("D:/Pipeline/Manual")
        self.assertEqual(artifact_path(self.root, "d:/pipeline/manual/runs/a.json", source),
                         self.root / "runs/a.json")
        for path in ("D:/Pipeline/Manual/../other/a", "D:/Pipeline/Manual2/runs/a",
                     "D:drive-relative", "D:/Pipeline/Manual/file:stream",
                     str(self.root / "file:stream"), str(self.root)):
            with self.subTest(path=path), self.assertRaises(ValueError):
                artifact_path(self.root, path, source)

    def test_partial_evaluation_requires_newline_before_append(self):
        c = self.controller
        self.fail = "eval_student.py"
        with self.assertRaises(subprocess.CalledProcessError):
            c.run_method_seed("P1-DEFICIT", 13, [1])
        prediction = self.root / "runs/p1p2_integration/P1-DEFICIT_seed13/S1/eval_dev.jsonl"
        row = {"problem_id": self.ids[0], "checkpoint": "P1-DEFICIT_seed13_S1", "status": "valid"}
        prediction.write_text(json.dumps(row), encoding="utf-8")
        prior = prediction.read_bytes()
        self.calls.clear()
        with self.assertRaisesRegex(RuntimeError, "line boundary"):
            c.run_method_seed("P1-DEFICIT", 13, [1])
        self.assertEqual(self.calls, [])
        self.assertEqual(prediction.read_bytes(), prior)

    def test_hook_rejects_incomplete_input_without_sidecar(self):
        c = self.controller
        prediction = self.root / "partial.jsonl"
        jsonl(prediction, [{"problem_id": self.ids[0], "checkpoint": "P1P2_seed13_S1", "status": "valid"}])
        sidecar = self.root / "P1P2_seed13_S1"
        result = subprocess.run([sys.executable, "-B", str(SCRIPTS / "run_p1p2_post_eval.py"),
                                 "--method", "P1P2", "--seed", "13", "--round", "1",
                                 "--prediction", str(prediction), "--output-dir", str(sidecar),
                                 "--checkpoint", str(c.s0_reference), "--gold-manifest", str(c.gold_manifest),
                                 "--gold-labels", str(c.gold_labels), "--approval-csv", str(c.approval),
                                 "--dev-ids", str(c.dev_ids), "--config", str(c.config)],
                                cwd=self.root, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Prediction coverage mismatch", result.stderr)
        self.assertFalse(sidecar.exists())

    def test_partial_adapter_and_corrupt_intent_are_preserved(self):
        c = self.controller
        adapter = self.root / "models/p1p2_integration/P1-DEFICIT_seed13/student_ckpt_001"
        adapter.mkdir(parents=True)
        weights = adapter / "adapter_model.safetensors"
        weights.write_bytes(b"partial")
        with self.assertRaisesRegex(FileExistsError, "interrupted training"):
            c.run_method_seed("P1-DEFICIT", 13, [1])
        self.assertEqual(weights.read_bytes(), b"partial")
        self.fail = "eval_student.py"
        with self.assertRaises(subprocess.CalledProcessError):
            c.run_method_seed("P1-DEFICIT", 42, [1])
        intent = self.root / "runs/p1p2_integration/P1-DEFICIT_seed42/S1/eval_dev.intent.json"
        write(intent, {"adapter_sha256": "wrong"})
        fingerprint = sha256(intent)
        self.calls.clear()
        with self.assertRaisesRegex(ValueError, "evaluation provenance mismatch"):
            c.run_method_seed("P1-DEFICIT", 42, [1])
        self.assertEqual(self.calls, [])
        self.assertEqual(sha256(intent), fingerprint)

    def test_dry_run_creates_no_model_or_run_outputs(self):
        c = Controller(self.root, resume=False, dry_run=True, runner=self.dispatch)
        c.run_method_seed("P1P2", 9999, [1, 2, 3])
        self.assertEqual(self.calls, [])
        self.assertFalse((self.root / "runs/p1p2_integration_custom").exists())
        self.assertFalse((self.root / "models").exists())
