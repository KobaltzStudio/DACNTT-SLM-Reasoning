from pathlib import Path
import csv
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]

GOLD = ROOT / "data/gold_releases/vFinal_2026-11-16"
SPLIT = ROOT / "splits/p1p2_vfinal_2026-11-16"

SOURCE_APPROVAL = ROOT / (
    "integration_staging/P1/reports/capability/"
    "p1_day14_final_2026-11-14/approved/"
    "gold_supplement_85_approved_review.csv"
)


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_ids(path):
    return [
        x.strip()
        for x in path.read_text(encoding="utf-8-sig").splitlines()
        if x.strip()
    ]


def require(condition, message):
    if not condition:
        raise AssertionError(message)
    print("PASS:", message)


def main():
    provenance_path = GOLD / "gold_release_provenance.json"
    require(provenance_path.is_file(), "Gold provenance exists")

    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))

    expected_files = {
        "gold_vfinal_manifest.json",
        "supplement_annotations_vfinal.jsonl",
        "gold_supplement_85_approved_review.csv",
        "adjudication_human_confirmed.csv",
    }

    require(
        set(provenance["files"]) == expected_files,
        "Provenance lists exactly four source files",
    )

    for name in sorted(expected_files):
        path = GOLD / name
        require(path.is_file(), f"Gold file exists: {name}")

        actual_hash = sha256(path)
        expected_hash = provenance["files"][name]["sha256"]

        require(
            actual_hash == expected_hash,
            f"Gold SHA-256 matches provenance: {name}",
        )

        require(
            path.stat().st_size == provenance["files"][name]["bytes"],
            f"Gold byte size matches provenance: {name}",
        )

    release_approval = GOLD / "gold_supplement_85_approved_review.csv"

    require(
        sha256(release_approval) == sha256(SOURCE_APPROVAL),
        "Release approval CSV matches original source",
    )

    with release_approval.open(
        "r", encoding="utf-8-sig", newline=""
    ) as f:
        approval_rows = list(csv.DictReader(f))

    approval_ids = [
        str(row["problem_id"]).strip()
        for row in approval_rows
    ]

    require(len(approval_rows) == 85, "Approval CSV has 85 rows")
    require(len(set(approval_ids)) == 85, "Approval IDs are unique")

    status_counts = {}
    for row in approval_rows:
        status = str(row["review_status"]).strip()
        human = str(row["human_approval"]).strip()

        status_counts[status] = status_counts.get(status, 0) + 1

        require(
            human.startswith("APPROVED_BY_USER_"),
            f"Explicit user approval exists for {row['problem_id']}",
        )

    require(
        status_counts == {
            "APPROVED_NO_LABEL_CHANGE": 84,
            "APPROVED_WITH_SOURCE_CLARIFICATION": 1,
        },
        "Approval review-status distribution is 84 + 1",
    )

    with (GOLD / "adjudication_human_confirmed.csv").open(
        "r", encoding="utf-8-sig", newline=""
    ) as f:
        adjudication_rows = list(csv.DictReader(f))

    adjudication_ids = {
        str(row["problem_id"]).strip()
        for row in adjudication_rows
    }

    require(len(adjudication_rows) == 22, "Adjudication has 22 rows")
    require(
        adjudication_ids.issubset(set(approval_ids)),
        "All 22 adjudication IDs overlap the 85 approved Gold IDs",
    )

    graph_path = SPLIT / "d_dev_graph_ids.txt"
    select_path = SPLIT / "d_dev_select_ids.txt"
    split_manifest_path = SPLIT / "split_manifest.json"

    require(graph_path.is_file(), "D_dev_graph file exists")
    require(select_path.is_file(), "D_dev_select file exists")
    require(split_manifest_path.is_file(), "Split manifest exists")

    split_manifest = json.loads(
        split_manifest_path.read_text(encoding="utf-8")
    )

    graph_ids = read_ids(graph_path)
    select_ids = read_ids(select_path)

    require(len(graph_ids) == 85, "D_dev_graph contains 85 IDs")
    require(len(select_ids) == 415, "D_dev_select contains 415 IDs")
    require(len(set(graph_ids)) == 85, "D_dev_graph IDs are unique")
    require(len(set(select_ids)) == 415, "D_dev_select IDs are unique")

    require(
        set(graph_ids) == set(approval_ids),
        "D_dev_graph exactly matches approved Gold IDs",
    )

    require(
        not (set(graph_ids) & set(select_ids)),
        "D_dev_graph and D_dev_select do not overlap",
    )

    require(
        len(set(graph_ids) | set(select_ids)) == 500,
        "Combined versioned dev split contains 500 unique IDs",
    )

    for path in [graph_path, select_path]:
        metadata = split_manifest["files"][path.name]

        require(
            sha256(path) == metadata["sha256"],
            f"Split SHA-256 matches manifest: {path.name}",
        )

        require(
            len(read_ids(path)) == metadata["count"],
            f"Split count matches manifest: {path.name}",
        )

    require(
        split_manifest["counts"]["d_dev_original"] == 500,
        "Original D_dev count is 500",
    )
    require(
        split_manifest["counts"]["d_pool"] == 6968,
        "D_pool count is 6968",
    )
    require(
        split_manifest["counts"]["d_test"] == 1319,
        "D_test count is 1319",
    )

    print("\nGOLD_RELEASE_VALIDATION: PASS")
    print("SPLIT_RELEASE_VALIDATION: PASS")
    print("Approval IDs       :", len(approval_ids))
    print("Adjudication IDs   :", len(adjudication_ids))
    print("D_dev_graph        :", len(graph_ids))
    print("D_dev_select       :", len(select_ids))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("\nRELEASE_VALIDATION: FAIL")
        print(type(exc).__name__ + ":", exc)
        sys.exit(1)
