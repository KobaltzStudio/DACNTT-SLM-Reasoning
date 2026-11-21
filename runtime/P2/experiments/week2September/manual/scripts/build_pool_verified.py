#!/usr/bin/env python3
"""
Build the verified Task 6 pool (Instruction_task6.md section 9, steps 2 and 4).

Inputs:
  trajectory/pool/pool_v1_teacher_raw.jsonl            all 5,500 Teacher outputs (vLLM)
  trajectory/pool/pool_v1_capability_predictions.jsonl  C(tau) from rules v2, --source raw (T6-6)

A raw row enters pool_v1_verified.jsonl when
  1. answer_utils re-scores it as valid (must agree with metadata.verification_status);
  2. it has a C(tau) prediction;
  3. the row (raw fields + capabilities) passes schemas/teacher_trajectory_schema_v2.json.
Problems with no row left are not eligible (T6-3). Every excluded row is listed with its reason in
pool_v1_excluded.jsonl; nothing is dropped silently.

Outputs:
  trajectory/pool/pool_v1_verified.jsonl
  trajectory/pool/pool_v1_excluded.jsonl
  trajectory/pool/pool_v1_manifest.json   inputs, outputs, counts, SHA-256

Usage (from experiments/week2September/manual/):
  python scripts/build_pool_verified.py
"""
import argparse
import collections
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

sys.path.insert(0, str(Path(__file__).resolve().parent))
from answer_utils import evaluate_output  # noqa: E402
from student_common import MANUAL_DIR, read_jsonl, sha256_file, write_json  # noqa: E402

POOL = MANUAL_DIR / "trajectory" / "pool"
FIELDS = ["problem_id", "teacher_model", "trajectory_id", "checkpoint", "question", "reasoning_trace",
          "answer", "ground_truth", "capabilities", "metadata", "raw_generation"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw", type=Path, default=POOL / "pool_v1_teacher_raw.jsonl")
    ap.add_argument("--capabilities", type=Path, default=POOL / "pool_v1_capability_predictions.jsonl")
    ap.add_argument("--schema", type=Path, default=MANUAL_DIR / "schemas" / "teacher_trajectory_schema_v2.json")
    ap.add_argument("--rules", type=Path, default=MANUAL_DIR / "config" / "capability_rules_v2.json")
    ap.add_argument("--out", type=Path, default=POOL / "pool_v1_verified.jsonl")
    ap.add_argument("--excluded", type=Path, default=POOL / "pool_v1_excluded.jsonl")
    ap.add_argument("--manifest", type=Path, default=POOL / "pool_v1_manifest.json")
    args = ap.parse_args()

    validator = Draft202012Validator(json.loads(args.schema.read_text(encoding="utf-8")))
    raw = read_jsonl(args.raw)
    caps = {p["trajectory_id"]: p["capabilities_predicted"] for p in read_jsonl(args.capabilities)}

    verified, excluded = [], []
    for r in raw:
        tid = r["trajectory_id"]
        status = evaluate_output(r["raw_generation"], r["ground_truth"])
        if status != r["metadata"]["verification_status"]:
            raise ValueError(f"{tid}: stored status {r['metadata']['verification_status']} != re-scored {status}")
        if status != "valid":
            excluded.append({"trajectory_id": tid, "problem_id": r["problem_id"], "reason": status})
            continue
        if tid not in caps:
            raise ValueError(f"{tid}: valid but no capability prediction")
        row = {k: r[k] for k in FIELDS if k != "capabilities"}
        row["capabilities"] = caps[tid]
        row["metadata"] = {**r["metadata"], "capability_extractor": "rules_v2/raw_generation"}
        row = {k: row[k] for k in FIELDS}
        errors = sorted(e.message for e in validator.iter_errors(row))
        if errors:
            excluded.append({"trajectory_id": tid, "problem_id": r["problem_id"], "reason": "schema",
                             "schema_errors": errors})
            continue
        verified.append(row)

    for path, rows in ((args.out, verified), (args.excluded, excluded)):
        with path.open("w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    problems = {r["problem_id"] for r in raw}
    eligible = collections.Counter(r["problem_id"] for r in verified)
    rel = lambda p: str(Path(p).resolve().relative_to(MANUAL_DIR))  # noqa: E731
    write_json(args.manifest, {
        "pool_version": "v1",
        "rules": "row valid by answer_utils (I1) + C(tau) from rules v2 on raw_generation (T6-6) + schema v2; "
                 "problems without any such row are not eligible (T6-3)",
        "counts": {
            "raw_trajectories": len(raw),
            "raw_problems": len(problems),
            "verified_trajectories": len(verified),
            "eligible_problems": len(eligible),
            "excluded_problems": sorted(problems - set(eligible)),
            "excluded_by_reason": dict(collections.Counter(e["reason"] for e in excluded)),
            "verified_per_problem": dict(sorted(collections.Counter(eligible.values()).items())),
        },
        "inputs": {rel(p): sha256_file(p) for p in (args.raw, args.capabilities, args.schema, args.rules,
                                                    POOL / "pool_v1_input.jsonl",
                                                    MANUAL_DIR / "config" / "experiment_config.json")},
        "outputs": {rel(p): sha256_file(p) for p in (args.out, args.excluded)},
    })
    print(f"verified {len(verified)} trajectories, {len(eligible)} eligible problems "
          f"(of {len(problems)}); excluded {dict(collections.Counter(e['reason'] for e in excluded))}")


if __name__ == "__main__":
    main()
