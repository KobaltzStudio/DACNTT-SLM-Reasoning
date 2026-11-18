import csv
import json
from pathlib import Path

ROOT = Path(".")
INPUT_PATH = ROOT / "reports/capability/d3_audit/adjudication_evidence.csv"
OUTPUT_PATH = ROOT / "reports/capability/d3_audit/adjudication_proposals.csv"

# These are preliminary model proposals, not approved Gold labels.
PROPOSALS = {
    "gsm8k_train_00325": {
        "capabilities": ["fraction", "subtraction"],
        "difficulty": "medium",
        "rationale": (
            "Preliminary proposal: fractional reasoning and determining "
            "the remaining quantity appear central. Do not retain division "
            "merely because a fraction can be calculated by division. "
            "Verify the referent of each quantity in the original question."
        ),
        "guideline": "Guideline v3 Rule 2; Rule 3; Rule 8; Rule 9"
    },
    "gsm8k_train_00761": {
        "capabilities": ["fraction", "division"],
        "difficulty": "medium",
        "rationale": (
            "Preliminary proposal: infer the whole from a known fractional "
            "part, then calculate another fractional quantity. Division "
            "is proposed because finding the whole from a part is an "
            "explicit inverse-division case in Rule 2."
        ),
        "guideline": "Guideline v3 Rule 2; Rule 3; Rule 8"
    },
    "gsm8k_train_00769": {
        "capabilities": ["multiplication", "percentage", "subtraction"],
        "difficulty": "medium",
        "rationale": (
            "Preliminary proposal: calculate the relevant percentage "
            "quantities and compare them. Verify whether the requested "
            "difference is an absolute percentage-point difference or "
            "a relative percentage change."
        ),
        "guideline": "Guideline v3 Rule 2; Rule 8; Rule 9"
    },
    "gsm8k_train_01013": {
        "capabilities": ["addition", "fraction"],
        "difficulty": "medium",
        "rationale": (
            "Preliminary proposal: calculate fractional quantities and "
            "combine them. Do not add multiplication solely because "
            "fraction-of-a-quantity can be represented as a product."
        ),
        "guideline": "Guideline v3 Rule 3; Rule 8"
    },
    "gsm8k_train_01280": {
        "capabilities": ["addition", "fraction", "subtraction"],
        "difficulty": "medium",
        "rationale": (
            "Preliminary proposal: derive fractional groups, combine "
            "the relevant groups, and determine the remaining quantity. "
            "Verify which groups are explicitly required by the question."
        ),
        "guideline": "Guideline v3 Rule 3; Rule 8"
    },
    "gsm8k_train_01334": {
        "capabilities": ["division", "multiplication", "ratio", "subtraction"],
        "difficulty": "medium",
        "rationale": (
            "Preliminary proposal: allocate a total according to a ratio "
            "and calculate the difference between the allocated parts. "
            "Check whether multiplication is independently required "
            "under the problem-level capability definition."
        ),
        "guideline": "Guideline v3 Rule 2; Rule 6; Rule 8; Section 15"
    },
    "gsm8k_train_01600": {
        "capabilities": ["division", "multiplication", "ratio"],
        "difficulty": "medium",
        "rationale": (
            "Preliminary proposal: distribute a total according to a "
            "ratio and calculate the requested allocation. Verify the "
            "requested quantity and whether multiplication is an "
            "independent required capability."
        ),
        "guideline": "Guideline v3 Rule 2; Rule 6; Rule 8; Section 15"
    },
    "gsm8k_train_02342": {
        "capabilities": ["division", "multiplication", "percentage", "subtraction"],
        "difficulty": "hard",
        "rationale": (
            "Preliminary proposal: derive subgroup counts, determine "
            "the relevant percentage, and combine complementary "
            "quantities. Verify every intermediate quantity against "
            "the original question."
        ),
        "guideline": "Guideline v3 Rule 2; Rule 8; Rule 9"
    },
    "gsm8k_train_02754": {
        "capabilities": ["addition", "fraction", "subtraction"],
        "difficulty": "medium",
        "rationale": (
            "Preliminary proposal: combine initial quantities, calculate "
            "fractional consumption, and determine what remains. "
            "Do not infer multiplication from fraction notation alone."
        ),
        "guideline": "Guideline v3 Rule 3; Rule 8"
    },
    "gsm8k_train_02858": {
        "capabilities": ["division", "multiplication", "percentage", "subtraction"],
        "difficulty": "medium",
        "rationale": (
            "Preliminary proposal: derive a subgroup count, calculate "
            "another group, and determine a percentage. Verify whether "
            "the complement operation is required by the question."
        ),
        "guideline": "Guideline v3 Rule 2; Rule 8"
    },
    "gsm8k_train_02919": {
        "capabilities": ["addition", "fraction", "subtraction"],
        "difficulty": "medium",
        "rationale": (
            "Preliminary proposal: combine group counts, calculate "
            "fractional departures, and determine the remaining count. "
            "Check whether division is separately required rather than "
            "being merely an alternative way to calculate a fraction."
        ),
        "guideline": "Guideline v3 Rule 2; Rule 3; Rule 8"
    },
    "gsm8k_train_02997": {
        "capabilities": ["fraction", "subtraction"],
        "difficulty": "easy",
        "rationale": (
            "Preliminary proposal: determine fractional portions and "
            "the remaining portion. Fraction-of-a-whole does not imply "
            "division as a separate capability."
        ),
        "guideline": "Guideline v3 Rule 2; Rule 3; Rule 8"
    },
    "gsm8k_train_03016": {
        "capabilities": ["division", "multiplication", "percentage"],
        "difficulty": "medium",
        "rationale": (
            "Preliminary proposal: calculate a percentage-based student "
            "count, calculate the associated cost, and compare it with "
            "the budget. Verify whether division is a required operation "
            "or whether the percentage calculation alone is sufficient."
        ),
        "guideline": "Guideline v3 Rule 2; Rule 8; Section 15"
    },
    "gsm8k_train_03125": {
        "capabilities": ["addition", "percentage"],
        "difficulty": "medium",
        "rationale": (
            "Preliminary proposal: calculate percentage-based charges "
            "and combine the resulting amounts. Do not infer multiplication "
            "solely from the arithmetic implementation of a percentage."
        ),
        "guideline": "Guideline v3 Rule 8; Section 15"
    },
    "gsm8k_train_03140": {
        "capabilities": ["addition", "division", "percentage"],
        "difficulty": "medium",
        "rationale": (
            "Preliminary proposal: reverse a fixed deduction and then "
            "reverse a percentage-based change. Verify that the inverse "
            "percentage step satisfies the explicit division definition."
        ),
        "guideline": "Guideline v3 Rule 2; Rule 8"
    },
    "gsm8k_train_03263": {
        "capabilities": ["addition", "division", "fraction"],
        "difficulty": "medium",
        "rationale": (
            "Preliminary proposal: use part-whole relationships and "
            "fractional proportions to infer the requested quantity. "
            "Check whether division is independently required under "
            "Rule 2 rather than merely used to evaluate a fraction."
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
            "Preliminary proposal: allocate a total by ratio, calculate "
            "fractional sales, multiply quantities by prices, and sum "
            "revenue. Verify that every listed capability is required "
            "by the problem, not merely by one possible trajectory."
        ),
        "guideline": "Guideline v3 Rule 2; Rule 3; Rule 6; Rule 8; Section 15"
    },
    "gsm8k_train_04426": {
        "capabilities": ["division", "multiplication", "ratio", "subtraction"],
        "difficulty": "medium",
        "rationale": (
            "Preliminary proposal: allocate a total according to a ratio "
            "and calculate the difference between groups. Verify whether "
            "multiplication is independently required."
        ),
        "guideline": "Guideline v3 Rule 2; Rule 6; Rule 8; Section 15"
    },
    "gsm8k_train_04617": {
        "capabilities": ["addition", "division", "multiplication", "ratio"],
        "difficulty": "medium",
        "rationale": (
            "Preliminary proposal: use the difference between ratio parts "
            "to infer one unit, then calculate the total. Do not add "
            "subtraction automatically if the problem's required "
            "reasoning does not require a separate subtraction capability."
        ),
        "guideline": "Guideline v3 Rule 2; Rule 6; Rule 8; Section 15"
    },
    "gsm8k_train_04862": {
        "capabilities": ["addition", "percentage", "subtraction"],
        "difficulty": "medium",
        "rationale": (
            "Preliminary proposal: calculate remaining percentages and "
            "combine the relevant amounts. Verify whether the problem "
            "requires an additional multiplication capability."
        ),
        "guideline": "Guideline v3 Rule 8; Section 15"
    },
    "gsm8k_train_05194": {
        "capabilities": ["addition", "percentage", "subtraction"],
        "difficulty": "medium",
        "rationale": (
            "Preliminary proposal: calculate a percentage-based charge, "
            "add it to the base amount, and subtract from the payment. "
            "Do not infer multiplication solely from percentage notation."
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
            "Preliminary proposal: combine meal costs, calculate the "
            "specified wine quantity, apply the fractional discount, "
            "and calculate the tip. Verify whether the tip base is "
            "pre-discount or post-discount from the exact wording."
        ),
        "guideline": "Guideline v3 Rule 3; Rule 8; Rule 9; Section 15"
    },
}


def parse_labels(value):
    if not value:
        return []
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return parsed
    except (json.JSONDecodeError, TypeError):
        pass
    return []


def main():
    if not INPUT_PATH.exists():
        raise FileNotFoundError(INPUT_PATH)

    with INPUT_PATH.open(
        "r", encoding="utf-8-sig", newline=""
    ) as f:
        rows = list(csv.DictReader(f))

    if len(rows) != 22:
        raise ValueError(f"Expected 22 evidence rows, got {len(rows)}")

    seen = set()
    output_rows = []

    for row in rows:
        problem_id = row["problem_id"]

        if problem_id in seen:
            raise ValueError(f"Duplicate problem_id: {problem_id}")
        seen.add(problem_id)

        proposal = PROPOSALS.get(problem_id)
        if proposal is None:
            raise ValueError(f"No proposal defined for {problem_id}")

        output = dict(row)

        output["A1_original_labels"] = row.get("A1_original_labels", "")
        output["A1_reviewed_labels"] = row.get("A1_reviewed_labels", "")
        output["A2_labels"] = row.get("A2_labels", "")

        output["proposed_capabilities"] = json.dumps(
            proposal["capabilities"], ensure_ascii=False
        )
        output["proposed_difficulty"] = proposal["difficulty"]
        output["proposed_rationale"] = proposal["rationale"]
        output["guideline_reference"] = proposal["guideline"]

        output["proposed_solution_outline"] = ""
        output["adjudication_status"] = "PROPOSED_PENDING_REVIEW"
        output["final_capabilities"] = ""
        output["final_difficulty"] = ""
        output["final_rationale"] = ""
        output["reviewer"] = ""

        output_rows.append(output)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    columns = list(output_rows[0].keys())

    with OUTPUT_PATH.open(
        "w", encoding="utf-8-sig", newline=""
    ) as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(output_rows)

    print("D3 ADJUDICATION PROPOSALS: PASS")
    print("Records:", len(output_rows))
    print("Unique IDs:", len(seen))
    print("Pending review:", len(output_rows))
    print("Output:", OUTPUT_PATH)


if __name__ == "__main__":
    main()
