import unittest, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from p1p2_controller import build_parser, parse_checkpoints

class CliTests(unittest.TestCase):
    def test_matrix_arguments(self):
        args=build_parser().parse_args(['--methods','B2','B3','B4','B5','P1-DEFICIT','P1P2','--seeds','13','42','2026','--rounds','all','--resume'])
        self.assertEqual(args.methods,['B2','B3','B4','B5','P1-DEFICIT','P1P2'])
        self.assertEqual(args.seeds,[13,42,2026])
        self.assertTrue(args.resume)
        self.assertEqual(parse_checkpoints(args),[1,2,3])

    def test_range_excludes_start_checkpoint(self):
        args=build_parser().parse_args(['--method','P1P2','--seed','13','--from-checkpoint','S1','--to-checkpoint','S3'])
        self.assertEqual(parse_checkpoints(args),[2,3])

    def test_round_and_range_conflict(self):
        args=build_parser().parse_args(['--method','P1P2','--seed','13','--round','2','--to-checkpoint','S3'])
        with self.assertRaises(ValueError): parse_checkpoints(args)

    def test_invalid_range(self):
        args=build_parser().parse_args(['--method','P1P2','--seed','13','--from-checkpoint','S2','--to-checkpoint','S1'])
        with self.assertRaises(ValueError): parse_checkpoints(args)

if __name__ == '__main__': unittest.main()
