import json
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from p1p2_controller import Controller, parse_checkpoints, build_parser

class ControllerPolicyTests(unittest.TestCase):
    def test_checkpoint_round_mapping(self):
        cases = [(['--method','P1P2','--seed','13','--round','2'], [2]),
                 (['--method','P1P2','--seed','13','--from-checkpoint','S1','--to-checkpoint','S3'], [2,3]),
                 (['--method','P1P2','--seed','13','--rounds','all'], [1,2,3])]
        for argv, expected in cases:
            args = build_parser().parse_args(argv)
            self.assertEqual(parse_checkpoints(args), expected)

    def test_p1_deficit_command_never_receives_nll(self):
        obj = Controller.__new__(Controller)
        obj.py = sys.executable
        obj.scripts = Path('/project/scripts')
        obj.pool = Path('/project/pool.jsonl')
        obj.tokens = Path('/project/tokens.jsonl')
        obj.d_pool = Path('/project/d_pool.txt')
        obj.config = Path('/project/config.json')
        obj.dry_run = True
        obj.actions = []
        obj.emit = lambda label, cmd, outputs=(): obj.actions.append({'label':label,'cmd':[str(x) for x in cmd]})
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); run=root/'runs/P1-DEFICIT_seed13'; out=run/'round_001'
            state=root/'state.json'; state.write_text('{}')
            train, log = obj._ensure_selection_p1('P1-DEFICIT',13,1,run,root,state,None)
            command=obj.actions[0]['cmd']
            self.assertNotIn('--nll', command)
            self.assertIn('--method', command)
            self.assertEqual(train.parent.name,'round_001')

    def test_p1p2_selection_requires_current_nll_argument(self):
        obj = Controller.__new__(Controller)
        obj.py=sys.executable; obj.scripts=Path('/project/scripts')
        obj.pool=Path('/project/pool.jsonl'); obj.tokens=Path('/project/tokens.jsonl')
        obj.d_pool=Path('/project/d_pool.txt'); obj.config=Path('/project/config.json')
        obj.dry_run=True; obj.actions=[]
        obj.emit=lambda label,cmd,outputs=(): obj.actions.append([str(x) for x in cmd])
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); state=root/'state.json'; state.write_text('{}')
            nll=root/'S1_nll.jsonl'
            obj._ensure_selection_p1('P1P2',13,2,root/'run',root,state,nll)
            cmd=obj.actions[0]
            self.assertIn('--nll',cmd)
            self.assertEqual(cmd[cmd.index('--nll')+1],str(nll))


    def test_p2_existing_selection_guard_uses_target_checkpoint(self):
        obj = Controller.__new__(Controller)
        obj.resume = False
        obj.dry_run = False
        obj.root = Path("/")
        obj.actions = []
        with tempfile.TemporaryDirectory() as td:
            run = Path(td)
            out = run / "round_001"
            out.mkdir()
            (out / "train_set.json").write_text(json.dumps({
                "method": "B4", "training_seed": 13, "round": 1
            }), encoding="utf-8")
            (out / "selection_log.jsonl").write_text("", encoding="utf-8")
            # Existing selection without --resume must be rejected, not crash
            # with NameError from the former undefined round_no variable.
            with self.assertRaises(FileExistsError):
                obj._ensure_selection_p2("B4", 13, 2, run, None)

    def test_hook_forwards_all_gold_and_dev_inputs(self):
        obj = Controller.__new__(Controller)
        obj.py = sys.executable
        obj.scripts = Path("/project/scripts")
        obj.root = Path("/project")
        obj.gold_manifest = Path("/tmp/gold_manifest.json")
        obj.gold_labels = Path("/tmp/gold_labels.jsonl")
        obj.approval = Path("/tmp/approval.csv")
        obj.dev_ids = Path("/tmp/dev_ids.txt")
        obj.config = Path("/tmp/config.json")
        obj.actions = []
        obj.emit = lambda label, cmd, outputs=(): obj.actions.append([str(x) for x in cmd])
        with tempfile.TemporaryDirectory() as td:
            paths = [obj.gold_manifest, obj.gold_labels, obj.approval, obj.dev_ids, obj.config]
            for path in paths:
                path.write_text("fixture", encoding="utf-8")
            run = Path(td) / "run"
            model = Path(td) / "model"
            report = Path(td) / "report"
            train_set = Path(td) / "train_set.json"
            selection_log = Path(td) / "selection_log.jsonl"
            train_set.write_text("{}", encoding="utf-8")
            selection_log.write_text("", encoding="utf-8")
            obj._hook("P1P2", 13, 2, Path(td)/"pred.jsonl", model, run, model,
                      report, train_set, selection_log)
            cmd = obj.actions[0]
            for flag in ("--gold-manifest", "--gold-labels", "--approval-csv",
                         "--dev-ids", "--config", "--train-set", "--selection-log",
                         "--train-log", "--checkpoint-log"):
                self.assertIn(flag, cmd)

if __name__ == '__main__': unittest.main()
