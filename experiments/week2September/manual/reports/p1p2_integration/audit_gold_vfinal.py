import json
from collections import Counter
from pathlib import Path

GOLD_PATH = Path(
    r"C:\Users\PC - NGHI\Desktop\Pipeline\P1\experiments\week2September\manual\data\gold_vfinal\supplement_annotations_vfinal.jsonl"
)

MANIFEST_PATH = Path(
    r"C:\Users\PC - NGHI\Desktop\Pipeline\P1\experiments\week2September\manual\data\gold_vfinal\gold_vfinal_manifest.json"
)

EXPECTED_CAPABILITIES = {
    "addition",
    "subtraction",
    "multiplication",
    "division",
    "fraction",
    "percentage",
    "ratio",
}


def load_jsonl(path):
    records = []

    with path.open("r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            if not line.strip():
                raise ValueError(
                    f"Empty line at {path}:{line_number}"
                )

            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON at {path}:{line_number}: {exc}"
                ) from exc

            if not isinstance(record, dict):
                raise ValueError(
                    f"Expected JSON object at line {line_number}"
                )

            records.append(record)

    return records


def main():
    if not GOLD_PATH.is_file():
        raise FileNotFoundError(GOLD_PATH)

    if not MANIFEST_PATH.is_file():
        raise FileNotFoundError(MANIFEST_PATH)

    manifest = json.loads(
        MANIFEST_PATH.read_text(encoding="utf-8")
    )

    records = load_jsonl(GOLD_PATH)

    ids = [
        record.get("problem_id")
        for record in records
    ]

    missing_ids = [
        index + 1
        for index, problem_id in enumerate(ids)
        if not isinstance(problem_id, str) or not problem_id.strip()
    ]

    valid_ids = [
        problem_id
        for problem_id in ids
        if isinstance(problem_id, str) and problem_id.strip()
    ]

    id_counts = Counter(valid_ids)

    duplicate_ids = {
        problem_id: count
        for problem_id, count in id_counts.items()
        if count > 1
    }

    capability_counts = Counter()
    invalid_capabilities = []
    missing_capability_records = []

    for index, record in enumerate(records, start=1):
        capabilities = record.get("capabilities_manual")

        if not isinstance(capabilities, list) or not capabilities:
            missing_capability_records.append(index)
            continue

        for capability in capabilities:
            if capability not in EXPECTED_CAPABILITIES:
                invalid_capabilities.append({
                    "line": index,
                    "capability": capability,
                    "problem_id": record.get("problem_id"),
                })
            else:
                capability_counts[capability] += 1

    keys = sorted({
        key
        for record in records
        for key in record.keys()
    })

    print("=== GOLD VFINAL SUPPLEMENT AUDIT ===")
    print(f"File: {GOLD_PATH}")
    print(f"Manifest: {MANIFEST_PATH}")
    print(f"Actual records: {len(records)}")
    print(f"Manifest supplement_count: {manifest.get('supplement_count')}")
    print(f"Manifest total_count: {manifest.get('total_count')}")
    print(f"Unique non-empty problem IDs: {len(set(valid_ids))}")
    print(f"Missing/invalid IDs: {len(missing_ids)}")
    print(f"Duplicate IDs: {len(duplicate_ids)}")
    print(f"Missing capability records: {len(missing_capability_records)}")
    print(f"Invalid capability labels: {len(invalid_capabilities)}")

    print("\n=== RECORD KEYS ===")
    print(keys)

    print("\n=== CAPABILITY COUNTS ===")
    for capability in sorted(EXPECTED_CAPABILITIES):
        print(f"{capability}: {capability_counts[capability]}")

    print("\n=== DUPLICATE IDS ===")
    print(json.dumps(duplicate_ids, indent=2, ensure_ascii=False))

    print("\n=== INVALID CAPABILITIES ===")
    print(json.dumps(invalid_capabilities[:30], indent=2, ensure_ascii=False))

    print("\n=== FIRST RECORD ===")
    print(json.dumps(records[0], indent=2, ensure_ascii=False))

    checks = {
        "record_count_is_85": len(records) == 85,
        "manifest_count_matches": len(records) == manifest.get("supplement_count"),
        "all_ids_valid": len(missing_ids) == 0,
        "all_ids_unique": len(duplicate_ids) == 0,
        "all_capabilities_valid": len(invalid_capabilities) == 0,
        "all_records_have_capabilities": len(missing_capability_records) == 0,
    }

    print("\n=== CHECKS ===")
    for name, passed in checks.items():
        print(f"{name}: {'PASS' if passed else 'FAIL'}")

    if not all(checks.values()):
        raise SystemExit("GOLD SUPPLEMENT AUDIT: FAIL")

    print("\nGOLD SUPPLEMENT AUDIT: PASS")


if __name__ == "__main__":
    main()
