import json, tempfile, unittest, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from p1p2_controller import Controller

class ResumeTests(unittest.TestCase):
    def test_completed_prediction_is_recognized(self):
        obj=Controller.__new__(Controller)
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); obj.dev_ids=root/'dev.txt'
            ids=[f'id{i}' for i in range(500)]
            obj.dev_ids.write_text('\n'.join(ids),encoding='utf-8')
            pred=root/'pred.jsonl'
            pred.write_text(''.join(json.dumps({'problem_id':x,'status':'valid','checkpoint':'TAG'})+'\n' for x in ids),encoding='utf-8')
            pred.with_suffix('.summary.json').write_text(json.dumps({'checkpoint':'TAG','split':'dev','n_problems':500}),encoding='utf-8')
            self.assertTrue(obj._valid_prediction(pred,'TAG'))

    def test_partial_prediction_is_not_complete(self):
        obj=Controller.__new__(Controller)
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); obj.dev_ids=root/'dev.txt'
            ids=[f'id{i}' for i in range(500)]
            obj.dev_ids.write_text('\n'.join(ids),encoding='utf-8')
            pred=root/'pred.jsonl'; pred.write_text(json.dumps({'problem_id':'id0','status':'valid','checkpoint':'TAG'})+'\n')
            pred.with_suffix('.summary.json').write_text(json.dumps({'checkpoint':'TAG','split':'dev','n_problems':1}),encoding='utf-8')
            self.assertFalse(obj._valid_prediction(pred,'TAG'))

if __name__ == '__main__': unittest.main()
