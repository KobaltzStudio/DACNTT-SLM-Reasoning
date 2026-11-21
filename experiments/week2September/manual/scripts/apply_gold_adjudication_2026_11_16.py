from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path


REPO = Path(r"C:\KLTN-SLM-Reasoning")

WORKLIST = (
    REPO
    / "experiments/week2September/manual/data/gold/review_2026-11-15"
    / "adjudication_worklist_63_pending.csv"
)

OUTPUT_DIR = (
    REPO
    / "experiments/week2September/manual/reports/gold/review_2026-11-16"
)

ALLOWED_CAPABILITIES = {
    "addition",
    "subtraction",
    "multiplication",
    "division",
    "fraction",
    "percentage",
    "ratio",
}

# These are the decisions supplied by the reviewer on 2026-11-16.
# The original Gold vFinal files are deliberately not modified.
DECISIONS = [
    {
        "problem_id": "gsm8k_train_00666",
        "decision_status": "CONFIRMED",
        "final_capabilities": [
            "addition", "multiplication", "fraction"
        ],
        "answer_status": "CONFIRMED",
        "answer_decision": "27",
        "difficulty_decision": "KEEP_EXISTING",
        "ambiguity_decision": "NO_NEW_AMBIGUITY",
        "decision_reason": (
            "Dataset-original reasoning gives Anthony 8 cats and 4 dogs; "
            "Leonel 4 cats and 11 dogs; total 27. Correct the Gold note "
            "to 27 and retain the existing capability labels."
        ),
    },
    {
        "problem_id": "gsm8k_train_00830",
        "decision_status": "CONFIRMED_WITH_SOURCE_CAVEAT",
        "final_capabilities": [
            "addition", "subtraction", "multiplication", "percentage"
        ],
        "answer_status": "SOURCE_REASONING_ACCEPTED_WITH_CAVEAT",
        "answer_decision": "$2.50",
        "difficulty_decision": "KEEP_EXISTING",
        "ambiguity_decision": (
            "SOURCE_TEXT_SAYS_WITH_TAX_BUT_REASONING_DOES_NOT_CALCULATE_TAX"
        ),
        "decision_reason": (
            "The supplied source reasoning calculates 3*2=6, 4*3=12, "
            "tip=25%*18=4.50, then subtracts 18+4.50 from 25 to obtain "
            "$2.50. Add subtraction to the capability labels. Preserve "
            "the source caveat: the question says 'with tax', but the "
            "reasoning does not separately calculate tax."
        ),
    },
    {
        "problem_id": "gsm8k_train_00840",
        "decision_status": "CONFIRMED",
        "final_capabilities": ["multiplication", "ratio"],
        "answer_status": "CONFIRMED",
        "answer_decision": "$100",
        "difficulty_decision": "KEEP_EXISTING",
        "ambiguity_decision": "NO_NEW_AMBIGUITY",
        "decision_reason": (
            "Amy receives one ratio part and Sandra receives two. "
            "Sandra receives 2*50=$100. Remove division; retain "
            "multiplication and ratio. The erroneous $25 transcript "
            "is not used as the correct solution."
        ),
    },
    {
        "problem_id": "gsm8k_train_01200",
        "decision_status": "CONFIRMED_WITH_INTERPRETATION",
        "final_capabilities": [
            "addition", "multiplication", "fraction"
        ],
        "answer_status": "CONFIRMED_UNDER_INTERPRETATION_A",
        "answer_decision": "$42.00",
        "difficulty_decision": "KEEP_EXISTING",
        "ambiguity_decision": (
            "INTERPRET_AS_FOUR_STEAKS_EACH_WEIGHING_HALF_A_POUND"
        ),
        "decision_reason": (
            "Reviewer accepts interpretation A: four steaks at 0.5 lb "
            "each, giving 2 lb of steak. Steak costs $30; chicken costs "
            "$12; total is $42. Retain existing capability labels."
        ),
    },
    {
        "problem_id": "gsm8k_train_03048",
        "decision_status": "CONFIRMED_WITH_CATEGORY_ASSUMPTION",
        "final_capabilities": [
            "subtraction", "multiplication", "division", "percentage"
        ],
        "answer_status": "CONFIRMED_UNDER_DISJOINT_CATEGORY_ASSUMPTION",
        "answer_decision": "20%",
        "difficulty_decision": "KEEP_EXISTING",
        "ambiguity_decision": (
            "NOVELS_GRAPHIC_NOVELS_AND_COMIC_BOOKS_ARE_DISJOINT_GROUPS"
        ),
        "decision_reason": (
            "Assume novels, graphic novels, and comic books are three "
            "mutually exclusive categories. Novels=0.65*120=78; "
            "comics=120-78-18=24; percentage=24/120*100=20%. "
            "Retain existing capability labels and document the assumption."
        ),
    },
    {
        "problem_id": "gsm8k_train_06921",
        "decision_status": "CONFIRMED",
        "final_capabilities": [
            "subtraction", "multiplication", "division", "percentage"
        ],
        "answer_status": "KEEP_EXISTING_GOLD_ANSWER",
        "answer_decision": "17%",
        "difficulty_decision": "KEEP_EXISTING",
        "ambiguity_decision": "NO_NEW_AMBIGUITY",
        "decision_reason": (
            "Add division because profit percentage requires "
            "(selling_price-cost_price)/cost_price*100. "
            "The percentage calculation has a necessary division step."
        ),
    },
    {
        "problem_id": "gsm8k_train_07158",
        "decision_status": "CONFIRMED",
        "final_capabilities": [
            "addition", "multiplication", "division", "ratio"
        ],
        "answer_status": "KEEP_EXISTING_GOLD_ANSWER",
        "answer_decision": "120 pints",
        "difficulty_decision": "KEEP_EXISTING",
        "ambiguity_decision": "NO_NEW_AMBIGUITY",
        "decision_reason": (
            "Add addition to the capability labels. The cider recipe "
            "requires combining 20 golden apples and 40 pink lady apples "
            "per pint; the full reasoning also uses multiplication, "
            "ratio allocation, and division."
        ),
    },
    {
        "problem_id": "gsm8k_train_07349",
        "decision_status": "CONFIRMED",
        "final_capabilities": ["fraction", "ratio"],
        "answer_status": "KEEP_EXISTING_GOLD_ANSWER",
        "answer_decision": "28 cups",
        "difficulty_decision": "KEEP_EXISTING",
        "ambiguity_decision": "NO_NEW_AMBIGUITY",
        "decision_reason": (
            "Retain fraction and ratio. Remove multiplication and division "
            "under Guideline v3: do not label arithmetic implementation "
            "operations when the reasoning requirement is fraction of "
            "a quantity and ratio interpretation."
        ),
    },
    {
        "problem_id": "gsm8k_train_00713",
        "decision_status": "CAPABILITY_REVIEWED_ANSWER_CONDITIONAL",
        "final_capabilities": [
            "addition", "subtraction", "multiplication", "percentage"
        ],
        "answer_status": "CONDITIONAL_PENDING_OVERLAP_ASSUMPTION",
        "answer_decision": (
            "20% if malaria-infected and Zika-infected mosquito groups "
            "are disjoint"
        ),
        "difficulty_decision": "KEEP_EXISTING",
        "ambiguity_decision": (
            "OVERLAP_BETWEEN_MALARIA_AND_ZIKA_INFECTED_MOSQUITO_GROUPS_UNSPECIFIED"
        ),
        "decision_reason": (
            "The malaria vaccine affects malaria only. Malaria risk="
            "0.40*0.50*(1-0.50)=0.10; Zika risk=0.20*0.50=0.10. "
            "The sum is 20% only if the two infected-mosquito groups "
            "are disjoint (or the problem intends direct addition). "
            "Keep the answer conditional until that assumption is accepted."
        ),
    },
]


def read_csv(path: Path) -> tuple[list[dict], list[str]]:
    if not path.is_file():
        raise FileNotFoundError(f"Required worklist not found: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fields = list(reader.fieldnames or [])

    if not rows:
        raise ValueError("The adjudication worklist is empty.")
    if "problem_id" not in fields:
        raise ValueError("Worklist is missing required column: problem_id")

    return rows, fields


def validate(rows: list[dict]) -> None:
    ids = [row["problem_id"] for row in rows]

    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate problem_id found in the worklist.")

    if len(rows) != 63:
        raise ValueError(
            f"Expected 63 pending worklist rows, found {len(rows)}."
        )

    decision_ids = [item["problem_id"] for item in DECISIONS]
    if len(decision_ids) != len(set(decision_ids)):
        raise ValueError("Duplicate problem_id found in DECISIONS.")

    missing = sorted(set(decision_ids) - set(ids))
    if missing:
        raise ValueError(
            "Decision IDs are absent from the pending worklist: "
            + ", ".join(missing)
        )

    for item in DECISIONS:
        labels = item["final_capabilities"]
        if not labels:
            raise ValueError(
                f"{item['problem_id']} has an empty capability list."
            )
        if len(labels) != len(set(labels)):
            raise ValueError(
                f"{item['problem_id']} has duplicate capability labels."
            )

        invalid = sorted(set(labels) - ALLOWED_CAPABILITIES)
        if invalid:
            raise ValueError(
                f"{item['problem_id']} has invalid labels: {invalid}"
            )


def main() -> None:
    rows, worklist_fields = read_csv(WORKLIST)
    validate(rows)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    row_by_id = {row["problem_id"]: row for row in rows}
    ledger = []

    for decision in DECISIONS:
        source_row = row_by_id[decision["problem_id"]]

        record = {
            "problem_id": decision["problem_id"],
            "split": source_row.get("split", ""),
            "source_gold_capabilities": source_row.get(
                "gold_capabilities", ""
            ),
            "final_capabilities": json.dumps(
                decision["final_capabilities"],
                ensure_ascii=False,
            ),
            "decision_status": decision["decision_status"],
            "answer_status": decision["answer_status"],
            "answer_decision": decision["answer_decision"],
            "difficulty_decision": decision["difficulty_decision"],
            "ambiguity_decision": decision["ambiguity_decision"],
            "decision_reason": decision["decision_reason"],
            "reviewer": "User",
            "review_date": "2026-11-16",
        }
        ledger.append(record)

    ledger_path = OUTPUT_DIR / "user_adjudication_2026-11-16.csv"
    ledger_fields = list(ledger[0].keys())

    with ledger_path.open(
        "w", encoding="utf-8-sig", newline=""
    ) as f:
        writer = csv.DictWriter(f, fieldnames=ledger_fields)
        writer.writeheader()
        writer.writerows(ledger)

    status_counts = Counter(
        item["decision_status"] for item in DECISIONS
    )
    answer_counts = Counter(
        item["answer_status"] for item in DECISIONS
    )

    summary = {
        "review_date": "2026-11-16",
        "worklist_path": str(WORKLIST),
        "worklist_rows": len(rows),
        "decision_rows": len(DECISIONS),
        "unique_decision_ids": len(
            {item["problem_id"] for item in DECISIONS}
        ),
        "remaining_unreviewed_rows": len(rows) - len(DECISIONS),
        "decision_status_counts": dict(status_counts),
        "answer_status_counts": dict(answer_counts),
        "gold_vfinal_modified": False,
        "original_worklist_modified": False,
        "ledger_path": str(ledger_path),
    }

    summary_json = OUTPUT_DIR / "adjudication_summary_2026-11-16.json"
    summary_json.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    summary_md = OUTPUT_DIR / "adjudication_summary_2026-11-16.md"
    lines = [
        "# Gold Adjudication Summary — 2026-11-16",
        "",
        f"- Pending worklist rows at input: **{len(rows)}**",
        f"- Decisions recorded: **{len(DECISIONS)}**",
        f"- Rows not yet reviewed: **{len(rows) - len(DECISIONS)}**",
        "- Original worklist modified: **No**",
        "- Gold vFinal modified: **No**",
        "",
        "## Decision status",
        "",
    ]

    for key, value in sorted(status_counts.items()):
        lines.append(f"- `{key}`: {value}")

    lines += ["", "## Answer status", ""]
    for key, value in sorted(answer_counts.items()):
        lines.append(f"- `{key}`: {value}")

    lines += [
        "",
        "## Important pending issue",
        "",
        "`gsm8k_train_00713` has capability labels reviewed, but its "
        "20% answer remains conditional on the assumption that the "
        "malaria-infected and Zika-infected mosquito groups are disjoint "
        "(or that the dataset intends direct addition of the two rates).",
        "",
        "## Remaining work",
        "",
        "Review the other 54 rows individually. Do not mark them confirmed "
        "by default. Do not create or freeze Gold vNext until all required "
        "review decisions and validations are complete.",
        "",
    ]

    summary_md.write_text("\n".join(lines), encoding="utf-8")

    print("PASS: adjudication input validation")
    print(f"Worklist rows: {len(rows)}")
    print(f"Decisions recorded: {len(DECISIONS)}")
    print(f"Rows still requiring review: {len(rows) - len(DECISIONS)}")
    print(f"Ledger: {ledger_path}")
    print(f"Summary CSV rows: {len(ledger)}")
    print("Original worklist: unchanged")
    print("Gold vFinal: unchanged")


if __name__ == "__main__":
    main()
