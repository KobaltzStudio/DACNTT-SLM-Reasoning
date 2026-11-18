import json
from pathlib import Path

ROOT = Path(".")

SOURCES = [
    ROOT / "data/batch_100/batch_100_annotations_v2.jsonl",
    ROOT / "data/supplement/supplement_annotations_v2.jsonl"
]

OUTPUTS = [
    ROOT / "data/gold_vnext/batch_100_annotations_vnext.jsonl",
    ROOT / "data/gold_vnext/supplement_annotations_vnext.jsonl"
]

DECISIONS_PATH = ROOT / "reports/capability/d3_audit/adjudication_decisions.json"
REPORT_PATH = ROOT / "reports/capability/d3_audit/gold_vnext_validation.json"

VALID_CAPABILITIES = {
    "addition", "subtraction", "multiplication", "division",
    "percentage", "fraction", "ratio"
}
VALID_DIFFICULTIES = {"easy", "medium", "hard"}


def read_jsonl(path):
    rows = []
    with path.open("r", encoding="utf-8-sig") as f:
        for line_no, line in enumerate(f, 1):
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid JSON: {path}:{line_no}: {exc}")
    return rows


def index_unique(rows, source_name):
    result = {}
    for row in rows:
        pid = row.get("problem_id")
        if not pid:
            raise ValueError(f"Missing problem_id in {source_name}")
        if pid in result:
            raise ValueError(f"Duplicate problem_id in {source_name}: {pid}")
        result[pid] = row
    return result


def main():
    for path in SOURCES + OUTPUTS + [DECISIONS_PATH]:
        if not path.exists():
            raise FileNotFoundError(path)

    source_batch = read_jsonl(SOURCES[0])
    source_supplement = read_jsonl(SOURCES[1])
    output_batch = read_jsonl(OUTPUTS[0])
    output_supplement = read_jsonl(OUTPUTS[1])

    source = index_unique(source_batch + source_supplement, "Gold v2")
    output = index_unique(output_batch + output_supplement, "Gold vNext")

    decisions = json.loads(DECISIONS_PATH.read_text(encoding="utf-8"))
    adjudicated_ids = set(decisions)

    errors = []
    checks = {}

    checks["batch_count"] = len(output_batch) == 100
    checks["supplement_count"] = len(output_supplement) == 85
    checks["total_count"] = len(output) == 185
    checks["unique_ids"] = len(output) == 185
    checks["same_id_inventory"] = set(source) == set(output)
    checks["decision_count"] = len(adjudicated_ids) == 22
    checks["all_decision_ids_exist"] = adjudicated_ids.issubset(output)

    if not checks["same_id_inventory"]:
        errors.append("Gold v2 and Gold vNext ID inventories differ.")

    changed_capabilities = []
    changed_difficulties = []
    ground_truth_changes = []
    unadjudicated_changes = []

    for pid, new in output.items():
        old = source.get(pid)
        if old is None:
            continue

        if old.get("ground_truth") != new.get("ground_truth"):
            ground_truth_changes.append(pid)

        if old.get("capabilities_manual") != new.get("capabilities_manual"):
            changed_capabilities.append(pid)

        if old.get("difficulty_manual") != new.get("difficulty_manual"):
            changed_difficulties.append(pid)

        if pid not in adjudicated_ids:
            if (
                old.get("capabilities_manual") != new.get("capabilities_manual")
                or old.get("difficulty_manual") != new.get("difficulty_manual")
            ):
                unadjudicated_changes.append(pid)

        labels = new.get("capabilities_manual")
        difficulty = new.get("difficulty_manual")

        if not isinstance(labels, list) or not labels:
            errors.append(f"Invalid/empty capabilities_manual: {pid}")
        elif not set(labels).issubset(VALID_CAPABILITIES):
            errors.append(f"Unknown capability label: {pid}")

        if difficulty not in VALID_DIFFICULTIES:
            errors.append(f"Invalid difficulty: {pid}")

    checks["ground_truth_unchanged"] = len(ground_truth_changes) == 0
    checks["no_unadjudicated_label_changes"] = len(unadjudicated_changes) == 0
    checks["all_labels_valid"] = not any(
        "capabilities_manual" in e or "capability label" in e for e in errors
    )
    checks["all_difficulties_valid"] = not any(
        "difficulty" in e for e in errors
    )
    checks["all_adjudicated_ids_present"] = adjudicated_ids.issubset(output)

    report = {
        "dataset": "Gold vNext",
        "status": "PASS" if all(checks.values()) and not errors else "FAIL",
        "checks": checks,
        "source_record_count": len(source),
        "output_record_count": len(output),
        "adjudication_decision_count": len(adjudicated_ids),
        "changed_capability_ids": sorted(changed_capabilities),
        "changed_difficulty_ids": sorted(changed_difficulties),
        "ground_truth_changed_ids": sorted(ground_truth_changes),
        "unadjudicated_label_changed_ids": sorted(unadjudicated_changes),
        "errors": errors
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("GOLD VNEXT VALIDATION:", report["status"])
    for name, passed in checks.items():
        print(f"{name}: {'PASS' if passed else 'FAIL'}")
    print("Source records:", len(source))
    print("Output records:", len(output))
    print("Changed capability records:", len(changed_capabilities))
    print("Changed difficulty records:", len(changed_difficulties))
    print("Ground truth changes:", len(ground_truth_changes))
    print("Unadjudicated label changes:", len(unadjudicated_changes))
    print("Report:", REPORT_PATH)

    if errors:
        for error in errors:
            print("ERROR:", error)

    if report["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
