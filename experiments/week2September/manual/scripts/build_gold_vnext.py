import json
from pathlib import Path
from collections import Counter

ROOT = Path(".")

BATCH_INPUT = ROOT / "data/batch_100/batch_100_annotations_v2.jsonl"
SUPPLEMENT_INPUT = ROOT / "data/supplement/supplement_annotations_v2.jsonl"

DECISIONS_INPUT = ROOT / "reports/capability/d3_audit/adjudication_decisions.json"

OUTPUT_DIR = ROOT / "data/gold_vnext"
BATCH_OUTPUT = OUTPUT_DIR / "batch_100_annotations_vnext.jsonl"
SUPPLEMENT_OUTPUT = OUTPUT_DIR / "supplement_annotations_vnext.jsonl"
MANIFEST_OUTPUT = OUTPUT_DIR / "gold_vnext_manifest.json"

VALID_CAPABILITIES = {
    "addition", "subtraction", "multiplication", "division",
    "percentage", "fraction", "ratio"
}
VALID_DIFFICULTIES = {"easy", "medium", "hard"}


def read_jsonl(path):
    if not path.exists():
        raise FileNotFoundError(path)

    rows = []
    seen = set()

    with path.open("r", encoding="utf-8-sig") as f:
        for line_no, line in enumerate(f, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            pid = row.get("problem_id")

            if not pid:
                raise ValueError(f"Missing problem_id: {path}:{line_no}")
            if pid in seen:
                raise ValueError(f"Duplicate ID in {path}: {pid}")

            seen.add(pid)
            rows.append(row)

    return rows


def write_jsonl(path, rows):
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main():
    batch = read_jsonl(BATCH_INPUT)
    supplement = read_jsonl(SUPPLEMENT_INPUT)

    decisions = json.loads(DECISIONS_INPUT.read_text(encoding="utf-8"))

    if len(batch) != 100:
        raise ValueError(f"Expected 100 batch records, got {len(batch)}")
    if len(supplement) != 85:
        raise ValueError(f"Expected 85 supplement records, got {len(supplement)}")

    batch_ids = {r["problem_id"] for r in batch}
    supplement_ids = {r["problem_id"] for r in supplement}

    if batch_ids & supplement_ids:
        raise ValueError("Duplicate problem IDs across batch and supplement.")

    all_ids = batch_ids | supplement_ids

    missing_decision_ids = set(decisions) - all_ids
    if missing_decision_ids:
        raise ValueError(
            "Adjudication IDs not found in Gold v2: "
            + ", ".join(sorted(missing_decision_ids))
        )

    if len(decisions) != 22:
        raise ValueError(f"Expected 22 adjudication decisions, got {len(decisions)}")

    original_by_id = {
        r["problem_id"]: r for r in batch + supplement
    }

    changed_ids = set()

    def apply_decisions(rows):
        output = []

        for original in rows:
            row = dict(original)
            pid = row["problem_id"]

            if pid in decisions:
                decision = decisions[pid]
                capabilities = decision["capabilities"]
                difficulty = decision["difficulty"]

                if not capabilities:
                    raise ValueError(f"Empty capabilities for {pid}")
                if len(capabilities) != len(set(capabilities)):
                    raise ValueError(f"Duplicate capabilities for {pid}")
                if not set(capabilities).issubset(VALID_CAPABILITIES):
                    raise ValueError(f"Invalid capabilities for {pid}")
                if difficulty not in VALID_DIFFICULTIES:
                    raise ValueError(f"Invalid difficulty for {pid}")

                row["capabilities_manual"] = capabilities
                row["difficulty_manual"] = difficulty

                old_notes = row.get("notes", "")
                provenance = (
                    "[D3 AI adjudication proposal; pending human confirmation] "
                    + decision["rationale"]
                )
                row["notes"] = (
                    (old_notes.rstrip() + " " + provenance).strip()
                    if old_notes else provenance
                )

                changed_ids.add(pid)

            output.append(row)

        return output

    batch_vnext = apply_decisions(batch)
    supplement_vnext = apply_decisions(supplement)

    if changed_ids != set(decisions):
        missing = set(decisions) - changed_ids
        raise ValueError(
            "Some decisions were not applied: " + ", ".join(sorted(missing))
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_jsonl(BATCH_OUTPUT, batch_vnext)
    write_jsonl(SUPPLEMENT_OUTPUT, supplement_vnext)

    final_ids = {
        r["problem_id"] for r in batch_vnext + supplement_vnext
    }

    if len(final_ids) != 185:
        raise ValueError(f"Expected 185 unique IDs, got {len(final_ids)}")

    # Ensure ground truth and all non-adjudicated records remain unchanged.
    for row in batch_vnext + supplement_vnext:
        pid = row["problem_id"]
        original = original_by_id[pid]

        if row.get("ground_truth") != original.get("ground_truth"):
            raise ValueError(f"Ground truth changed for {pid}")

        if pid not in decisions:
            if row.get("capabilities_manual") != original.get("capabilities_manual"):
                raise ValueError(f"Unadjudicated capabilities changed: {pid}")
            if row.get("difficulty_manual") != original.get("difficulty_manual"):
                raise ValueError(f"Unadjudicated difficulty changed: {pid}")

    capability_support = Counter()
    difficulty_support = Counter()

    for row in batch_vnext + supplement_vnext:
        labels = row.get("capabilities_manual", [])
        difficulty = row.get("difficulty_manual")

        if not isinstance(labels, list) or not labels:
            raise ValueError(f"Invalid capabilities_manual: {row['problem_id']}")
        if not set(labels).issubset(VALID_CAPABILITIES):
            raise ValueError(f"Unknown capability: {row['problem_id']}")
        if difficulty not in VALID_DIFFICULTIES:
            raise ValueError(f"Invalid difficulty: {row['problem_id']}")

        capability_support.update(labels)
        difficulty_support.update([difficulty])

    manifest = {
        "dataset_name": "Gold vNext",
        "version": "vNext",
        "records": len(final_ids),
        "batch_100_records": len(batch_vnext),
        "supplement_records": len(supplement_vnext),
        "adjudicated_records": len(changed_ids),
        "adjudication_method": "AI-assisted adjudication; pending human confirmation",
        "source_files": [
            str(BATCH_INPUT),
            str(SUPPLEMENT_INPUT)
        ],
        "adjudication_decisions": str(DECISIONS_INPUT),
        "output_files": [
            str(BATCH_OUTPUT),
            str(SUPPLEMENT_OUTPUT)
        ],
        "ground_truth_modified": False,
        "non_adjudicated_labels_modified": False,
        "capability_support": dict(capability_support),
        "difficulty_support": dict(difficulty_support)
    }

    MANIFEST_OUTPUT.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("GOLD VNEXT BUILD: PASS")
    print("Batch records:", len(batch_vnext))
    print("Supplement records:", len(supplement_vnext))
    print("Total unique records:", len(final_ids))
    print("Adjudicated records applied:", len(changed_ids))
    print("Ground truth modified: False")
    print("Non-adjudicated labels modified: False")
    print("Output directory:", OUTPUT_DIR)


if __name__ == "__main__":
    main()
