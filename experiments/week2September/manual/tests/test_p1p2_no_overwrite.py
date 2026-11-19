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

    def test_dry_run_never_publishes_checkpoint_log_for_existing_adapter(self):
        controller = Controller.__new__(Controller)
        controller.dry_run = True
        controller.actions = []
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            train_set = root / "train_set.json"
            selection_log = root / "selection_log.jsonl"
            model = root / "adapter"
            model.mkdir()
            train_log = model / "train_log.json"
            for path in (train_set, selection_log, train_log):
                path.write_text("{}", encoding="utf-8")
            destination = controller._checkpoint_log(
                root / "run", "P1P2", 13, 1, train_set, model, train_log
            )
            self.assertFalse(destination.parent.exists())
            self.assertEqual(controller.actions[0]["outputs"], [str(destination)])

if __name__ == '__main__': unittest.main()
