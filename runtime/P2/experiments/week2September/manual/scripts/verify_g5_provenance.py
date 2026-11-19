from pathlib import Path
import hashlib
import json
import sys

MANUAL = Path(__file__).resolve().parents[1]

SIDECAR_ROOTS = [
    MANUAL / "reports/capability_g4_validation/B4_seed13_S1",
    MANUAL / "reports/capability_g4_validation/B4_seed13_S2",
    MANUAL / "reports/capability_g4_validation/B4_seed13_S3",
]

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def hash_path(path: Path) -> str:
    if path.is_file():
        return sha256_file(path)

    if path.is_dir():
        files = sorted(p for p in path.rglob("*") if p.is_file())
        if not files:
            raise ValueError(f"Empty directory: {path}")

        h = hashlib.sha256()
        for file in files:
            relative = file.relative_to(path).as_posix()
            h.update(relative.encode("utf-8"))
            h.update(b"\0")
            h.update(sha256_file(file).encode("ascii"))
            h.update(b"\n")
        return h.hexdigest()

    raise FileNotFoundError(path)

def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

def check_path(label, raw_path, expected_hash=None):
    print(f"\n[{label}]")
    if not raw_path:
        print("PATH: NOT_PROVIDED")
        return False

    path = Path(raw_path)
    print("PATH:", path)
    print("EXISTS:", path.exists())

    if not path.exists():
        return False

    try:
        actual = hash_path(path)
        print("ACTUAL_SHA256:", actual)
        if expected_hash:
            print("EXPECTED_SHA256:", expected_hash)
            print("HASH_MATCH:", actual.lower() == expected_hash.lower())
            return actual.lower() == expected_hash.lower()
        return True
    except Exception as exc:
        print("HASH_ERROR:", repr(exc))
        return False

all_ok = True

for root in SIDECAR_ROOTS:
    print("\n" + "=" * 72)
    print("CONTEXT:", root.name)

    manifest_path = root / "student_capability_evaluation_manifest.json"
    fingerprint_path = root / "input_fingerprint.json"
    lineage_path = root / "checkpoint_lineage.json"

    required = [manifest_path, fingerprint_path, lineage_path]
    if not all(p.is_file() for p in required):
        print("SIDECAR_FILES_MISSING")
        all_ok = False
        continue

    manifest = load_json(manifest_path)
    fingerprint = load_json(fingerprint_path)
    lineage = load_json(lineage_path)

    expected_inputs = manifest.get("input_hashes", {})
    fingerprint_inputs = fingerprint.get("inputs", {})

    print("\n--- INTERNAL FINGERPRINT CONSISTENCY ---")
    print("RUN_ID:", manifest.get("run_id"))
    print("METHOD:", manifest.get("method"))
    print("SEED:", manifest.get("seed"))
    print("ROUND:", manifest.get("round"))
    print("GOLD_POLICY:", manifest.get("gold_policy"))
    print("STRICT_METRIC:", manifest.get("strict_metric"))
    print("CAPABILITY_ROWS:", manifest.get("n_capability_rows"))

    same_inputs = expected_inputs == fingerprint_inputs
    print("MANIFEST_INPUTS_EQUAL_FINGERPRINT_INPUTS:", same_inputs)
    if not same_inputs:
        all_ok = False

    checkpoint_hash = expected_inputs.get("checkpoint")
    lineage_checkpoint_hash = lineage.get("checkpoint_sha256")
    checkpoint_hash_match = checkpoint_hash == lineage_checkpoint_hash
    print("MANIFEST_CHECKPOINT_HASH_EQUALS_LINEAGE:", checkpoint_hash_match)
    if not checkpoint_hash_match:
        all_ok = False

    print("\n--- PHYSICAL ARTIFACT CHECKS ---")
    checks = [
        ("checkpoint", lineage.get("checkpoint_path"), checkpoint_hash),
        ("train_set", lineage.get("train_set"), expected_inputs.get("train_set")),
        ("train_log", lineage.get("train_log"), expected_inputs.get("train_log")),
        ("checkpoint_log", lineage.get("checkpoint_log"), expected_inputs.get("checkpoint_log")),
    ]

    for label, raw_path, expected in checks:
        if not check_path(label, raw_path, expected):
            all_ok = False

    print("\n--- SIDECAR OUTPUT HASH CHECKS ---")
    outputs = manifest.get("outputs", {})
    for filename, metadata in outputs.items():
        path = root / filename
        expected = metadata.get("sha256")
        if not path.is_file():
            print(filename, "MISSING")
            all_ok = False
            continue
        actual = sha256_file(path)
        matched = actual.lower() == str(expected).lower()
        print(filename, "HASH_MATCH:", matched)
        if not matched:
            all_ok = False

    print("\n--- COVERAGE STATUS ---")
    coverage_path = root / "prediction_coverage_report.json"
    coverage = load_json(coverage_path) if coverage_path.is_file() else {}
    print("STATUS:", coverage.get("status"))
    print("PREDICTIONS:", coverage.get("prediction_records"))
    print("UNIQUE_PREDICTIONS:", coverage.get("prediction_unique_ids"))
    print("GOLD_MATCHED:", coverage.get("gold_matched_prediction_ids"))
    if coverage.get("status") != "PASS":
        all_ok = False

print("\n" + "=" * 72)
print("PROVENANCE_PHYSICAL_AUDIT:", "PASS" if all_ok else "INCOMPLETE")
print("NOTE: PASS means all checked paths and hashes match; it does not independently prove semantic parent-child lineage.")
sys.exit(0 if all_ok else 2)
