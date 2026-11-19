from pathlib import Path
import csv
import hashlib
import json
import shutil
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]

APPROVAL = ROOT / (
    "integration_staging/P1/reports/capability/"
    "p1_day14_final_2026-11-14/approved/"
    "gold_supplement_85_approved_review.csv"
)
ADJUDICATION = ROOT / (
    "reports/capability/d3_audit/"
    "adjudication_human_confirmed.csv"
)

GOLD_MANIFEST = ROOT / "data/gold_vfinal/gold_vfinal_manifest.json"
GOLD_LABELS = ROOT / "data/gold_vfinal/supplement_annotations_vfinal.jsonl"

DEV_FILE = ROOT / "splits/d_dev_ids.txt"
POOL_FILE = ROOT / "splits/d_pool_ids.txt"
TEST_FILE = ROOT / "splits/d_test_ids.txt"
SOURCE_SPLIT_MANIFEST = ROOT / "splits/split_manifest.json"

GOLD_RELEASE = ROOT / "data/gold_releases/vFinal_2026-11-16"
SPLIT_RELEASE = ROOT / "splits/p1p2_vfinal_2026-11-16"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_ids(path: Path) -> list[str]:
    if not path.is_file():
        raise FileNotFoundError(path)
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]


def require_file(path: Path):
    if not path.is_file():
        raise FileNotFoundError(f"Required input missing: {path}")


def copy_new(source: Path, destination: Path):
    require_file(source)
    if destination.exists():
        raise FileExistsError(
            f"Refusing to overwrite existing release file: {destination}"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def load_approval_ids(path: Path) -> tuple[list[str], list[dict]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    required = {"problem_id", "review_status", "human_approval"}
    if not rows:
        raise ValueError("Approval CSV is empty")
    if not required.issubset(rows[0].keys()):
        raise ValueError(
            f"Approval CSV missing columns: {required - set(rows[0].keys())}"
        )

    ids = [str(row["problem_id"]).strip() for row in rows]
    if any(not x for x in ids):
        raise ValueError("Approval CSV contains empty problem_id")
    if len(ids) != len(set(ids)):
        raise ValueError("Approval CSV contains duplicate problem_id")
    if len(ids) != 85:
        raise ValueError(f"Expected 85 approval rows, found {len(ids)}")

    accepted = {
        "APPROVED_NO_LABEL_CHANGE",
        "APPROVED_WITH_SOURCE_CLARIFICATION",
    }
    for row in rows:
        pid = str(row["problem_id"]).strip()
        status = str(row["review_status"]).strip()
        human = str(row["human_approval"]).strip()

        if status not in accepted:
            raise ValueError(f"Unapproved review status: {pid}={status}")
        if not human.startswith("APPROVED_BY_USER_"):
            raise ValueError(f"Missing user approval: {pid}={human}")

    return ids, rows


def main():
    inputs = [
        APPROVAL, ADJUDICATION, GOLD_MANIFEST, GOLD_LABELS,
        DEV_FILE, POOL_FILE, TEST_FILE, SOURCE_SPLIT_MANIFEST,
    ]
    for path in inputs:
        require_file(path)

    # Do not overwrite an earlier release.
    if GOLD_RELEASE.exists():
        raise FileExistsError(f"Gold release already exists: {GOLD_RELEASE}")
    if SPLIT_RELEASE.exists():
        raise FileExistsError(f"Split release already exists: {SPLIT_RELEASE}")

    gold_ids, approval_rows = load_approval_ids(APPROVAL)

    dev = read_ids(DEV_FILE)
    pool = read_ids(POOL_FILE)
    test = read_ids(TEST_FILE)

    for name, ids in [("D_dev", dev), ("D_pool", pool), ("D_test", test)]:
        if len(ids) != len(set(ids)):
            raise ValueError(f"{name} contains duplicate IDs")

    if len(dev) != 500:
        raise ValueError(f"Expected 500 D_dev IDs, found {len(dev)}")
    if len(pool) != 6968:
        raise ValueError(f"Expected 6968 D_pool IDs, found {len(pool)}")
    if len(test) != 1319:
        raise ValueError(f"Expected 1319 D_test IDs, found {len(test)}")

    dev_set, pool_set, test_set = set(dev), set(pool), set(test)
    gold_set = set(gold_ids)

    if not gold_set.issubset(dev_set):
        raise ValueError("Some approved Gold IDs are outside D_dev")
    if dev_set & pool_set:
        raise ValueError("D_dev and D_pool overlap")
    if dev_set & test_set:
        raise ValueError("D_dev and D_test overlap")
    if pool_set & test_set:
        raise ValueError("D_pool and D_test overlap")

    graph_ids = [pid for pid in dev if pid in gold_set]
    select_ids = [pid for pid in dev if pid not in gold_set]

    if len(graph_ids) != 85 or len(select_ids) != 415:
        raise ValueError(
            f"Unexpected split sizes: graph={len(graph_ids)}, "
            f"select={len(select_ids)}"
        )
    if set(graph_ids) != gold_set:
        raise ValueError("D_dev_graph does not exactly match approved Gold IDs")
    if set(graph_ids) & set(select_ids):
        raise ValueError("D_dev_graph and D_dev_select overlap")
    if set(graph_ids) | set(select_ids) != dev_set:
        raise ValueError("D_dev_graph + D_dev_select do not cover D_dev")

    # Create Gold release using copies. Original sources remain untouched.
    GOLD_RELEASE.mkdir(parents=True)
    gold_files = {
        "gold_vfinal_manifest.json": GOLD_MANIFEST,
        "supplement_annotations_vfinal.jsonl": GOLD_LABELS,
        "gold_supplement_85_approved_review.csv": APPROVAL,
        "adjudication_human_confirmed.csv": ADJUDICATION,
    }
    for name, source in gold_files.items():
        copy_new(source, GOLD_RELEASE / name)

    gold_provenance = {
        "release_id": "vFinal_2026-11-16",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "semantic_approval_basis": (
            "User confirmed that all 85 rows in the approval CSV were "
            "personally reviewed and semantically approved."
        ),
        "approval_row_count": len(approval_rows),
        "approval_unique_problem_ids": len(gold_ids),
        "review_status_counts": {},
        "human_adjudication_count": 22,
        "adjudication_interpretation": (
            "The 22 adjudication records overlap the 85 approved Gold IDs; "
            "they are additional adjudication evidence, not 22 additional "
            "Gold examples."
        ),
        "files": {},
    }
    for row in approval_rows:
        status = str(row["review_status"]).strip()
        gold_provenance["review_status_counts"][status] = (
            gold_provenance["review_status_counts"].get(status, 0) + 1
        )

    for name in gold_files:
        p = GOLD_RELEASE / name
        gold_provenance["files"][name] = {
            "sha256": sha256(p),
            "bytes": p.stat().st_size,
        }

    provenance_path = GOLD_RELEASE / "gold_release_provenance.json"
    provenance_path.write_text(
        json.dumps(gold_provenance, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    # Create versioned dev split.
    SPLIT_RELEASE.mkdir(parents=True)
    graph_path = SPLIT_RELEASE / "d_dev_graph_ids.txt"
    select_path = SPLIT_RELEASE / "d_dev_select_ids.txt"

    graph_path.write_text("\n".join(graph_ids) + "\n", encoding="utf-8")
    select_path.write_text("\n".join(select_ids) + "\n", encoding="utf-8")

    split_manifest = {
        "split_version": "p1p2_vfinal_2026-11-16",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_split_manifest": {
            "path": "splits/split_manifest.json",
            "sha256": sha256(SOURCE_SPLIT_MANIFEST),
        },
        "policy": {
            "d_dev_graph": (
                "Exactly the 85 user-approved Gold supplement problem IDs."
            ),
            "d_dev_select": (
                "The remaining 415 D_dev IDs; reserved for checkpoint "
                "selection and excluded from Gold capability evaluation."
            ),
            "d_test": (
                "Unchanged. Not used for checkpoint selection."
            ),
        },
        "counts": {
            "d_dev_original": len(dev),
            "d_dev_graph": len(graph_ids),
            "d_dev_select": len(select_ids),
            "d_pool": len(pool),
            "d_test": len(test),
        },
        "files": {
            graph_path.name: {
                "sha256": sha256(graph_path),
                "count": len(graph_ids),
            },
            select_path.name: {
                "sha256": sha256(select_path),
                "count": len(select_ids),
            },
        },
    }
    (SPLIT_RELEASE / "split_manifest.json").write_text(
        json.dumps(split_manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print("RELEASE_CREATION: PASS")
    print(f"Gold release : {GOLD_RELEASE}")
    print(f"Split release: {SPLIT_RELEASE}")
    print(f"D_dev_graph  : {len(graph_ids)}")
    print(f"D_dev_select : {len(select_ids)}")
    print(f"D_pool       : {len(pool)}")
    print(f"D_test       : {len(test)}")
    print("Original Gold and split source files were not modified.")


if __name__ == "__main__":
    main()
