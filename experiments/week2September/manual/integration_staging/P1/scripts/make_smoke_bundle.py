#!/usr/bin/env python3
"""
Pack exactly the files the Task 5 smoke test needs into one zip for Google Colab.

The zip keeps paths relative to experiments/week2September/manual/ and contains
MANIFEST.sha256 so the notebook can verify the upload. Nothing outside this list is shipped.

Usage (from experiments/week2September/manual/):
  python scripts/make_smoke_bundle.py --out smoke_bundle.zip
"""
import argparse
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from student_common import MANUAL_DIR, sha256_file  # noqa: E402

FILES = [
    "scripts/answer_utils.py",
    "scripts/student_common.py",
    "scripts/generate_teacher_trajectories_batch.py",  # source of PROMPT_TEMPLATE (drift check)
    "scripts/eval_student.py",
    "scripts/select_smoke_train_set.py",
    "scripts/train_round.py",
    "scripts/compute_nll.py",
    "scripts/analyze_smoke_test.py",
    "config/experiment_config.json",
    "splits/d_dev_ids.txt",
    "data/raw/gsm8k_train.jsonl",
    "trajectory/pool/batch_100_teacher_verified.jsonl",
    "notebooks/smoke_test_colab.ipynb",
]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=Path("smoke_bundle.zip"))
    args = ap.parse_args()

    manifest = []
    with zipfile.ZipFile(args.out, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in FILES:
            path = MANUAL_DIR / rel
            if not path.exists():
                raise FileNotFoundError(path)
            z.write(path, rel)
            manifest.append(f"{sha256_file(path)}  {rel}")
        z.writestr("MANIFEST.sha256", "\n".join(manifest) + "\n")
    print(f"{len(FILES)} files -> {args.out} ({args.out.stat().st_size / 2**20:.1f} MB)")


if __name__ == "__main__":
    main()
