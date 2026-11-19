"""Read-only release planning and model-free reproduction of the mixed-newline A S2 resume."""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path.cwd().resolve()
PACKAGE = Path("C:/Users/PC - NGHI/Desktop/Pipeline/p1p2_unified/runpod_package_20261119_004529") / "P2/experiments/week2September/manual"
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "tests")]
from p1p2_controller import Controller, read_json, read_jsonl, sha256
from student_common import read_jsonl_resumable
from test_p1p2_runtime import RuntimeTests, write

A = "P1-DEFICIT"
B = "P1P2"
A_RUN = Path("runs/p1p2_integration/P1-DEFICIT_seed13")
A_MODEL = Path("models/p1p2_integration/P1-DEFICIT_seed13/student_ckpt_002")
TAG = "P1-DEFICIT_seed13_S2"

def read_only():
    plans = {}
    def deny(*args, **kwargs):
        raise AssertionError("No model or controller subprocess is permitted in the release audit")
    for base in (ROOT, PACKAGE):
        prediction = base / A_RUN / "S2/eval_dev.jsonl"
        prefix = prediction.read_bytes()
        rows = [json.loads(line) for line in prefix.splitlines(keepends=True)]
        ids = (base / "splits/d_dev_ids.txt").read_text(encoding="utf-8-sig").split()
        seen = {row["problem_id"] for row in rows}
        assert len(ids) == len(set(ids)) == 500
        assert len(rows) == len(seen) == 75 and seen <= set(ids)
        assert all(row["checkpoint"] == TAG for row in rows) and prefix.endswith(b"\n")
        assert not prediction.with_suffix(".summary.json").exists()
        remaining = [identifier for identifier in ids if identifier not in seen]
        assert len(remaining) == 425
        intent = read_json(prediction.with_name("eval_dev.intent.json"))
        adapter = base / A_MODEL
        weights = adapter / "adapter_model.safetensors"
        train_log = read_json(adapter / "train_log.json")
        assert train_log["steps"] == 26
        assert intent["adapter_sha256"] == sha256(adapter) and weights.is_file()
        per_root = {}
        with contextlib.redirect_stdout(io.StringIO()):
            for group, rounds, n in [(A, [1], 0), (B, [1], 0), (A, [2], 4), (B, [2, 3], 16)]:
                c = Controller(base, dry_run=True, resume=True, runner=deny, backend="hf", dtype="bf16",
                               micro_batch=1, nll_batch=1, eval_batch=1, legacy_windows_root=str(ROOT))
                c.run_method_seed(group, 13, rounds)
                assert len(c.actions) == n
                stages = [a["stage"] for a in c.actions]
                commands = [a["command"] for a in c.actions]
                assert all("test" not in cmd and "--split=test" not in cmd for cmd in commands)
                if group == A and rounds == [2]:
                    assert stages == ["eval_dev_P1-DEFICIT_seed13_S2", "checkpoint_log_P1-DEFICIT_seed13_S2",
                          "post_eval_P1-DEFICIT_seed13_S2", "capability_state_P1-DEFICIT_seed13_selection_3"]
                    assert Path(commands[0][commands[0].index("--adapter") + 1]) == adapter
                if group == B and rounds == [2, 3]:
                    nll = [cmd for stage, cmd in zip(stages, commands) if stage.startswith("compute_nll")]
                    trainers = [cmd for stage, cmd in zip(stages, commands) if stage.startswith("train_")]
                    assert [cmd[cmd.index("--tag") + 1] for cmd in nll] == ["S1", "S2"]
                    assert all(n[ n.index("--adapter") + 1] == t[t.index("--init-adapter") + 1]
                               for n, t in zip(nll, trainers))
                    assert [Path(cmd[cmd.index("--adapter") + 1]).name for cmd in nll] == [
                        "student_ckpt_001", "student_ckpt_002"]
                per_root[f"{group}/{rounds}"] = c.actions
        assert prediction.read_bytes() == prefix
        assert sha256(adapter) == intent["adapter_sha256"]
        plans[str(base)] = {"prefix_sha256": sha256(prediction), "rows_present": len(rows),
                            "rows_remaining": len(remaining), "steps_already_trained": train_log["steps"],
                            "adapter_sha256": sha256(adapter), "plans": per_root}
    assert len({value["prefix_sha256"] for value in plans.values()}) == 1
    with (HERE / "release_dry_run.json").open("x", encoding="utf8") as f:
        json.dump(plans, f, indent=2)
    print("Read-only source/package plans agree; real prefix remains 75/500, adapter 26 steps, 425 missing.")

class ReleaseResumeTest(RuntimeTests):
    def test_a_s2_mixed_line_endings_preserves_exact_prefix(self):
        c = self.controller
        c.run_method_seed(A, 13, [1])
        self.fail = "eval_student.py"
        with self.assertRaises(subprocess.CalledProcessError):
            c.run_method_seed(A, 13, [2])
        prediction = self.root / A_RUN / "S2/eval_dev.jsonl"
        rows = [{"problem_id": identifier, "checkpoint": TAG, "status": "valid"}
                for identifier in self.ids[:75]]
        prefix = b"".join(json.dumps(r).encode() + b"\r\n" for r in rows)
        prediction.parent.mkdir(parents=True, exist_ok=True)
        prediction.write_bytes(prefix)
        adapter = self.root / A_MODEL
        initial_hash = sha256(adapter)
        original_dispatch = self.dispatch
        events = []
        def dispatch(cmd):
            name = Path(cmd[1]).name
            events.append(name)
            if name == "eval_student.py":
                args = dict(zip(cmd[2::2], cmd[3::2]))
                self.assertEqual(args["--split"], "dev")
                self.assertEqual(Path(args["--adapter"]), adapter)
                checked = read_jsonl_resumable(prediction)
                self.assertEqual(prediction.read_bytes(), prefix)
                done = {row["problem_id"] for row in checked}
                todo = [i for i in self.ids if i not in done]
                self.assertEqual(len(todo), 425)
                # Write exactly the emulator output a Linux appender would add.
                with prediction.open("ab") as f:
                    for identifier in todo:
                        f.write(json.dumps({"problem_id": identifier, "checkpoint": TAG,
                                           "status": "valid"}).encode() + b"\n")
                write(prediction.with_suffix(".summary.json"), {"split": "dev", "checkpoint": TAG,
                                                                 "n_problems": 500, "accuracy": 1.0})
                return
            elif name == "run_p1p2_post_eval.py":
                self.assertEqual(len(read_jsonl(prediction)), 500)
                self.assertTrue(prediction.read_bytes().startswith(prefix))
            original_dispatch(cmd)
        self.fail = None
        c.runner = dispatch
        c.run_method_seed(A, 13, [2])
        self.assertEqual(events, ["eval_student.py", "run_p1p2_post_eval.py", "p1p2_capability_state.py"])
        self.assertEqual(sha256(adapter), initial_hash)
        self.assertTrue(prediction.read_bytes().startswith(prefix))
        self.assertEqual(len({r["problem_id"] for r in read_jsonl(prediction)}), 500)
        self.assertFalse((self.root / A_RUN / "S3").exists())
        self.assertTrue((self.root / "reports/p1p2_integration/capability_state/P1-DEFICIT_seed13").is_dir())
        events.clear()
        c.run_method_seed(A, 13, [2])
        self.assertEqual(events, [])

if __name__ == "__main__":
    read_only()
    suite = unittest.TestSuite([ReleaseResumeTest("test_a_s2_mixed_line_endings_preserves_exact_prefix")])
    raise SystemExit(not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful())
