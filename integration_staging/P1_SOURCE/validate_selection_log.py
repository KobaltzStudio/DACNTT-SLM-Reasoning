"""
Validate a selection log (JSONL) against schemas/selection_log_schema.json.

Extra checks beyond the schema:
  - selection records: problem_id must be in D_pool (if --pool is given or splits/d_pool_ids.txt exists)
  - selection records: trajectory_id must start with problem_id

Usage:
  python3 scripts/validate_selection_log.py LOG.jsonl [--pool splits/d_pool_ids.txt]

Exit code 0 if every line is valid, 1 otherwise.
"""

from pathlib import Path
import argparse
import json
import sys

from jsonschema import Draft202012Validator


BASE = Path(__file__).resolve().parents[1]
SCHEMA_FILE = BASE / "schemas" / "selection_log_schema.json"
DEFAULT_POOL = BASE / "splits" / "d_pool_ids.txt"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("log", type=Path)
    parser.add_argument("--pool", type=Path, default=None)
    args = parser.parse_args()

    schema = json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)

    pool_file = args.pool or (DEFAULT_POOL if DEFAULT_POOL.exists() else None)
    pool = set(pool_file.read_text(encoding="utf-8").split()) if pool_file else None
    if pool is None:
        print("[WARN] No D_pool file; skipping D_pool membership check")

    n_errors = 0
    n_lines = 0

    with args.log.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            if not line.strip():
                continue
            n_lines += 1
            errors = []
            try:
                record = json.loads(line)
            except json.JSONDecodeError as e:
                errors.append(f"invalid JSON: {e}")
                record = None

            if record is not None:
                schema_errors = list(validator.iter_errors(record))
                if schema_errors:
                    # oneOf errors are noisy; report the branch matching record_type
                    branch = {"selection": "selection", "checkpoint": "checkpoint"}.get(record.get("record_type"))
                    if branch:
                        sub = Draft202012Validator({**schema["$defs"][branch], "$defs": schema["$defs"]})
                        errors += [f"{'/'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in sub.iter_errors(record)]
                    else:
                        errors.append(f"record_type must be 'selection' or 'checkpoint', got {record.get('record_type')!r}")

                if record.get("record_type") == "selection":
                    pid, tid = record.get("problem_id"), record.get("trajectory_id")
                    if pool is not None and pid not in pool:
                        errors.append(f"problem_id {pid} not in D_pool")
                    if isinstance(tid, str) and isinstance(pid, str) and not tid.startswith(pid):
                        errors.append(f"trajectory_id {tid} does not start with problem_id {pid}")

            if errors:
                n_errors += 1
                for e in errors:
                    print(f"[FAIL] line {line_no}: {e}")
            else:
                print(f"[PASS] line {line_no}")

    print()
    print(f"Lines: {n_lines}  invalid: {n_errors}")
    sys.exit(1 if n_errors else 0)


if __name__ == "__main__":
    main()
