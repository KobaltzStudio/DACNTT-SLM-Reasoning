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

if __name__ == '__main__': unittest.main()
