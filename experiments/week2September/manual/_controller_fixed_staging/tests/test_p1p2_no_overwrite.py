import tempfile, unittest, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from p1p2_controller import Controller

class NoOverwriteTests(unittest.TestCase):
    def test_partial_selection_pair_is_rejected(self):
        obj=Controller.__new__(Controller)
        obj.dry_run=False; obj.actions=[]
        obj.py=sys.executable; obj.scripts=Path('/scripts')
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); run=root/'run'; out=run/'round_001'; out.mkdir(parents=True)
            (out/'train_set.json').write_text('{}')
            with self.assertRaises(RuntimeError):
                obj._ensure_selection_p1('P1P2',13,1,run,root,root/'state.json',None)

    def test_forbidden_namespace_is_rejected(self):
        obj=Controller.__new__(Controller); obj.root=Path('/project')
        with self.assertRaises(ValueError):
            obj.safe_output(Path('/project/runs/main/B5_seed13'),'run')

if __name__ == '__main__': unittest.main()
