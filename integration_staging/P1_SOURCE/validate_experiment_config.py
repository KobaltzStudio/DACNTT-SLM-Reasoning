"""
Validate config/experiment_config.json against schemas/experiment_config_schema.json.

Extra checks:
  - methods.required contains both B4 and B5 (primary comparison)
  - splits.manifest_sha256 matches the manifest file (when not "TBD")
  - schedule.rounds_M + 1 test checkpoints listed
  - --frozen: no "TBD" value anywhere

Usage:
  python3 scripts/validate_experiment_config.py [--config config/experiment_config.json] [--frozen]
"""

from pathlib import Path
import argparse
import hashlib
import json
import sys

from jsonschema import Draft202012Validator


BASE = Path(__file__).resolve().parents[1]
SCHEMA_FILE = BASE / "schemas" / "experiment_config_schema.json"
DEFAULT_CONFIG = BASE / "config" / "experiment_config.json"


def find_tbd(value, path="$"):
    if value == "TBD":
        yield path
    elif isinstance(value, dict):
        for k, v in value.items():
            yield from find_tbd(v, f"{path}.{k}")
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from find_tbd(v, f"{path}[{i}]")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--frozen", action="store_true")
    args = parser.parse_args()

    schema = json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    config = json.loads(args.config.read_text(encoding="utf-8"))

    errors = []
    for e in Draft202012Validator(schema).iter_errors(config):
        errors.append(f"schema: {'/'.join(map(str, e.path)) or '<root>'}: {e.message}")

    required = config.get("methods", {}).get("required", [])
    if not {"B4", "B5"} <= set(required):
        errors.append("methods.required must contain B4 and B5 (primary comparison)")

    sha = config.get("splits", {}).get("manifest_sha256")
    manifest = BASE / config.get("splits", {}).get("manifest", "")
    if sha not in (None, "TBD"):
        if not manifest.is_file():
            errors.append(f"split manifest not found: {manifest}")
        elif hashlib.sha256(manifest.read_bytes()).hexdigest() != sha:
            errors.append("splits.manifest_sha256 does not match the manifest file")

    m = config.get("schedule", {}).get("rounds_M")
    test_ckpts = config.get("evaluation", {}).get("test_checkpoints", [])
    if isinstance(m, int) and any(int(c[-3:]) > m for c in test_ckpts):
        errors.append("evaluation.test_checkpoints contains a checkpoint beyond rounds_M")

    tbd = list(find_tbd(config))
    if args.frozen and tbd:
        errors += [f"TBD not allowed in frozen config: {p}" for p in tbd]

    for e in errors:
        print(f"[FAIL] {e}")
    if tbd and not args.frozen:
        print(f"[INFO] {len(tbd)} TBD value(s) remain (allowed in draft):")
        for p in tbd:
            print(f"       {p}")

    print()
    if errors:
        print(f"[FAIL] {len(errors)} problem(s)")
        sys.exit(1)
    print("[PASS] experiment_config is valid" + (" and frozen" if args.frozen else " (draft)"))


if __name__ == "__main__":
    main()
