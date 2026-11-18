from pathlib import Path
import json
import re
import sys


# ============================================================
# Configuration
# ============================================================

BASE = Path(__file__).resolve().parents[1]

OUTPUT_DIR = BASE / "data" / "raw"
OUTPUT_FILE = OUTPUT_DIR / "gsm8k_train.jsonl"

PILOT_FILE = BASE / "data" / "pilot" / "pilot_30.jsonl"
BATCH_FILE = BASE / "data" / "batch_100" / "batch_100.jsonl"

DATASET_NAME = "openai/gsm8k"
DATASET_CONFIG = "main"
DATASET_SPLIT = "train"

EXPECTED_COUNT = 7473


# ============================================================
# Helpers
# ============================================================

def normalize_text(text):
    if text is None:
        return ""

    return " ".join(str(text).strip().split())


def extract_gsm8k_answer(answer):
    """
    GSM8K HF answers normally end with:

        #### <final_answer>

    Only the final answer is stored as ground_truth.
    """
    answer = str(answer).strip()

    match = re.search(r"####\s*(.+?)\s*$", answer)

    if match:
        return match.group(1).strip()

    return answer


def problem_id_number(problem_id):
    """
    Convert:
        gsm8k_train_00042
    -> 42
    """
    prefix = "gsm8k_train_"

    if not str(problem_id).startswith(prefix):
        raise ValueError(
            f"Invalid problem_id format: {problem_id}"
        )

    return int(str(problem_id)[len(prefix):])


def make_problem_id(index):
    return f"gsm8k_train_{index:05d}"


def load_jsonl(path):
    records = []

    if not path.exists():
        return records

    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"Invalid JSON at {path}, line {line_no}: {e}"
                )

    return records


def get_question(record):
    return normalize_text(
        record.get(
            "question",
            record.get("problem", record.get("problem_text", ""))
        )
    )


def get_problem_id(record):
    return record.get(
        "problem_id",
        record.get("id")
    )


# ============================================================
# Load existing project records
# ============================================================

def load_existing_project_records():
    """
    Load existing project datasets whose problem_id mappings
    must remain unchanged.

    These files are treated as canonical for already-existing
    problems. Their problem_id values are NEVER regenerated.
    """

    sources = [
        PILOT_FILE,
        BATCH_FILE,
    ]

    all_records = []

    print()
    print("=" * 70)
    print("Loading existing project records")
    print("=" * 70)

    for path in sources:

        if not path.exists():
            print()
            print(f"[WARN] File not found:")
            print(f"       {path}")
            continue

        records = load_jsonl(path)

        print()
        print(f"[PASS] {path}")
        print(f"       Records: {len(records)}")

        all_records.extend(records)

    if not all_records:
        raise RuntimeError(
            "No existing project records were found. "
            "Cannot safely preserve project problem_id mappings."
        )

    return all_records


# ============================================================
# Build canonical project mapping
# ============================================================

def build_project_mapping(existing_records):
    """
    Build:

        question -> problem_id
        problem_id -> question

    Existing project IDs are treated as canonical.

    If the same question is associated with two different IDs,
    or the same ID is associated with two different questions,
    the script stops instead of silently changing mappings.
    """

    question_to_id = {}
    id_to_question = {}
    id_to_ground_truth = {}

    print()
    print("=" * 70)
    print("Building canonical project mapping")
    print("=" * 70)

    for record in existing_records:

        problem_id = get_problem_id(record)
        question = get_question(record)

        if not problem_id:
            raise ValueError(
                "Existing record is missing problem_id/id."
            )

        if not question:
            raise ValueError(
                f"Existing record {problem_id} has an empty question."
            )

        if problem_id in id_to_question:
            old_question = id_to_question[problem_id]

            if old_question != question:
                raise ValueError(
                    "Project ID conflict detected:\n"
                    f"  problem_id: {problem_id}\n"
                    f"  old question: {old_question[:150]}\n"
                    f"  new question: {question[:150]}"
                )

        else:
            id_to_question[problem_id] = question

        if question in question_to_id:
            old_id = question_to_id[question]

            if old_id != problem_id:
                raise ValueError(
                    "Question is associated with multiple project IDs:\n"
                    f"  question: {question[:150]}\n"
                    f"  ID 1: {old_id}\n"
                    f"  ID 2: {problem_id}"
                )

        else:
            question_to_id[question] = problem_id

        ground_truth = record.get("ground_truth")

        if ground_truth is not None:
            ground_truth = normalize_text(ground_truth)

            if problem_id in id_to_ground_truth:
                old_answer = id_to_ground_truth[problem_id]

                if old_answer != ground_truth:
                    raise ValueError(
                        "Ground-truth conflict detected:\n"
                        f"  problem_id: {problem_id}\n"
                        f"  old: {old_answer}\n"
                        f"  new: {ground_truth}"
                    )

            else:
                id_to_ground_truth[problem_id] = ground_truth

    print(
        f"[PASS] Unique existing project problems: "
        f"{len(question_to_id)}"
    )

    print(
        f"[PASS] Reserved project IDs: "
        f"{len(id_to_question)}"
    )

    return (
        question_to_id,
        id_to_question,
        id_to_ground_truth,
    )


# ============================================================
# Build HF question index
# ============================================================

def build_hf_question_index(dataset):
    """
    Build:

        normalized_question -> HF source indices

    This is used only internally while generating gsm8k_train.jsonl.

    No mapping file is written.
    """

    question_to_indices = {}

    for hf_index, record in enumerate(dataset):

        question = normalize_text(record["question"])

        question_to_indices.setdefault(
            question,
            []
        ).append(hf_index)

    duplicate_questions = {
        question: indices
        for question, indices in question_to_indices.items()
        if len(indices) > 1
    }

    if duplicate_questions:
        raise ValueError(
            "Duplicate questions detected in HF GSM8K dataset. "
            "Cannot guarantee deterministic source_index mapping."
        )

    print(
        f"[PASS] Unique HF questions: "
        f"{len(question_to_indices)}"
    )

    return question_to_indices


# ============================================================
# Match existing project records to HF
# ============================================================

def validate_existing_records_against_hf(
    question_to_indices,
    question_to_id,
):
    """
    Ensure every existing project problem can be located exactly
    once in the current HF GSM8K train split.

    This is critical because project problem_id values are retained,
    while source_index comes from the current HF dataset.
    """

    print()
    print("=" * 70)
    print("Matching existing project records to HF GSM8K")
    print("=" * 70)

    missing = []
    multiple = []

    matches = {}

    for question, problem_id in question_to_id.items():

        indices = question_to_indices.get(question, [])

        if len(indices) == 0:
            missing.append(
                {
                    "problem_id": problem_id,
                    "question": question,
                }
            )
            continue

        if len(indices) != 1:
            multiple.append(
                {
                    "problem_id": problem_id,
                    "indices": indices,
                    "question": question,
                }
            )
            continue

        matches[problem_id] = indices[0]

    if missing:
        print(
            f"[FAIL] {len(missing)} existing project "
            "problem(s) were not found in HF."
        )

        for item in missing[:10]:
            print()
            print(f"problem_id: {item['problem_id']}")
            print(f"question:   {item['question'][:150]}")

        raise RuntimeError(
            "Existing project records do not fully match "
            "the current HF GSM8K train split."
        )

    if multiple:
        raise RuntimeError(
            "At least one existing project problem matched "
            "multiple HF records."
        )

    print(
        f"[PASS] Matched {len(matches)} existing project "
        "problems to unique HF source_index values."
    )

    return matches


# ============================================================
# Build complete normalized dataset
# ============================================================

def build_normalized_dataset(
    dataset,
    question_to_id,
    id_to_question,
    id_to_ground_truth,
):
    """
    Create the final canonical project dataset.

    Rules:

    1. Existing project problem_id values are preserved.
    2. source_index is ALWAYS the actual HF index.
    3. Existing questions keep their project question text.
    4. Existing ground_truth values are preserved.
    5. New problems receive unused project IDs deterministically.
    6. No existing problem_id is changed.
    """

    question_to_indices = build_hf_question_index(dataset)

    existing_matches = validate_existing_records_against_hf(
        question_to_indices,
        question_to_id,
    )

    reserved_ids = set(id_to_question.keys())

    output_records = []

    used_problem_ids = set()

    next_problem_number = 0

    existing_count = 0
    new_count = 0

    for hf_index, record in enumerate(dataset):

        hf_question = normalize_text(record["question"])

        # ----------------------------------------------------
        # Existing project problem
        # ----------------------------------------------------

        if hf_question in question_to_id:

            problem_id = question_to_id[hf_question]

            project_question = id_to_question[problem_id]

            if problem_id in id_to_ground_truth:
                ground_truth = id_to_ground_truth[problem_id]
            else:
                ground_truth = extract_gsm8k_answer(
                    record["answer"]
                )

            existing_count += 1

        # ----------------------------------------------------
        # New problem
        # ----------------------------------------------------

        else:

            while True:

                candidate_id = make_problem_id(
                    next_problem_number
                )

                next_problem_number += 1

                if candidate_id not in reserved_ids:
                    break

            problem_id = candidate_id

            project_question = hf_question

            ground_truth = extract_gsm8k_answer(
                record["answer"]
            )

            new_count += 1

        # ----------------------------------------------------
        # Safety checks
        # ----------------------------------------------------

        if problem_id in used_problem_ids:

            raise RuntimeError(
                f"Duplicate problem_id generated: {problem_id}"
            )

        used_problem_ids.add(problem_id)

        if not ground_truth:

            raise ValueError(
                f"Empty ground_truth for {problem_id}"
            )

        output_records.append(
            {
                "problem_id": problem_id,
                "source_index": hf_index,
                "question": project_question,
                "ground_truth": ground_truth,
            }
        )

    print()
    print("=" * 70)
    print("Canonical mapping summary")
    print("=" * 70)

    print(
        f"Existing project problems preserved: "
        f"{existing_count}"
    )

    print(
        f"New problems assigned IDs: "
        f"{new_count}"
    )

    print(
        f"Total records: "
        f"{len(output_records)}"
    )

    return output_records


# ============================================================
# Validate final dataset
# ============================================================

def validate_final_dataset(
    records,
    existing_records,
):
    print()
    print("=" * 70)
    print("Validating final gsm8k_train.jsonl")
    print("=" * 70)

    if len(records) != EXPECTED_COUNT:

        raise ValueError(
            f"Expected {EXPECTED_COUNT} records, "
            f"but generated {len(records)}."
        )

    print(
        f"[PASS] Record count: {len(records)}"
    )

    # --------------------------------------------------------
    # Required fields
    # --------------------------------------------------------

    required_fields = {
        "problem_id",
        "source_index",
        "question",
        "ground_truth",
    }

    for index, record in enumerate(records):

        missing = (
            required_fields
            - set(record.keys())
        )

        if missing:
            raise ValueError(
                f"Record {index} is missing fields: "
                f"{missing}"
            )

        if not record["question"]:
            raise ValueError(
                f"Record {index} has empty question."
            )

        if not record["ground_truth"]:
            raise ValueError(
                f"Record {index} has empty ground_truth."
            )

    print("[PASS] Required fields are present.")

    # --------------------------------------------------------
    # Unique problem IDs
    # --------------------------------------------------------

    problem_ids = [
        record["problem_id"]
        for record in records
    ]

    if len(problem_ids) != len(set(problem_ids)):

        raise ValueError(
            "Duplicate problem_id detected."
        )

    print("[PASS] problem_id values are unique.")

    # --------------------------------------------------------
    # Unique HF source indices
    # --------------------------------------------------------

    source_indices = [
        record["source_index"]
        for record in records
    ]

    if len(source_indices) != len(set(source_indices)):

        raise ValueError(
            "Duplicate source_index detected."
        )

    print("[PASS] source_index values are unique.")

    # --------------------------------------------------------
    # Source index range
    # --------------------------------------------------------

    for source_index in source_indices:

        if not (
            0 <= source_index < EXPECTED_COUNT
        ):
            raise ValueError(
                f"Invalid source_index: {source_index}"
            )

    print(
        "[PASS] source_index values are within "
        "the HF dataset range."
    )

    # --------------------------------------------------------
    # Existing project mapping verification
    # --------------------------------------------------------

    final_by_id = {
        record["problem_id"]: record
        for record in records
    }

    checked = 0

    for existing in existing_records:

        problem_id = get_problem_id(existing)

        if problem_id not in final_by_id:

            raise ValueError(
                f"Existing problem_id disappeared: "
                f"{problem_id}"
            )

        final_record = final_by_id[problem_id]

        existing_question = get_question(existing)

        final_question = normalize_text(
            final_record["question"]
        )

        if existing_question != final_question:

            raise ValueError(
                "Existing question changed:\n"
                f"problem_id: {problem_id}\n"
                f"existing:   {existing_question[:150]}\n"
                f"generated:  {final_question[:150]}"
            )

        if "ground_truth" in existing:

            existing_answer = normalize_text(
                existing["ground_truth"]
            )

            final_answer = normalize_text(
                final_record["ground_truth"]
            )

            if existing_answer != final_answer:

                raise ValueError(
                    "Existing ground_truth changed:\n"
                    f"problem_id: {problem_id}\n"
                    f"existing:   {existing_answer}\n"
                    f"generated:  {final_answer}"
                )

        checked += 1

    print(
        f"[PASS] Existing project records preserved: "
        f"{checked}"
    )

    # --------------------------------------------------------
    # source_index type
    # --------------------------------------------------------

    if not all(
        isinstance(record["source_index"], int)
        for record in records
    ):
        raise ValueError(
            "source_index must be integer."
        )

    print("[PASS] source_index type is valid.")


# ============================================================
# Export
# ============================================================

def export_dataset(records):

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    if OUTPUT_FILE.exists():

        print()
        print(
            f"[WARN] Output file already exists:"
        )
        print(
            f"       {OUTPUT_FILE}"
        )

        response = input(
            "Overwrite it? [y/N]: "
        ).strip().lower()

        if response != "y":

            print(
                "[STOP] Export cancelled."
            )

            sys.exit(0)

    # --------------------------------------------------------
    # Sort by canonical project problem_id.
    #
    # This makes:
    #
    # gsm8k_train_00000
    # gsm8k_train_00001
    # ...
    #
    # appear in project order, while source_index retains
    # the true HF location.
    # --------------------------------------------------------

    records = sorted(
        records,
        key=lambda record: problem_id_number(
            record["problem_id"]
        )
    )

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8"
    ) as f:

        for record in records:

            f.write(
                json.dumps(
                    record,
                    ensure_ascii=False
                )
                + "\n"
            )

    print()
    print("=" * 70)
    print("Export completed")
    print("=" * 70)

    print(
        f"Output:"
    )
    print(
        f"  {OUTPUT_FILE}"
    )

    print(
        f"Records:"
    )
    print(
        f"  {len(records)}"
    )


# ============================================================
# Preview
# ============================================================

def preview_dataset():

    print()
    print("=" * 70)
    print("FINAL PREVIEW")
    print("=" * 70)

    records = load_jsonl(
        OUTPUT_FILE
    )

    preview_count = min(
        5,
        len(records)
    )

    for index in range(preview_count):

        record = records[index]

        print()
        print(
            f"problem_id:   "
            f"{record['problem_id']}"
        )

        print(
            f"source_index: "
            f"{record['source_index']}"
        )

        print(
            f"question:     "
            f"{record['question'][:150]}"
        )

        print(
            f"ground_truth: "
            f"{record['ground_truth']}"
        )


# ============================================================
# Main
# ============================================================

def main():

    print("=" * 70)
    print("GSM8K TRAIN DOWNLOADER")
    print("=" * 70)

    print()
    print(
        f"Dataset : {DATASET_NAME}"
    )

    print(
        f"Config  : {DATASET_CONFIG}"
    )

    print(
        f"Split   : {DATASET_SPLIT}"
    )

    print(
        f"Output  : {OUTPUT_FILE}"
    )

    print()
    print(
        "Important:"
    )

    print(
        "  Existing project problem_id values will be preserved."
    )

    print(
        "  source_index will store the true Hugging Face index."
    )

    print(
        "  No mapping/index file will be created."
    )

    # --------------------------------------------------------
    # Import Hugging Face datasets
    # --------------------------------------------------------

    try:

        from datasets import load_dataset

    except ImportError:

        print()
        print(
            "[ERROR] Python package 'datasets' "
            "is not installed."
        )

        print()
        print(
            "Install it with:"
        )

        print()
        print(
            "    pip install datasets"
        )

        sys.exit(1)

    # --------------------------------------------------------
    # Load HF dataset
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("Loading GSM8K from Hugging Face")
    print("=" * 70)

    try:

        dataset = load_dataset(
            DATASET_NAME,
            DATASET_CONFIG,
            split=DATASET_SPLIT,
        )

    except Exception as e:

        print()
        print(
            "[ERROR] Failed to load GSM8K."
        )

        print()
        print(str(e))

        print()
        print(
            "Make sure you have internet access and "
            "the 'datasets' package is installed."
        )

        sys.exit(1)

    print()
    print(
        "[PASS] Dataset loaded successfully."
    )

    print(
        f"Records: {len(dataset)}"
    )

    # --------------------------------------------------------
    # Basic source validation
    # --------------------------------------------------------

    if len(dataset) != EXPECTED_COUNT:

        print()
        print(
            f"[FAIL] Expected {EXPECTED_COUNT} records, "
            f"but HF returned {len(dataset)}."
        )

        print()
        print(
            "STOP: Do not generate gsm8k_train.jsonl "
            "from an unexpected dataset version."
        )

        sys.exit(1)

    print(
        f"[PASS] HF record count is exactly "
        f"{EXPECTED_COUNT}."
    )

    # --------------------------------------------------------
    # Convert HF dataset to Python records
    # --------------------------------------------------------

    records = []

    for index, record in enumerate(dataset):

        if "question" not in record:
            raise ValueError(
                f"HF record {index} is missing 'question'."
            )

        if "answer" not in record:
            raise ValueError(
                f"HF record {index} is missing 'answer'."
            )

        question = normalize_text(
            record["question"]
        )

        answer = normalize_text(
            record["answer"]
        )

        if not question:
            raise ValueError(
                f"HF record {index} has empty question."
            )

        if not answer:
            raise ValueError(
                f"HF record {index} has empty answer."
            )

        records.append(
            {
                "question": question,
                "answer": answer,
            }
        )

    print(
        "[PASS] HF source fields validated."
    )

    # --------------------------------------------------------
    # Load existing project data
    # --------------------------------------------------------

    existing_records = (
        load_existing_project_records()
    )

    (
        question_to_id,
        id_to_question,
        id_to_ground_truth,
    ) = build_project_mapping(
        existing_records
    )

    # --------------------------------------------------------
    # Build final dataset
    # --------------------------------------------------------

    final_records = build_normalized_dataset(
        records,
        question_to_id,
        id_to_question,
        id_to_ground_truth,
    )

    # --------------------------------------------------------
    # Validate final dataset
    # --------------------------------------------------------

    validate_final_dataset(
        final_records,
        existing_records,
    )

    # --------------------------------------------------------
    # Export
    # --------------------------------------------------------

    export_dataset(
        final_records
    )

    # --------------------------------------------------------
    # Preview
    # --------------------------------------------------------

    preview_dataset()

    # --------------------------------------------------------
    # Success
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("SUCCESS")
    print("=" * 70)

    print()
    print(
        "gsm8k_train.jsonl is ready."
    )

    print()
    print(
        f"Source file:"
    )

    print(
        f"  {OUTPUT_FILE}"
    )

    print()
    print(
        "Mapping policy:"
    )

    print(
        "  - Existing problem_id values: PRESERVED"
    )

    print(
        "  - HF source_index: TRUE HF INDEX"
    )

    print(
        "  - New problem_id values: DETERMINISTIC"
    )

    print(
        "  - Additional mapping file: NONE"
    )

    print()
    print(
        "Next step:"
    )

    print(
        "  Run create_supplement_candidates.py "
        "against this gsm8k_train.jsonl."
    )


if __name__ == "__main__":
    main()