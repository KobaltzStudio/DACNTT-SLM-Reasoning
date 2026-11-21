from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
from collections import Counter
from pathlib import Path


# This script is stored in manual/scripts, so parents[1] is manual/.
BASE = Path(__file__).resolve().parents[1]

PATHS = {
    "batch": BASE / "data/gold_vfinal/batch_100_annotations_vfinal.jsonl",
    "supplement": BASE / "data/gold_vfinal/supplement_annotations_vfinal.jsonl",
    "gold_manifest": BASE / "data/gold_vfinal/gold_vfinal_manifest.json",
    "raw_train": BASE / "data/raw/gsm8k_train.jsonl",
    "supplement_raw": BASE / "data/raw/supplement_selected.jsonl",
    "worklist": (
        BASE / "data/gold/review_2026-11-15"
        / "adjudication_worklist_63_pending.csv"
    ),
    "queue": (
        BASE / "reports/capability/p1_gold_audit_2026-11-14"
        / "gold_review_queue.csv"
    ),
    "human_confirmed": (
        BASE / "reports/capability/d3_audit"
        / "adjudication_human_confirmed.csv"
    ),
    "schema_inspection": (
        BASE / "reports/gold/review_2026-11-15"
        / "gold_source_schema_inspection.json"
    ),
}

REPORT_DIR = BASE / "reports/gold/review_2026-11-16"
DATA_DIR = BASE / "data"

CANDIDATE_NAME = "gold_vnext_candidate_2026-11-16"
CANDIDATE_DIR = DATA_DIR / CANDIDATE_NAME
STAGING_DIR = DATA_DIR / f".{CANDIDATE_NAME}_staging"

BATCH_NAME = "batch_100_annotations_vnext.jsonl"
SUPPLEMENT_NAME = "supplement_annotations_vnext.jsonl"
MANIFEST_NAME = "gold_vnext_manifest.json"

EXPECTED_FIELDS = {
    "problem_id",
    "capabilities_manual",
    "difficulty_manual",
    "notes",
    "annotator_id",
    "schema_version",
}

VALID_CAPABILITIES = {
    "addition",
    "subtraction",
    "multiplication",
    "division",
    "fraction",
    "percentage",
    "ratio",
}
VALID_DIFFICULTIES = {"easy", "medium", "hard"}


# The following 22 decisions were explicitly confirmed by the user.
# All other 41 pending IDs are retained without changing their annotations.
DECISIONS = {
    "gsm8k_train_00666": {
        "capabilities": ["addition", "multiplication", "fraction"],
        "answer_status": "CONFIRMED",
        "answer_decision": "27",
        "ambiguity": False,
        "ambiguity_status": "NO_NEW_AMBIGUITY",
        "reason": (
            "Correct the Gold note to 27. Anthony has 8 cats and 4 dogs; "
            "Leonel has 4 cats and 11 dogs. Total = 27. Retain labels."
        ),
        "note_mode": "replace",
        "note": (
            "Corrected Gold note: Anthony has 12 pets, of which 2/3 are "
            "cats: 8 cats and 4 dogs. Leonel has half as many cats as "
            "Anthony: 4 cats, and 7 more dogs than Anthony: 11 dogs. "
            "Total = 8 + 4 + 4 + 11 = 27. Ground truth is 27."
        ),
    },
    "gsm8k_train_00830": {
        "capabilities": [
            "addition", "subtraction", "multiplication", "percentage"
        ],
        "answer_status": "SOURCE_VARIANT_CONFLICT_KEEP_RAW_GROUND_TRUTH",
        "answer_decision": (
            "Current raw source asks total meal cost and has ground truth "
            "25. The separately supplied source variant asks for the lassi "
            "price and its reasoning gives $2.50. These are different targets."
        ),
        "ambiguity": True,
        "ambiguity_status": "SOURCE_VARIANT_AND_TAX_WORDING_CONFLICT",
        "reason": (
            "Add subtraction because the supplied alternate reasoning "
            "solves 25 - (18 + 4.50) = 2.50. Preserve the distinction "
            "between the alternate source variant (lassi price) and the "
            "current raw dataset record (meal total, ground truth 25). "
            "The current raw question states lassi costs $2 and asks for "
            "the meal total with tax. Its ground truth must not be replaced "
            "by 2.50. The tax wording is not separately calculated."
        ),
        "note_mode": "append",
        "note": (
            "Adjudication 2026-11-16: add subtraction. Source caveat: "
            "the separately supplied variant asks for the mango lassi "
            "price and derives $2.50 by 25 - (18 + 4.50). The current raw "
            "dataset variant instead states the lassi costs $2, asks for "
            "the meal total, and has ground truth 25. Do not conflate the "
            "two targets or modify raw ground truth. The phrase 'with tax' "
            "is not accompanied by a separately calculated tax amount."
        ),
    },
    "gsm8k_train_00840": {
        "capabilities": ["multiplication", "ratio"],
        "answer_status": "CONFIRMED",
        "answer_decision": "$100",
        "ambiguity": False,
        "ambiguity_status": "NO_NEW_AMBIGUITY",
        "reason": (
            "Amy receives one ratio part and Sandra receives two. "
            "Sandra receives 2 * 50 = 100. Remove division."
        ),
        "note_mode": "append",
        "note": (
            "Adjudication 2026-11-16: ratio 2:1:3 means Sandra receives "
            "twice Amy's share. Amy receives $50, so Sandra receives "
            "2 * $50 = $100. Remove division; retain multiplication and ratio."
        ),
    },
    "gsm8k_train_01200": {
        "capabilities": ["addition", "multiplication", "fraction"],
        "answer_status": "CONFIRMED_UNDER_INTERPRETATION_A",
        "answer_decision": "$42.00",
        "ambiguity": True,
        "ambiguity_status": "INTERPRETATION_A_ACCEPTED",
        "reason": (
            "Accept interpretation A: four steaks, each weighing half "
            "a pound. Steak costs $30 and chicken costs $12; total $42."
        ),
        "note_mode": "append",
        "note": (
            "Adjudication 2026-11-16: accepted interpretation A: four "
            "steaks weighing 0.5 lb each. Steak weight = 2 lb; steak cost "
            "= $30; chicken cost = $12; total = $42. This interpretation "
            "is retained as the adjudicated reading of the wording."
        ),
    },
    "gsm8k_train_03048": {
        "capabilities": [
            "subtraction", "multiplication", "division", "percentage"
        ],
        "answer_status": "CONFIRMED_UNDER_DISJOINT_CATEGORY_ASSUMPTION",
        "answer_decision": "20%",
        "ambiguity": True,
        "ambiguity_status": "DISJOINT_CATEGORY_ASSUMPTION_ACCEPTED",
        "reason": (
            "Assume novels, graphic novels, and comic books are mutually "
            "exclusive categories. Novels = 78; comics = 120 - 78 - 18 "
            "= 24; comic percentage = 20%."
        ),
        "note_mode": "append",
        "note": (
            "Adjudication 2026-11-16: retain answer 20% under the accepted "
            "assumption that novels, graphic novels, and comic books are "
            "three mutually exclusive categories. Novels = 0.65 * 120 = 78; "
            "comic books = 120 - 78 - 18 = 24; 24/120 = 20%."
        ),
    },
    "gsm8k_train_06921": {
        "capabilities": [
            "subtraction", "multiplication", "division", "percentage"
        ],
        "answer_status": "KEEP_EXISTING_GOLD_ANSWER",
        "answer_decision": "17%",
        "ambiguity": False,
        "ambiguity_status": "NO_NEW_AMBIGUITY",
        "reason": (
            "Add division because profit percentage requires profit "
            "divided by cost price, multiplied by 100."
        ),
        "note_mode": "append",
        "note": (
            "Adjudication 2026-11-16: add division. Profit percentage "
            "requires (selling price - cost price) / cost price * 100. "
            "The division is a necessary reasoning operation."
        ),
    },
    "gsm8k_train_07158": {
        "capabilities": ["addition", "multiplication", "division", "ratio"],
        "answer_status": "KEEP_EXISTING_GOLD_ANSWER",
        "answer_decision": "120 pints",
        "ambiguity": False,
        "ambiguity_status": "NO_NEW_AMBIGUITY",
        "reason": (
            "Add addition for combining 20 golden apples and 40 pink "
            "lady apples required per pint. Retain multiplication, "
            "division, and ratio."
        ),
        "note_mode": "append",
        "note": (
            "Adjudication 2026-11-16: add addition for combining the "
            "20 golden delicious apples and 40 pink lady apples required "
            "per pint. The full reasoning also uses multiplication, "
            "ratio allocation, and division. Answer remains 120 pints."
        ),
    },
    "gsm8k_train_07349": {
        "capabilities": ["fraction", "ratio"],
        "answer_status": "KEEP_EXISTING_GOLD_ANSWER",
        "answer_decision": "28 cups",
        "ambiguity": False,
        "ambiguity_status": "NO_NEW_AMBIGUITY",
        "reason": (
            "Retain fraction and ratio; remove multiplication and division "
            "under Guideline v3 because these are not separate reasoning "
            "requirements in this problem."
        ),
        "note_mode": "append",
        "note": (
            "Adjudication 2026-11-16: retain fraction and ratio; remove "
            "multiplication and division under Guideline v3. The problem "
            "requires interpreting the sugar share as a fraction of the "
            "total mixture and applying the stated ratio."
        ),
    },
    "gsm8k_train_00713": {
        "capabilities": [
            "addition", "subtraction", "multiplication", "percentage"
        ],
        "answer_status": "ACCEPTED_TARGET_15_WITH_EXPLICIT_ASSUMPTIONS",
        "answer_decision": "15%",
        "ambiguity": True,
        "ambiguity_status": "VACCINE_SCOPE_AND_MOSQUITO_OVERLAP_ASSUMPTIONS",
        "reason": (
            "Preserve intended answer 15%. This requires assuming that "
            "the two infected-mosquito groups are disjoint and that the "
            "50% vaccine reduction applies to infection risk for both "
            "malaria and Zika, despite the phrase 'malaria vaccine'. "
            "This scope assumption conflicts with the literal malaria-only "
            "description and must remain explicit."
        ),
        "note_mode": "append",
        "note": (
            "Adjudication 2026-11-16: preserve dataset target answer 15% "
            "under the intended-source assumptions: (1) malaria-infected "
            "and Zika-infected mosquito groups are disjoint; (2) the 50% "
            "vaccine reduction applies to post-bite infection risk for "
            "both malaria and Zika. This second assumption is not entailed "
            "by the literal phrase 'malaria vaccine'; the wording describes "
            "a malaria vaccine but the intended 15% calculation applies "
            "the reduction to both viruses. Mark as ambiguous. Do not "
            "describe 15% as following from a malaria-only vaccine model."
        ),
    },

    # Eleven capability decisions confirmed by the user.
    "gsm8k_train_00155": {
        "capabilities": ["subtraction", "fraction"],
        "answer_status": "KEEP_SOURCE_GROUND_TRUTH",
        "answer_decision": None,
        "ambiguity": False,
        "ambiguity_status": "NO_NEW_AMBIGUITY",
        "reason": (
            "Remove multiplication. Fractional portions are taken from "
            "quantities; successive remaining amounts require subtraction."
        ),
        "note_mode": "append",
        "note": (
            "Adjudication 2026-11-16: remove multiplication. The reasoning "
            "requirements are fraction and subtraction."
        ),
    },
    "gsm8k_train_00779": {
        "capabilities": ["subtraction", "division", "fraction"],
        "answer_status": "KEEP_SOURCE_GROUND_TRUTH",
        "answer_decision": None,
        "ambiguity": False,
        "ambiguity_status": "NO_NEW_AMBIGUITY",
        "reason": (
            "Remove multiplication and add subtraction. The problem "
            "requires finding the complementary fraction, then using "
            "division to recover totals from known fractional parts."
        ),
        "note_mode": "append",
        "note": (
            "Adjudication 2026-11-16: capabilities are subtraction, "
            "division, and fraction. Remove multiplication; subtraction "
            "is required to obtain the complementary fraction."
        ),
    },
    "gsm8k_train_00818": {
        "capabilities": ["subtraction", "division", "fraction"],
        "answer_status": "KEEP_SOURCE_GROUND_TRUTH",
        "answer_decision": None,
        "ambiguity": False,
        "ambiguity_status": "NO_NEW_AMBIGUITY",
        "reason": (
            "Remove multiplication. Jenny spends 3/7, leaving 4/7; "
            "division by the known fraction recovers the original amount."
        ),
        "note_mode": "append",
        "note": (
            "Adjudication 2026-11-16: retain subtraction, division, and "
            "fraction. Remove multiplication; inverse recovery from a "
            "known fractional part requires division."
        ),
    },
    "gsm8k_train_01869": {
        "capabilities": ["subtraction", "fraction"],
        "answer_status": "KEEP_SOURCE_GROUND_TRUTH",
        "answer_decision": None,
        "ambiguity": False,
        "ambiguity_status": "NO_NEW_AMBIGUITY",
        "reason": (
            "Remove multiplication. The problem applies fractions to "
            "successive remaining quantities and subtracts consumed amounts."
        ),
        "note_mode": "append",
        "note": (
            "Adjudication 2026-11-16: retain subtraction and fraction. "
            "Remove multiplication; fraction-of-quantity reasoning is "
            "not an independent multiplication requirement."
        ),
    },
    "gsm8k_train_02837": {
        "capabilities": ["addition", "fraction"],
        "answer_status": "KEEP_SOURCE_GROUND_TRUTH",
        "answer_decision": None,
        "ambiguity": False,
        "ambiguity_status": "NO_NEW_AMBIGUITY",
        "reason": (
            "Remove multiplication. The reasoning combines an addition "
            "step with fractional relationships."
        ),
        "note_mode": "append",
        "note": (
            "Adjudication 2026-11-16: retain addition and fraction. "
            "Remove multiplication; the fractional calculation is "
            "classified as fraction under Guideline v3."
        ),
    },
    "gsm8k_train_02893": {
        "capabilities": ["fraction"],
        "answer_status": "KEEP_SOURCE_GROUND_TRUTH",
        "answer_decision": None,
        "ambiguity": False,
        "ambiguity_status": "NO_NEW_AMBIGUITY",
        "reason": (
            "Retain fraction only. The required reasoning consists of "
            "taking fractional portions of a quantity."
        ),
        "note_mode": "append",
        "note": (
            "Adjudication 2026-11-16: retain fraction only. Remove "
            "multiplication; arithmetic implementation of a fraction "
            "does not establish an independent multiplication capability."
        ),
    },
    "gsm8k_train_03289": {
        "capabilities": ["subtraction", "fraction"],
        "answer_status": "KEEP_SOURCE_GROUND_TRUTH",
        "answer_decision": None,
        "ambiguity": False,
        "ambiguity_status": "NO_NEW_AMBIGUITY",
        "reason": (
            "Remove multiplication. The problem uses successive fractions "
            "of remaining quantities and subtraction."
        ),
        "note_mode": "append",
        "note": (
            "Adjudication 2026-11-16: retain subtraction and fraction. "
            "Remove multiplication under Guideline v3."
        ),
    },
    "gsm8k_train_03316": {
        "capabilities": ["subtraction", "fraction"],
        "answer_status": "KEEP_SOURCE_GROUND_TRUTH",
        "answer_decision": None,
        "ambiguity": False,
        "ambiguity_status": "NO_NEW_AMBIGUITY",
        "reason": (
            "Remove multiplication. The problem uses fractions of "
            "successive remaining quantities and subtraction."
        ),
        "note_mode": "append",
        "note": (
            "Adjudication 2026-11-16: retain subtraction and fraction. "
            "Remove multiplication under Guideline v3."
        ),
    },
    "gsm8k_train_03734": {
        "capabilities": ["addition", "subtraction", "fraction"],
        "answer_status": "KEEP_SOURCE_GROUND_TRUTH",
        "answer_decision": None,
        "ambiguity": False,
        "ambiguity_status": "NO_NEW_AMBIGUITY",
        "reason": (
            "Remove multiplication. The solution combines addition, "
            "subtraction, and fractional relationships."
        ),
        "note_mode": "append",
        "note": (
            "Adjudication 2026-11-16: retain addition, subtraction, and "
            "fraction. Remove multiplication under Guideline v3."
        ),
    },
    "gsm8k_train_03879": {
        "capabilities": ["subtraction", "fraction"],
        "answer_status": "KEEP_SOURCE_GROUND_TRUTH",
        "answer_decision": None,
        "ambiguity": False,
        "ambiguity_status": "NO_NEW_AMBIGUITY",
        "reason": (
            "Remove multiplication. The reasoning applies a fraction "
            "to a group and subtracts people who leave."
        ),
        "note_mode": "append",
        "note": (
            "Adjudication 2026-11-16: retain subtraction and fraction. "
            "Remove multiplication under Guideline v3."
        ),
    },
    "gsm8k_train_03882": {
        "capabilities": ["subtraction", "fraction"],
        "answer_status": "KEEP_SOURCE_GROUND_TRUTH",
        "answer_decision": None,
        "ambiguity": False,
        "ambiguity_status": "NO_NEW_AMBIGUITY",
        "reason": (
            "Remove multiplication. The solution applies a fraction "
            "to the remaining quantity and uses subtraction."
        ),
        "note_mode": "append",
        "note": (
            "Adjudication 2026-11-16: retain subtraction and fraction. "
            "Remove multiplication under Guideline v3."
        ),
    },

    "gsm8k_train_00239": {
        "capabilities": ["addition", "subtraction", "percentage"],
        "answer_status": "CONFIRMED_WITH_OVERLAP_ASSUMPTION",
        "answer_decision": "30%",
        "ambiguity": True,
        "ambiguity_status": "OVERLAP_DEFINED_AS_5_PERCENTAGE_POINTS_OF_TOTAL",
        "reason": (
            "Keep answer 30% and current labels. Accept the assumption "
            "that the overlap is 5 percentage points of all germs: "
            "50% + 25% - 5% = 70% killed; 30% remain. Mark ambiguity."
        ),
        "note_mode": "append",
        "note": (
            "Adjudication 2026-11-16: retain answer 30% and current "
            "capabilities. Explicit assumption: the overlap is 5 percentage "
            "points of the total germ population. Killed = 50% + 25% - 5% "
            "= 70%; remaining = 30%. The wording does not fully specify "
            "the denominator of the 5% overlap; mark ambiguity."
        ),
    },
    "gsm8k_train_02960": {
        "capabilities": ["addition", "subtraction", "division", "fraction"],
        "answer_status": "KEEP_SOURCE_GROUND_TRUTH",
        "answer_decision": "180",
        "ambiguity": False,
        "ambiguity_status": "NO_NEW_AMBIGUITY",
        "reason": (
            "Remove multiplication. The equation is x - x/2 - 14 - "
            "x/3 - 16 = 0; combine fixed expenses, subtract fractions, "
            "then solve x/6 = 30 by division."
        ),
        "note_mode": "append",
        "note": (
            "Adjudication 2026-11-16: remove multiplication. Let starting "
            "money be x: x - x/2 - 14 - x/3 - 16 = 0; hence x/6 = 30 "
            "and x = 180. Retain addition, subtraction, division, and fraction."
        ),
    },
}


def read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        raise FileNotFoundError(path)

    rows = []
    with path.open("r", encoding="utf-8-sig") as f:
        for line_no, line in enumerate(f, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL: {path}:{line_no}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"Expected JSON object: {path}:{line_no}")
            rows.append(row)
    return rows


def read_csv(path: Path) -> list[dict]:
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def read_json(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def index_by_id(rows: list[dict], label: str) -> dict[str, dict]:
    result = {}
    for row in rows:
        pid = row.get("problem_id")
        if not pid:
            raise ValueError(f"{label}: record without problem_id")
        if pid in result:
            raise ValueError(f"{label}: duplicate problem_id {pid}")
        result[pid] = row
    return result


def parse_labels(value, pid: str) -> list[str]:
    if isinstance(value, list):
        labels = value
    elif isinstance(value, str):
        labels = json.loads(value)
    else:
        raise ValueError(f"Invalid capabilities in worklist for {pid}")

    if not isinstance(labels, list) or not labels:
        raise ValueError(f"Empty/invalid capabilities for {pid}")

    labels = [str(x).strip() for x in labels]
    if len(labels) != len(set(labels)):
        raise ValueError(f"Duplicate capabilities for {pid}")

    invalid = set(labels) - VALID_CAPABILITIES
    if invalid:
        raise ValueError(f"Invalid capabilities for {pid}: {sorted(invalid)}")

    return labels


def check(condition: bool, name: str, detail, checks: list) -> None:
    checks.append({
        "name": name,
        "passed": bool(condition),
        "detail": detail,
    })


def append_note(old: str, new: str, mode: str) -> str:
    if mode == "replace":
        return new
    old = str(old or "").strip()
    return f"{old}\n[{new}]" if old else new


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"Refusing to write empty CSV: {path}")
    fields = list(rows[0].keys())
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    print("BASE:", BASE)
    print("Checking required source files...")

    missing = [str(path) for path in PATHS.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            "Missing required files:\n" + "\n".join(missing)
        )

    if CANDIDATE_DIR.exists():
        raise FileExistsError(
            f"Candidate already exists; refusing to overwrite: {CANDIDATE_DIR}"
        )
    if STAGING_DIR.exists():
        raise FileExistsError(
            f"Staging directory already exists; inspect it before rerunning: "
            f"{STAGING_DIR}"
        )

    # Read all authoritative sources.
    batch = read_jsonl(PATHS["batch"])
    supplement = read_jsonl(PATHS["supplement"])
    raw_train = read_jsonl(PATHS["raw_train"])
    supplement_raw = read_jsonl(PATHS["supplement_raw"])
    worklist = read_csv(PATHS["worklist"])
    queue = read_csv(PATHS["queue"])
    human = read_csv(PATHS["human_confirmed"])
    gold_manifest = read_json(PATHS["gold_manifest"])
    schema = read_json(PATHS["schema_inspection"])

    batch_by_id = index_by_id(batch, "Gold vFinal batch")
    supplement_by_id = index_by_id(supplement, "Gold vFinal supplement")
    raw_by_id = index_by_id(raw_train, "raw GSM8K train")
    supplement_raw_by_id = index_by_id(
        supplement_raw, "supplement_selected"
    )
    worklist_by_id = index_by_id(worklist, "63-row worklist")
    queue_by_id = index_by_id(queue, "Gold review queue")
    human_by_id = index_by_id(human, "human-confirmed adjudication")

    batch_ids = set(batch_by_id)
    supplement_ids = set(supplement_by_id)
    worklist_ids = set(worklist_by_id)
    queue_ids = set(queue_by_id)
    human_ids = set(human_by_id)

    checks = []

    check(len(batch) == 100, "batch_count", len(batch), checks)
    check(len(supplement) == 85, "supplement_count", len(supplement), checks)
    check(
        len(batch_ids | supplement_ids) == 185,
        "gold_total_unique_ids",
        len(batch_ids | supplement_ids),
        checks,
    )
    check(
        not (batch_ids & supplement_ids),
        "batch_supplement_disjoint",
        sorted(batch_ids & supplement_ids),
        checks,
    )
    check(
        len(worklist) == 63 and len(worklist_ids) == 63,
        "worklist_63_unique",
        {"rows": len(worklist), "unique": len(worklist_ids)},
        checks,
    )
    check(
        len(queue) == 185 and len(queue_ids) == 185,
        "queue_185_unique",
        {"rows": len(queue), "unique": len(queue_ids)},
        checks,
    )
    check(
        len(human) == 22 and len(human_ids) == 22,
        "human_confirmed_22_unique",
        {"rows": len(human), "unique": len(human_ids)},
        checks,
    )
    check(
        worklist_ids <= supplement_ids,
        "worklist_is_supplement_subset",
        sorted(worklist_ids - supplement_ids),
        checks,
    )
    check(
        not (worklist_ids & human_ids),
        "pending_and_human_confirmed_disjoint",
        sorted(worklist_ids & human_ids),
        checks,
    )
    check(
        set(DECISIONS) <= worklist_ids,
        "all_explicit_decisions_in_worklist",
        sorted(set(DECISIONS) - worklist_ids),
        checks,
    )
    check(
        len(DECISIONS) == 22,
        "explicit_decision_count",
        len(DECISIONS),
        checks,
    )

    queue_status = Counter(row.get("queue_status", "") for row in queue)
    queue_split = Counter(row.get("split", "") for row in queue)
    check(
        queue_status == {"excluded": 100, "pending": 63, "confirmed": 22},
        "queue_status_distribution",
        dict(queue_status),
        checks,
    )
    check(
        queue_split == {"D_pool": 100, "D_dev": 85},
        "queue_split_distribution",
        dict(queue_split),
        checks,
    )

    batch_queue_ids = {
        pid for pid, row in queue_by_id.items()
        if row.get("split") == "D_pool"
    }
    supplement_queue_ids = {
        pid for pid, row in queue_by_id.items()
        if row.get("split") == "D_dev"
    }
    check(
        batch_ids == batch_queue_ids,
        "batch_matches_D_pool",
        {
            "missing_from_batch": sorted(batch_queue_ids - batch_ids),
            "extra_in_batch": sorted(batch_ids - batch_queue_ids),
        },
        checks,
    )
    check(
        supplement_ids == supplement_queue_ids,
        "supplement_matches_D_dev",
        {
            "missing_from_supplement": sorted(
                supplement_queue_ids - supplement_ids
            ),
            "extra_in_supplement": sorted(
                supplement_ids - supplement_queue_ids
            ),
        },
        checks,
    )

    confirmed_queue_ids = {
        pid for pid, row in queue_by_id.items()
        if row.get("queue_status") == "confirmed"
    }
    pending_queue_ids = {
        pid for pid, row in queue_by_id.items()
        if row.get("queue_status") == "pending"
    }
    check(
        human_ids == confirmed_queue_ids,
        "human_confirmed_matches_queue",
        {
            "missing_in_human_file": sorted(confirmed_queue_ids - human_ids),
            "extra_in_human_file": sorted(human_ids - confirmed_queue_ids),
        },
        checks,
    )
    check(
        worklist_ids == pending_queue_ids,
        "worklist_matches_pending_queue",
        {
            "missing_in_worklist": sorted(pending_queue_ids - worklist_ids),
            "extra_in_worklist": sorted(worklist_ids - pending_queue_ids),
        },
        checks,
    )

    # Check all 63 records against both raw source files.
    raw_missing = []
    raw_question_mismatch = []
    raw_answer_mismatch = []

    for pid in worklist_ids:
        raw = raw_by_id.get(pid)
        sup_raw = supplement_raw_by_id.get(pid)

        if raw is None or sup_raw is None:
            raw_missing.append(pid)
            continue

        if raw.get("question") != sup_raw.get("question"):
            raw_question_mismatch.append(pid)

        if str(raw.get("ground_truth")) != str(sup_raw.get("ground_truth")):
            raw_answer_mismatch.append(pid)

    check(not raw_missing, "all_pending_ids_in_raw_sources", raw_missing, checks)
    check(
        not raw_question_mismatch,
        "raw_question_consistency",
        raw_question_mismatch,
        checks,
    )
    check(
        not raw_answer_mismatch,
        "raw_ground_truth_consistency",
        raw_answer_mismatch,
        checks,
    )

    # Check the six-field v1 annotation schema.
    schema_errors = []
    for source_name, records in [
        ("batch", batch),
        ("supplement", supplement),
    ]:
        for row in records:
            pid = row.get("problem_id", "<missing>")
            if set(row.keys()) != EXPECTED_FIELDS:
                schema_errors.append(
                    f"{source_name}:{pid}:fields={sorted(row.keys())}"
                )
                continue
            labels = row.get("capabilities_manual")
            difficulty = row.get("difficulty_manual")
            if (
                not isinstance(labels, list)
                or not labels
                or not set(labels) <= VALID_CAPABILITIES
            ):
                schema_errors.append(f"{source_name}:{pid}:capabilities")
            if difficulty not in VALID_DIFFICULTIES:
                schema_errors.append(f"{source_name}:{pid}:difficulty")
            if row.get("schema_version") != "v1":
                schema_errors.append(f"{source_name}:{pid}:schema_version")

    check(not schema_errors, "v1_annotation_schema", schema_errors[:20], checks)

    # Verify the source hashes against the recorded source inspection.
    source_hash_keys = {
        "batch": ("gold_batch", PATHS["batch"]),
        "supplement": ("gold_supplement", PATHS["supplement"]),
        "gold_manifest": ("gold_manifest", PATHS["gold_manifest"]),
        "raw_train": ("raw_train", PATHS["raw_train"]),
        "supplement_raw": ("supplement_selected", PATHS["supplement_raw"]),
        "human_confirmed": ("human_confirmed", PATHS["human_confirmed"]),
    }

    source_hashes = {}
    hash_errors = []

    for name, (schema_key, path) in source_hash_keys.items():
        actual = sha256(path)
        expected = (
            schema.get("source_hashes", {})
            .get(schema_key, {})
            .get("actual_sha256")
        )
        source_hashes[name] = {
            "path": str(path.relative_to(BASE)),
            "actual_sha256": actual,
            "inspection_sha256": expected,
            "matches_inspection": actual == expected if expected else None,
        }
        if expected and actual != expected:
            hash_errors.append(name)

    check(not hash_errors, "source_hashes_match_inspection", hash_errors, checks)

    # The 41 no-change records retain their original annotation and note.
    no_change_ids = worklist_ids - set(DECISIONS)
    check(
        len(no_change_ids) == 41,
        "no_change_review_count",
        len(no_change_ids),
        checks,
    )

    failed_prechecks = [item for item in checks if not item["passed"]]
    if failed_prechecks:
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        report = {
            "status": "FAIL_PRECHECK",
            "checks": checks,
            "failed_checks": failed_prechecks,
            "candidate_created": False,
        }
        (REPORT_DIR / "gold_review_63_validation_report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print("PRECHECK: FAIL")
        for item in failed_prechecks:
            print("FAIL:", item["name"], item["detail"])
        print("No candidate was created.")
        raise SystemExit(1)

    # Build a complete ledger for all 63 pending records.
    ledger = []
    disagreement = []
    candidate_supplement = []

    for pid, original in supplement_by_id.items():
        row = dict(original)

        if pid not in worklist_ids:
            candidate_supplement.append(row)
            continue

        source_question = raw_by_id[pid]["question"]
        source_ground_truth = str(raw_by_id[pid]["ground_truth"])
        source_labels = list(original["capabilities_manual"])
        source_difficulty = original["difficulty_manual"]
        source_notes = str(original.get("notes", ""))

        if pid in DECISIONS:
            decision = DECISIONS[pid]
            final_labels = list(decision["capabilities"])
            if not final_labels or not set(final_labels) <= VALID_CAPABILITIES:
                raise ValueError(f"Invalid final labels for {pid}")

            final_notes = append_note(
                source_notes,
                decision["note"],
                decision["note_mode"],
            )
            row["capabilities_manual"] = final_labels
            row["notes"] = final_notes

            answer_status = decision["answer_status"]
            answer_decision = (
                decision["answer_decision"]
                if decision["answer_decision"] is not None
                else f"Keep raw source ground truth: {source_ground_truth}"
            )
            ambiguity = decision["ambiguity"]
            ambiguity_status = decision["ambiguity_status"]
            decision_reason = decision["reason"]
            decision_source = "USER_CONFIRMED"
            review_status = "REVIEWED_USER_DECISION"
        else:
            final_labels = source_labels
            final_notes = source_notes
            answer_status = "KEEP_SOURCE_GROUND_TRUTH"
            answer_decision = source_ground_truth
            ambiguity = False
            ambiguity_status = "NO_NEW_AMBIGUITY_IDENTIFIED"
            decision_reason = (
                "Reviewed in the 2026-11-16 assistant review pass. "
                "No correction was proposed for this record. Retain the "
                "existing Gold capabilities, source ground truth, difficulty, "
                "and existing annotation note."
            )
            decision_source = "ASSISTANT_REVIEW_NO_CHANGE"
            review_status = "REVIEWED_NO_CHANGE"

        final_difficulty = source_difficulty
        difficulty_status = "KEEP_EXISTING"

        ledger_row = {
            "problem_id": pid,
            "split": worklist_by_id[pid].get("split", "D_dev"),
            "review_status": review_status,
            "decision_source": decision_source,
            "source_capabilities": json.dumps(
                source_labels, ensure_ascii=False
            ),
            "final_capabilities": json.dumps(
                final_labels, ensure_ascii=False
            ),
            "capability_changed": str(source_labels != final_labels).lower(),
            "source_ground_truth": source_ground_truth,
            "answer_status": answer_status,
            "answer_decision": answer_decision,
            "source_difficulty": source_difficulty,
            "final_difficulty": final_difficulty,
            "difficulty_status": difficulty_status,
            "ambiguity_flag": str(ambiguity).lower(),
            "ambiguity_status": ambiguity_status,
            "decision_reason": decision_reason,
            "source_question": source_question,
            "source_annotation_notes": source_notes,
            "final_annotation_notes": final_notes,
            "reviewer": "User-confirmed / assistant-reviewed",
            "review_date": "2026-11-16",
        }
        ledger.append(ledger_row)

        if pid in DECISIONS:
            disagreement.append({
                "problem_id": pid,
                "split": worklist_by_id[pid].get("split", "D_dev"),
                "source_capabilities": json.dumps(
                    source_labels, ensure_ascii=False
                ),
                "final_capabilities": json.dumps(
                    final_labels, ensure_ascii=False
                ),
                "capability_changed": str(
                    source_labels != final_labels
                ).lower(),
                "source_difficulty": source_difficulty,
                "final_difficulty": final_difficulty,
                "ambiguity_flag": str(ambiguity).lower(),
                "answer_status": answer_status,
                "source_ground_truth": source_ground_truth,
                "answer_decision": answer_decision,
                "decision_reason": decision_reason,
            })

        candidate_supplement.append(row)

    ledger_by_id = index_by_id(ledger, "adjudication ledger")
    check(
        len(ledger) == 63 and set(ledger_by_id) == worklist_ids,
        "ledger_covers_all_63",
        {"rows": len(ledger), "ids": len(ledger_by_id)},
        checks,
    )

    changed_label_ids = {
        row["problem_id"]
        for row in ledger
        if row["capability_changed"] == "true"
    }
    ambiguous_ids = {
        row["problem_id"]
        for row in ledger
        if row["ambiguity_flag"] == "true"
    }

    # Candidate supplement must preserve exactly 85 records.
    candidate_supplement_by_id = index_by_id(
        candidate_supplement, "candidate supplement"
    )
    check(
        len(candidate_supplement) == 85,
        "candidate_supplement_count",
        len(candidate_supplement),
        checks,
    )

    # Prepare a staging folder inside the repository. Never use TEMP/AppData.
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    STAGING_DIR.mkdir(parents=False, exist_ok=False)

    try:
        staged_batch = STAGING_DIR / BATCH_NAME
        staged_supplement = STAGING_DIR / SUPPLEMENT_NAME
        staged_manifest = STAGING_DIR / MANIFEST_NAME

        # Batch 100 is copied byte-for-byte, not reserialized.
        shutil.copyfile(PATHS["batch"], staged_batch)
        write_jsonl(staged_supplement, candidate_supplement)

        candidate_batch = read_jsonl(staged_batch)
        candidate_supp = read_jsonl(staged_supplement)
        candidate_batch_by_id = index_by_id(
            candidate_batch, "candidate batch"
        )
        candidate_supp_by_id = index_by_id(
            candidate_supp, "candidate supplement"
        )

        post_checks = []

        check(
            len(candidate_batch) == 100,
            "candidate_batch_count",
            len(candidate_batch),
            post_checks,
        )
        check(
            len(candidate_supp) == 85,
            "candidate_supplement_count",
            len(candidate_supp),
            post_checks,
        )
        check(
            len(set(candidate_batch_by_id) | set(candidate_supp_by_id)) == 185,
            "candidate_total_unique",
            len(set(candidate_batch_by_id) | set(candidate_supp_by_id)),
            post_checks,
        )
        check(
            set(candidate_batch_by_id) == batch_ids,
            "candidate_batch_inventory_unchanged",
            True,
            post_checks,
        )
        check(
            set(candidate_supp_by_id) == supplement_ids,
            "candidate_supplement_inventory_unchanged",
            True,
            post_checks,
        )
        check(
            sha256(staged_batch) == sha256(PATHS["batch"]),
            "batch_byte_identical",
            sha256(staged_batch),
            post_checks,
        )

        # Only the 22 explicitly decided pending IDs may differ.
        unexpected_changes = []
        for pid, old in supplement_by_id.items():
            new = candidate_supp_by_id[pid]

            if pid in DECISIONS:
                allowed_old = {
                    k: v for k, v in old.items()
                    if k not in {"capabilities_manual", "notes"}
                }
                allowed_new = {
                    k: v for k, v in new.items()
                    if k not in {"capabilities_manual", "notes"}
                }
                if allowed_old != allowed_new:
                    unexpected_changes.append(pid)
            elif old != new:
                unexpected_changes.append(pid)

        check(
            not unexpected_changes,
            "only_explicit_decisions_changed",
            unexpected_changes,
            post_checks,
        )

        human_changed = []
        for pid in human_ids:
            if supplement_by_id[pid] != candidate_supp_by_id[pid]:
                human_changed.append(pid)
        check(
            not human_changed,
            "human_confirmed_22_unchanged",
            human_changed,
            post_checks,
        )

        invalid_records = []
        for source_name, records in [
            ("batch", candidate_batch),
            ("supplement", candidate_supp),
        ]:
            for record in records:
                pid = record["problem_id"]
                if set(record.keys()) != EXPECTED_FIELDS:
                    invalid_records.append(f"{source_name}:{pid}:fields")
                    continue
                labels = record["capabilities_manual"]
                if (
                    not isinstance(labels, list)
                    or not labels
                    or not set(labels) <= VALID_CAPABILITIES
                ):
                    invalid_records.append(f"{source_name}:{pid}:capabilities")
                if record["difficulty_manual"] not in VALID_DIFFICULTIES:
                    invalid_records.append(f"{source_name}:{pid}:difficulty")
                if record["schema_version"] != "v1":
                    invalid_records.append(f"{source_name}:{pid}:schema")

        check(
            not invalid_records,
            "candidate_schema_and_labels",
            invalid_records[:20],
            post_checks,
        )

        check(
            len(ledger) == 63,
            "ledger_record_count",
            len(ledger),
            post_checks,
        )
        check(
            len(DECISIONS) == 22 and len(no_change_ids) == 41,
            "review_decision_partition",
            {"user_confirmed": len(DECISIONS), "no_change": len(no_change_ids)},
            post_checks,
        )

        failed_postchecks = [
            item for item in post_checks if not item["passed"]
        ]

        validation = {
            "review_date": "2026-11-16",
            "status": "PASS" if not failed_postchecks else "FAIL",
            "freeze_status": "NOT_FROZEN",
            "candidate_status": (
                "VALIDATED_PENDING_USER_APPROVAL"
                if not failed_postchecks else "VALIDATION_FAILED"
            ),
            "counts": {
                "batch": len(candidate_batch),
                "supplement": len(candidate_supp),
                "total": len(candidate_batch) + len(candidate_supp),
                "reviewed_pending": len(ledger),
                "user_confirmed_decisions": len(DECISIONS),
                "reviewed_no_change": len(no_change_ids),
                "capability_changed_records": len(changed_label_ids),
                "ambiguity_flagged_records": len(ambiguous_ids),
                "human_confirmed_preserved": len(human_ids),
            },
            "changed_capability_ids": sorted(changed_label_ids),
            "ambiguity_ids": sorted(ambiguous_ids),
            "source_hashes_before_build": source_hashes,
            "checks": checks + post_checks,
            "failed_checks": failed_postchecks,
            "gold_vfinal_modified": False,
            "raw_ground_truth_modified": False,
            "human_confirmed_modified": False,
        }

        if failed_postchecks:
            (REPORT_DIR / "gold_review_63_validation_report.json").write_text(
                json.dumps(validation, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            raise RuntimeError(
                "Candidate validation failed. Staging folder was retained "
                "for inspection; it was NOT promoted to candidate."
            )

        # Create candidate manifest only after all validations pass.
        manifest = {
            "dataset_name": "Gold vNext candidate",
            "version": "vNext-candidate-2026-11-16",
            "candidate_status": "VALIDATED_PENDING_USER_APPROVAL",
            "freeze_status": "NOT_FROZEN",
            "created_date": "2026-11-16",
            "records": 185,
            "batch_100_records": 100,
            "supplement_records": 85,
            "D_pool_records": 100,
            "D_dev_records": 85,
            "reviewed_pending_records": 63,
            "user_confirmed_decisions": 22,
            "reviewed_no_change_records": 41,
            "capability_changed_records": len(changed_label_ids),
            "ambiguity_flagged_records": len(ambiguous_ids),
            "human_confirmed_records_preserved": 22,
            "source_files": {
                "batch": str(PATHS["batch"].relative_to(BASE)),
                "supplement": str(PATHS["supplement"].relative_to(BASE)),
                "raw_train": str(PATHS["raw_train"].relative_to(BASE)),
                "supplement_raw": str(
                    PATHS["supplement_raw"].relative_to(BASE)
                ),
            },
            "output_files": {
                "batch": f"data/{CANDIDATE_NAME}/{BATCH_NAME}",
                "supplement": f"data/{CANDIDATE_NAME}/{SUPPLEMENT_NAME}",
            },
            "source_sha256": source_hashes,
            "candidate_sha256": {
                "batch": sha256(staged_batch),
                "supplement": sha256(staged_supplement),
            },
            "ground_truth_modified": False,
            "difficulty_modified": False,
            "gold_vfinal_modified": False,
            "human_confirmed_records_modified": False,
            "validation_status": "PASS",
            "approval_required_before_freeze": True,
        }

        staged_manifest.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # Verify original source hashes again before promotion.
        source_hashes_after = {
            name: sha256(path)
            for name, (_, path) in source_hash_keys.items()
        }
        source_unchanged = all(
            source_hashes_after[name] == values["actual_sha256"]
            for name, values in source_hashes.items()
        )
        if not source_unchanged:
            raise RuntimeError(
                "A source file changed during build. Candidate not promoted."
            )

        # Atomic rename within the same repository filesystem.
        os.replace(STAGING_DIR, CANDIDATE_DIR)

        final_batch = CANDIDATE_DIR / BATCH_NAME
        final_supplement = CANDIDATE_DIR / SUPPLEMENT_NAME
        final_manifest = CANDIDATE_DIR / MANIFEST_NAME

        # Re-check final candidate paths after promotion.
        final_checks = [
            {
                "name": "candidate_directory_promoted",
                "passed": CANDIDATE_DIR.is_dir(),
                "detail": str(CANDIDATE_DIR),
            },
            {
                "name": "candidate_files_exist",
                "passed": all(
                    p.is_file()
                    for p in [final_batch, final_supplement, final_manifest]
                ),
                "detail": "batch, supplement, manifest",
            },
            {
                "name": "source_hashes_unchanged_after_build",
                "passed": source_unchanged,
                "detail": source_hashes_after,
            },
        ]

        final_pass = all(item["passed"] for item in final_checks)
        validation["checks"].extend(final_checks)
        validation["status"] = "PASS" if final_pass else "FAIL"
        validation["candidate_status"] = (
            "VALIDATED_PENDING_USER_APPROVAL"
            if final_pass else "POST_PROMOTION_CHECK_FAILED"
        )
        validation["source_hashes_after_build"] = source_hashes_after
        validation["candidate_sha256_final"] = {
            "batch": sha256(final_batch),
            "supplement": sha256(final_supplement),
            "manifest": sha256(final_manifest),
        }

        # Reports.
        REPORT_DIR.mkdir(parents=True, exist_ok=True)

        ledger_path = REPORT_DIR / "user_adjudication_2026-11-16.csv"
        disagreement_path = (
            REPORT_DIR / "gold_review_63_disagreement_report.csv"
        )
        final_report_path = (
            REPORT_DIR / "gold_review_63_final_adjudication.md"
        )
        validation_json_path = (
            REPORT_DIR / "gold_review_63_validation_report.json"
        )
        validation_md_path = (
            REPORT_DIR / "gold_review_63_validation_report.md"
        )

        write_csv(ledger_path, ledger)
        write_csv(disagreement_path, disagreement)

        decision_status_counts = Counter(
            row["review_status"] for row in ledger
        )
        ambiguity_status_counts = Counter(
            row["ambiguity_status"] for row in ledger
        )

        final_lines = [
            "# Gold Review — Final Adjudication 2026-11-16",
            "",
            "## Review scope",
            "",
            f"- Pending worklist records: **{len(worklist)}**",
            f"- User-confirmed decisions: **{len(DECISIONS)}**",
            f"- Reviewed with no annotation change: **{len(no_change_ids)}**",
            f"- Total reviewed: **{len(ledger)}**",
            f"- Capability-changed records: **{len(changed_label_ids)}**",
            f"- Ambiguity-flagged records: **{len(ambiguous_ids)}**",
            "- Difficulty changes: **0**",
            "- Raw ground-truth changes: **0**",
            "- Gold vFinal modifications: **0**",
            "",
            "## Review status",
            "",
        ]

        for key, value in sorted(decision_status_counts.items()):
            final_lines.append(f"- `{key}`: {value}")

        final_lines += ["", "## Ambiguity status", ""]
        for key, value in sorted(ambiguity_status_counts.items()):
            final_lines.append(f"- `{key}`: {value}")

        final_lines += [
            "",
            "## Explicitly retained assumptions and source caveats",
            "",
            "- `gsm8k_train_00239`: 5% overlap is interpreted as "
            "5 percentage points of the total germ population; answer 30%.",
            "- `gsm8k_train_00713`: target answer 15% is retained under the "
            "assumptions that infected mosquito groups are disjoint and "
            "the vaccine reduction applies to both viruses, despite the "
            "malaria-vaccine wording.",
            "- `gsm8k_train_00830`: the current raw dataset record has "
            "ground truth 25 for total meal cost. The separately supplied "
            "variant asks for the lassi price and derives $2.50. The two "
            "targets are not interchangeable.",
            "- `gsm8k_train_01200`: interpretation A is accepted.",
            "- `gsm8k_train_03048`: the three book categories are assumed "
            "mutually exclusive.",
            "",
            "## Candidate",
            "",
            f"- Candidate directory: `{CANDIDATE_DIR}`",
            "- Candidate validation: **PASS**",
            "- Freeze status: **NOT FROZEN**",
            "- User approval required before release/freeze.",
            "",
        ]
        final_report_path.write_text(
            "\n".join(final_lines), encoding="utf-8"
        )

        validation_json_path.write_text(
            json.dumps(validation, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        validation_lines = [
            "# Gold vNext Candidate Validation — 2026-11-16",
            "",
            f"- Status: **{validation['status']}**",
            f"- Candidate status: **{validation['candidate_status']}**",
            "- Freeze status: **NOT FROZEN**",
            "",
            "## Counts",
            "",
        ]
        for key, value in validation["counts"].items():
            validation_lines.append(f"- {key}: **{value}**")

        validation_lines += ["", "## Checks", ""]
        for item in validation["checks"]:
            status = "PASS" if item["passed"] else "FAIL"
            validation_lines.append(
                f"- **{status}** `{item['name']}`: {item['detail']}"
            )

        validation_lines += [
            "",
            "## Source protection",
            "",
            "- Gold vFinal source files unchanged.",
            "- Raw source files unchanged.",
            "- Human-confirmed records unchanged.",
            "- Batch 100 copied byte-for-byte.",
            "- No ground-truth or difficulty field was modified.",
            "",
        ]
        validation_md_path.write_text(
            "\n".join(validation_lines), encoding="utf-8"
        )

        print()
        print("GOLD VNEXT CANDIDATE BUILD:", validation["status"])
        print("Batch records:", len(candidate_batch))
        print("Supplement records:", len(candidate_supp))
        print("Total records:", len(candidate_batch) + len(candidate_supp))
        print("Pending records reviewed:", len(ledger))
        print("User-confirmed decisions:", len(DECISIONS))
        print("No-change reviewed records:", len(no_change_ids))
        print("Capability-changed records:", len(changed_label_ids))
        print("Ambiguity-flagged records:", len(ambiguous_ids))
        print("Human-confirmed records preserved:", len(human_ids))
        print("Gold vFinal modified: False")
        print("Raw ground truth modified: False")
        print("Freeze status: NOT FROZEN")
        print("Candidate:", CANDIDATE_DIR)
        print("Ledger:", ledger_path)
        print("Disagreement report:", disagreement_path)
        print("Final adjudication report:", final_report_path)
        print("Validation report:", validation_json_path)
        print("Validation Markdown:", validation_md_path)

        if not final_pass:
            raise SystemExit(1)

    except Exception:
        # Keep any failed staging directory inside the repository for audit.
        print("BUILD FAILED. Candidate was not approved or frozen.")
        if STAGING_DIR.exists():
            print("Staging retained for inspection:", STAGING_DIR)
        raise


if __name__ == "__main__":
    main()
