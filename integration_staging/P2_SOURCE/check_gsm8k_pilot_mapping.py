from pathlib import Path
import json
import sys

from datasets import load_dataset


BASE = Path(__file__).resolve().parents[1]

PILOT_FILE = BASE / "data" / "pilot" / "pilot_30.jsonl"
REPORT_FILE = BASE / "reports" / "gsm8k_pilot_mapping.json"

DATASET_NAME = "openai/gsm8k"
DATASET_CONFIG = "main"
DATASET_SPLIT = "train"


def normalize(text):
    if text is None:
        return ""

    return " ".join(str(text).strip().split())


def load_jsonl(path):
    records = []

    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):

            line = line.strip()

            if not line:
                continue

            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise RuntimeError(
                    f"Invalid JSON at {path}, line {line_no}: {e}"
                )

    return records


def main():

    print("=" * 70)
    print("GSM8K ↔ PILOT MAPPING CHECK")
    print("=" * 70)

    # --------------------------------------------------------
    # Load pilot
    # --------------------------------------------------------

    print()
    print("Pilot:")
    print(f"  {PILOT_FILE}")

    if not PILOT_FILE.exists():

        print()
        print("[ERROR] Pilot file does not exist.")

        sys.exit(1)

    pilot = load_jsonl(PILOT_FILE)

    print(f"Pilot records: {len(pilot)}")

    # --------------------------------------------------------
    # Load Hugging Face GSM8K
    # --------------------------------------------------------

    print()
    print("Loading Hugging Face GSM8K...")

    dataset = load_dataset(
        DATASET_NAME,
        DATASET_CONFIG,
        split=DATASET_SPLIT,
    )

    print(f"GSM8K records: {len(dataset)}")

    # --------------------------------------------------------
    # Build normalized question -> source indices
    # --------------------------------------------------------

    print()
    print("Building question index...")

    question_to_indices = {}

    for index, record in enumerate(dataset):

        question = normalize(record["question"])

        question_to_indices.setdefault(
            question,
            []
        ).append(index)

    # --------------------------------------------------------
    # Match pilot
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("MAPPING RESULTS")
    print("=" * 70)

    mappings = []

    found = 0
    missing = 0
    multiple = 0

    for pilot_index, pilot_record in enumerate(pilot):

        problem_id = pilot_record.get(
            "problem_id"
        )

        question = normalize(
            pilot_record.get("question")
        )

        matches = question_to_indices.get(
            question,
            []
        )

        if len(matches) == 0:

            status = "not_found"
            missing += 1

        elif len(matches) == 1:

            status = "found"
            found += 1

        else:

            status = "multiple_matches"
            multiple += 1

        mapping = {
            "pilot_index": pilot_index,
            "problem_id": problem_id,
            "source_indices": matches,
            "status": status,
        }

        mappings.append(mapping)

        print()
        print(
            f"[{pilot_index:02d}] {problem_id}"
        )
        print(
            f"  HF index: {matches}"
        )
        print(
            f"  Status: {status}"
        )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)

    print(
        f"Pilot records:    {len(pilot)}"
    )

    print(
        f"Found:            {found}"
    )

    print(
        f"Not found:        {missing}"
    )

    print(
        f"Multiple matches: {multiple}"
    )

    # --------------------------------------------------------
    # Save report
    # --------------------------------------------------------

    REPORT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    report = {
        "dataset": DATASET_NAME,
        "config": DATASET_CONFIG,
        "split": DATASET_SPLIT,
        "dataset_size": len(dataset),
        "pilot_size": len(pilot),
        "found": found,
        "missing": missing,
        "multiple_matches": multiple,
        "mappings": mappings,
    }

    with REPORT_FILE.open(
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            report,
            f,
            ensure_ascii=False,
            indent=2
        )

    print()
    print("Report:")
    print(f"  {REPORT_FILE}")

    # --------------------------------------------------------
    # Final decision
    # --------------------------------------------------------

    print()

    if missing == 0 and multiple == 0:

        print("=" * 70)
        print("PASS")
        print("=" * 70)

        print()
        print(
            "All pilot problems exist exactly once in the "
            "Hugging Face GSM8K train set."
        )

        print()
        print(
            "The difference is an ordering difference."
        )

    else:

        print("=" * 70)
        print("DO NOT CONTINUE YET")
        print("=" * 70)

        if missing > 0:

            print(
                f"{missing} pilot problems were not found."
            )

        if multiple > 0:

            print(
                f"{multiple} pilot problems have multiple matches."
            )


if __name__ == "__main__":
    main()