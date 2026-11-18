#!/usr/bin/env python3
"""Prepare verified Teacher trajectories as extractor input."""
import argparse, json
from pathlib import Path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("input", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--allow-invalid", action="store_true")
    args = p.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    total = valid = invalid = 0
    with args.input.open("r", encoding="utf-8") as fin, args.output.open("w", encoding="utf-8") as fout:
        for line_no, line in enumerate(fin, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            total += 1
            status = row.get("metadata", {}).get("verification_status")
            if status != "valid" and not args.allow_invalid:
                invalid += 1
                continue
            fout.write(json.dumps(row, ensure_ascii=False) + "\n")
            valid += 1

    print(f"Input trajectories: {total}")
    print(f"Valid trajectories: {valid}")
    print(f"Excluded invalid: {invalid}")
    print(f"Created: {args.output}")


if __name__ == "__main__":
    main()
