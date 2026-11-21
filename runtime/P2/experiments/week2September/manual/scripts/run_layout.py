#!/usr/bin/env python3
"""
Read-only access to a runs directory written by run_experiment.py. No torch.

  <runs-dir>/S0/{eval_dev,eval_test,nll}.jsonl
  <runs-dir>/<method>_seed<seed>/round_NNN/{train_set.json,selection_log.jsonl}
  <runs-dir>/<method>_seed<seed>/S<t>/{adapter/train_log.json,eval_dev.jsonl,eval_test.jsonl,nll.jsonl}
  <runs-dir>/timing.jsonl

Used by validate_runs.py, score_learnability.py and build_figures.py.
"""
import json
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from select_round import round_dir  # noqa: E402
from student_common import read_jsonl  # noqa: E402

RUN_NAME = re.compile(r"^(?P<method>.+)_seed(?P<seed>\d+)$")
METHOD_ORDER = ("B5", "B4", "B2", "B3", "ablation_shuffled_scores")


class Run:
    def __init__(self, path):
        self.path = Path(path)
        m = RUN_NAME.match(self.path.name)
        self.method, self.seed = m["method"], int(m["seed"])
        self.name = self.path.name

    def rounds(self):
        """Round indices that have a train set, in order."""
        out, t = [], 0
        while (round_dir(self.path, t) / "train_set.json").exists():
            out.append(t)
            t += 1
        return out

    def train_set(self, t):
        return json.loads((round_dir(self.path, t) / "train_set.json").read_text(encoding="utf-8"))

    def selection_log(self, t):
        path = round_dir(self.path, t) / "selection_log.jsonl"
        return read_jsonl(path) if path.exists() else None

    def checkpoint_dir(self, t, runs_dir):
        """S_t of this run; S_0 is shared."""
        return Path(runs_dir) / "S0" if t == 0 else self.path / f"S{t}"

    def train_log(self, t):
        """train_log of the round that produced S_{t+1}."""
        path = self.path / f"S{t + 1}" / "adapter" / "train_log.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def discover(runs_dir):
    """Runs sorted by method order, then seed."""
    runs = [Run(p) for p in Path(runs_dir).iterdir() if p.is_dir() and RUN_NAME.match(p.name)]
    rank = {m: i for i, m in enumerate(METHOD_ORDER)}
    return sorted(runs, key=lambda r: (rank.get(r.method, len(rank)), r.method, r.seed))


def load_eval(ckpt_dir, split):
    """(rows, summary) of one evaluation, or (None, None) when it is not there."""
    rows_path = Path(ckpt_dir) / f"eval_{split}.jsonl"
    summary_path = Path(ckpt_dir) / f"eval_{split}.summary.json"
    if not rows_path.exists() or not summary_path.exists():
        return None, None
    return read_jsonl(rows_path), json.loads(summary_path.read_text(encoding="utf-8"))


def load_timing(runs_dir):
    path = Path(runs_dir) / "timing.jsonl"
    return read_jsonl(path) if path.exists() else []


def average_ranks(values):
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for k in range(i, j + 1):
            ranks[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return ranks


def spearman(x, y):
    return statistics.correlation(average_ranks(x), average_ranks(y))


def jaccard(a, b):
    a, b = set(a), set(b)
    return len(a & b) / len(a | b) if a | b else 1.0
