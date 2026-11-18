import hashlib
import json
from pathlib import Path

ROOT = Path(
    r"C:\Users\PC - NGHI\Desktop\Pipeline\P2\experiments\week2September\manual"
)

SOURCE_DIR = (
    ROOT / "integration_staging" / "P1"
    / "reports" / "task7" / "B4" / "seed_13"
)

OUTPUT_DIR = (
    ROOT / "reports" / "p1p2_integration"
    / "derived_predictions" / "B4_seed13"
)

CHECKPOINTS = [
    "student_ckpt_001",
    "student_ckpt_002",
    "student_ckpt_003",
]

EXPECTED_HASHES = {
    "student_ckpt_001":
        "9bb9aeb1c356b7563fc3d8b1b45fe9553bc7c2ca7907e7672833fae448f9a26d",
    "student_ckpt_002":
        "bd1c5a1a952056beea92d982b0212eab484a9bf6ad034cbc76803d6214d7c50f",
    "student_ckpt_003":
        "b27ecc6553c963cb8b173794b82f703aee4ebaf99461b0b051d45c06a55bf7cb",
}

ALLOWED_STATUS = {
    "valid",
    "invalid_answer",
    "invalid_format",
}

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def read_rows(path):
    rows = []
    with path.open("r", encoding="utf-8-sig") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSONL {path}:{line_no}: {exc}"
                ) from exc
            if not isinstance(row, dict):
                raise ValueError(
                    f"Expected JSON object at {path}:{line_no}"
                )
            rows.append(row)
    return rows

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    summary = []

    for checkpoint in CHECKPOINTS:
        source = SOURCE_DIR / f"eval_{checkpoint}_dev.jsonl"
        output = OUTPUT_DIR / f"eval_{checkpoint}_dev_status.jsonl"

        if not source.is_file():
            raise FileNotFoundError(source)

        if output.exists():
            raise FileExistsError(
                f"Refusing to overwrite existing derived file: {output}"
            )

        before_hash = sha256(source)
        expected_hash = EXPECTED_HASHES[checkpoint]

        if before_hash != expected_hash:
            raise ValueError(
                f"Source hash mismatch for {checkpoint}: "
                f"{before_hash} != {expected_hash}"
            )

        rows = read_rows(source)

        if len(rows) != 500:
            raise ValueError(
                f"{checkpoint}: expected 500 rows, found {len(rows)}"
            )

        ids = [str(row.get("problem_id", "")).strip() for row in rows]

        if any(not value for value in ids):
            raise ValueError(f"{checkpoint}: empty problem_id")

        if len(ids) != len(set(ids)):
            raise ValueError(f"{checkpoint}: duplicate problem_id")

        counts = {
            "valid": 0,
            "invalid_answer": 0,
            "invalid_format": 0,
        }

        derived_rows = []

        for row in rows:
            verification = row.get("verification_status")

            if verification not in ALLOWED_STATUS:
                raise ValueError(
                    f"{checkpoint}: unsupported verification_status "
                    f"{verification!r} for {row.get('problem_id')}"
                )

            if not isinstance(row.get("correct"), bool):
                raise ValueError(
                    f"{checkpoint}: correct must be Boolean for "
                    f"{row.get('problem_id')}"
                )

            expected_correct = verification == "valid"

            if row["correct"] != expected_correct:
                raise ValueError(
                    f"{checkpoint}: correct/status disagreement for "
                    f"{row.get('problem_id')}: "
                    f"correct={row['correct']}, status={verification}"
                )

            derived = dict(row)
            derived["status"] = verification
            derived_rows.append(derived)
            counts[verification] += 1

        with output.open("x", encoding="utf-8", newline="\n") as f:
            for row in derived_rows:
                f.write(
                    json.dumps(row, ensure_ascii=False) + "\n"
                )

        after_hash = sha256(source)

        if before_hash != after_hash:
            raise RuntimeError(
                f"Source prediction changed during adapter creation: "
                f"{source}"
            )

        output_rows = read_rows(output)

        if len(output_rows) != 500:
            raise RuntimeError(f"Output row count mismatch: {output}")

        if any("status" not in row for row in output_rows):
            raise RuntimeError(f"Output missing status: {output}")

        if any(
            row["status"] != row["verification_status"]
            for row in output_rows
        ):
            raise RuntimeError(f"Status mapping mismatch: {output}")

        record = {
            "checkpoint": checkpoint,
            "source": str(source),
            "source_sha256": before_hash,
            "source_sha256_after": after_hash,
            "output": str(output),
            "output_sha256": sha256(output),
            "records": len(output_rows),
            "unique_problem_ids": len({
                row["problem_id"] for row in output_rows
            }),
            "status_counts": counts,
            "source_unchanged": before_hash == after_hash,
            "status_mapping_valid": True,
        }

        summary.append(record)

        print("\nCHECKPOINT:", checkpoint)
        print("SOURCE_SHA256:", before_hash)
        print("OUTPUT:", output)
        print("OUTPUT_SHA256:", record["output_sha256"])
        print("RECORDS:", record["records"])
        print("UNIQUE_IDS:", record["unique_problem_ids"])
        print("STATUS_COUNTS:", counts)
        print("SOURCE_UNCHANGED:", record["source_unchanged"])
        print("STATUS_MAPPING: PASS")

    manifest = OUTPUT_DIR / "adapter_manifest.json"
    manifest.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("\nADAPTER_MANIFEST:", manifest)
    print("ADAPTER_BUILD: PASS")

if __name__ == "__main__":
    main()
