import csv
import json
from pathlib import Path

ROOT = Path(".")
INPUT = ROOT / "reports/capability/d3_audit/adjudication_evidence.csv"
OUTPUT_CSV = ROOT / "reports/capability/d3_audit/adjudication_final_ai.csv"
OUTPUT_JSON = ROOT / "reports/capability/d3_audit/adjudication_decisions.json"

DECISIONS = {
    "gsm8k_train_00325": {
        "capabilities": ["division", "fraction", "subtraction"],
        "difficulty": "medium",
        "rationale": (
            "The problem requires converting 1000 feet into 25-foot sections, "
            "then giving away one quarter and retaining half of the remainder. "
            "Division is independently required to determine the number of "
            "equal-length sections; fraction and subtraction are also required."
        ),
        "guideline": "Guideline v3 Rule 2; Rule 3; Rule 8"
    },
    "gsm8k_train_00761": {
        "capabilities": ["division", "fraction"],
        "difficulty": "medium",
        "rationale": (
            "Fifteen spotted dogs represent one half of the total, so the whole "
            "is inferred by inverse division. One fifth of the whole is then "
            "calculated. Fraction and division are both required."
        ),
        "guideline": "Guideline v3 Rule 2; Rule 3; Rule 8"
    },
    "gsm8k_train_00769": {
        "capabilities": ["multiplication", "percentage", "subtraction"],
        "difficulty": "medium",
        "rationale": (
            "The probabilities of losing both and winning both lawsuits are "
            "calculated by multiplying independent event probabilities. "
            "Their difference is expressed in percentage points."
        ),
        "guideline": "Guideline v3 Rule 8; Rule 9; Section 15"
    },
    "gsm8k_train_01013": {
        "capabilities": ["addition", "fraction"],
        "difficulty": "medium",
        "rationale": (
            "The quantities of consumed soda, sparkling water, and juice are "
            "determined using fractions of the stated quantities, then combined. "
            "Fraction is retained as the fractional-quantity capability; "
            "multiplication is not added merely because it is one way to "
            "evaluate a fraction."
        ),
        "guideline": "Guideline v3 Rule 3; Rule 8; Section 15"
    },
    "gsm8k_train_01280": {
        "capabilities": ["addition", "fraction", "subtraction"],
        "difficulty": "easy",
        "rationale": (
            "The numbers of men and women are determined from fractions of "
            "the total. Their counts are combined and subtracted from the "
            "total to determine the number of children."
        ),
        "guideline": "Guideline v3 Rule 3; Rule 8"
    },
    "gsm8k_train_01334": {
        "capabilities": ["division", "multiplication", "ratio", "subtraction"],
        "difficulty": "medium",
        "rationale": (
            "The total number of cards is divided into 20 ratio parts. "
            "The value of one part is multiplied by the difference of two "
            "ratio terms to obtain the difference in cards."
        ),
        "guideline": "Guideline v3 Rule 2; Rule 6; Rule 8; Section 15"
    },
    "gsm8k_train_01600": {
        "capabilities": ["division", "multiplication", "ratio"],
        "difficulty": "medium",
        "rationale": (
            "The revenue is allocated across 15 ratio parts. The value of "
            "one part is multiplied by the four salary parts."
        ),
        "guideline": "Guideline v3 Rule 2; Rule 6; Rule 8; Section 15"
    },
    "gsm8k_train_02342": {
        "capabilities": ["division", "multiplication", "percentage", "subtraction"],
        "difficulty": "hard",
        "rationale": (
            "The solution derives boys and girls from percentages, calculates "
            "the boys who do not play, doubles that count for girls who play, "
            "and expresses the result as a percentage of all girls. "
            "This combines complementary groups and part-to-whole reasoning."
        ),
        "guideline": "Guideline v3 Rule 2; Rule 8; Rule 9"
    },
    "gsm8k_train_02754": {
        "capabilities": ["addition", "fraction", "subtraction"],
        "difficulty": "medium",
        "rationale": (
            "Samuel's initial quantity is obtained by adding 20 to Bonnie's "
            "quantity. The fractions eaten and used for pie are calculated "
            "from Samuel's quantity, then subtracted to determine what remains."
        ),
        "guideline": "Guideline v3 Rule 3; Rule 8; Section 15"
    },
    "gsm8k_train_02858": {
        "capabilities": ["division", "multiplication", "percentage", "subtraction"],
        "difficulty": "medium",
        "rationale": (
            "The number of Julian's female friends is calculated from a "
            "percentage. Boyd has twice that number of female friends; "
            "subtracting from Boyd's total gives boys, and a part-to-whole "
            "percentage is then calculated."
        ),
        "guideline": "Guideline v3 Rule 2; Rule 8"
    },
    "gsm8k_train_02919": {
        "capabilities": ["fraction", "subtraction"],
        "difficulty": "medium",
        "rationale": (
            "The number of women is obtained as half the guests, and the "
            "number of children is obtained by subtracting known groups "
            "from the total. The fraction of men who leave and the remaining "
            "people are then determined by subtraction. No separate addition "
            "capability is necessary for the required reasoning."
        ),
        "guideline": "Guideline v3 Rule 2; Rule 3; Rule 8; Section 15"
    },
    "gsm8k_train_02997": {
        "capabilities": ["addition", "fraction", "subtraction"],
        "difficulty": "easy",
        "rationale": (
            "The blue and red quantities are determined from fractions of "
            "the total. These known quantities are added and subtracted "
            "from the total to obtain the black cars."
        ),
        "guideline": "Guideline v3 Rule 3; Rule 8"
    },
    "gsm8k_train_03016": {
        "capabilities": ["division", "multiplication", "percentage"],
        "difficulty": "medium",
        "rationale": (
            "The number of students receiving cards is calculated from "
            "60 percent of the class, then multiplied by the unit cost. "
            "The spending is compared with the total budget as a percentage."
        ),
        "guideline": "Guideline v3 Rule 2; Rule 8; Section 15"
    },
    "gsm8k_train_03125": {
        "capabilities": ["addition", "percentage"],
        "difficulty": "medium",
        "rationale": (
            "The insurance charge and tax are calculated as percentages "
            "according to the stated order, then added to the MSRP. "
            "Percentage captures the percentage reasoning; multiplication "
            "is not added solely as an implementation of percentage."
        ),
        "guideline": "Guideline v3 Rule 8; Section 15"
    },
    "gsm8k_train_03140": {
        "capabilities": ["addition", "division", "percentage"],
        "difficulty": "medium",
        "rationale": (
            "The fixed ten-dollar discount is reversed by addition. "
            "The remaining price is half the original price, so inverse "
            "division is required to recover the original price."
        ),
        "guideline": "Guideline v3 Rule 2; Rule 8"
    },
    "gsm8k_train_03263": {
        "capabilities": ["addition", "division", "fraction"],
        "difficulty": "medium",
        "rationale": (
            "The body, tail, and head are related through fractional "
            "proportions. Their lengths are combined to express the total "
            "as a multiple of the body; inverse division recovers the body, "
            "and the tail is then obtained as one half of it."
        ),
        "guideline": "Guideline v3 Rule 2; Rule 3; Rule 8"
    },
    "gsm8k_train_03390": {
        "capabilities": [
            "addition", "division", "fraction",
            "multiplication", "ratio"
        ],
        "difficulty": "hard",
        "rationale": (
            "The total animals are allocated by a goat-to-sheep ratio. "
            "Fractions of each group are sold, quantities are multiplied "
            "by their respective prices, and the two revenues are added."
        ),
        "guideline": "Guideline v3 Rule 2; Rule 3; Rule 6; Rule 8; Section 15"
    },
    "gsm8k_train_04426": {
        "capabilities": ["division", "multiplication", "ratio", "subtraction"],
        "difficulty": "medium",
        "rationale": (
            "The total photos are divided into ratio parts. The difference "
            "between the two ratio allocations is multiplied by the value "
            "of one part."
        ),
        "guideline": "Guideline v3 Rule 2; Rule 6; Rule 8; Section 15"
    },
    "gsm8k_train_04617": {
        "capabilities": ["addition", "division", "multiplication", "ratio"],
        "difficulty": "medium",
        "rationale": (
            "The difference of two ratio terms corresponds to four students, "
            "allowing the value of one part to be inferred by division. "
            "The total number of students is obtained by adding the boys' "
            "and girls' allocations. Ratio is central."
        ),
        "guideline": "Guideline v3 Rule 2; Rule 6; Rule 8; Section 15"
    },
    "gsm8k_train_04862": {
        "capabilities": ["addition", "multiplication", "percentage", "subtraction"],
        "difficulty": "medium",
        "rationale": (
            "The remaining percentage in each bottle is calculated by "
            "subtraction from 100 percent. The remaining quantity across "
            "two equivalent bottles is combined, requiring multiplication "
            "for the repeated quantity, and added to the remainder of the "
            "first bottle."
        ),
        "guideline": "Guideline v3 Rule 8; Section 15"
    },
    "gsm8k_train_05194": {
        "capabilities": ["addition", "percentage", "subtraction"],
        "difficulty": "easy",
        "rationale": (
            "The tax is calculated as a percentage of the bill and added "
            "to the bill. The total is subtracted from the payment to find "
            "the tip."
        ),
        "guideline": "Guideline v3 Rule 8; Section 15"
    },
    "gsm8k_train_05715": {
        "capabilities": [
            "addition", "fraction", "multiplication",
            "percentage", "subtraction"
        ],
        "difficulty": "medium",
        "rationale": (
            "The meal items are added, the two wine glasses require "
            "multiplication, half the entree price is discounted, and "
            "the tip is 20 percent of the full pre-discount meal cost. "
            "The discounted bill and tip are combined."
        ),
        "guideline": "Guideline v3 Rule 3; Rule 8; Rule 9; Section 15"
    }
}


def main():
    if not INPUT.exists():
        raise FileNotFoundError(INPUT)

    with INPUT.open("r", encoding="utf-8-sig", newline="") as f:
        evidence = list(csv.DictReader(f))

    evidence_by_id = {r["problem_id"]: r for r in evidence}

    if len(evidence) != 22 or len(evidence_by_id) != 22:
        raise ValueError("Evidence must contain exactly 22 unique records.")

    if set(evidence_by_id) != set(DECISIONS):
        missing = set(evidence_by_id) - set(DECISIONS)
        extra = set(DECISIONS) - set(evidence_by_id)
        raise ValueError(f"Decision ID mismatch. Missing={missing}; Extra={extra}")

    final_rows = []
    for problem_id, decision in DECISIONS.items():
        source = evidence_by_id[problem_id]
        row = dict(source)
        row["final_capabilities"] = json.dumps(
            decision["capabilities"], ensure_ascii=False
        )
        row["final_difficulty"] = decision["difficulty"]
        row["final_rationale"] = decision["rationale"]
        row["guideline_reference_final"] = decision["guideline"]
        row["adjudication_status"] = "AI_ADJUDICATED_PENDING_HUMAN_CONFIRMATION"
        row["reviewer"] = "ChatGPT_AI"
        final_rows.append(row)

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(final_rows[0].keys()))
        writer.writeheader()
        writer.writerows(final_rows)

    OUTPUT_JSON.write_text(
        json.dumps(DECISIONS, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("D3 AI ADJUDICATION: PASS")
    print("Records:", len(final_rows))
    print("Unique IDs:", len(DECISIONS))
    print("Human confirmation status: pending")
    print("CSV:", OUTPUT_CSV)
    print("JSON:", OUTPUT_JSON)


if __name__ == "__main__":
    main()
