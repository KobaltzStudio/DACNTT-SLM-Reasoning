import json
from collections import Counter, defaultdict
from pathlib import Path


BASE = Path("experiments/week2September")

BASELINE_FILE = (
    BASE / "processed" / "baseline_with_difficulty_100.jsonl"
)

TRAJECTORY_FILE = (
    BASE / "processed"
    / "teacher_trajectories_reevaluated_50x5.jsonl"
)

CANDIDATE_FILE = (
    BASE / "processed"
    / "teacher_correct_student_wrong_with_metadata.jsonl"
)

SKILL_GAP_FILE = (
    BASE / "processed"
    / "student_skill_gap.json"
)


def load_jsonl(path):
    if not path.exists():
        raise FileNotFoundError(path)

    with path.open("r", encoding="utf-8") as f:
        return [
            json.loads(line)
            for line in f
            if line.strip()
        ]


def check_unique_keys(records, key_fields):
    keys = [
        tuple(record.get(field) for field in key_fields)
        for record in records
    ]

    duplicates = [
        key
        for key, count in Counter(keys).items()
        if count > 1
    ]

    return duplicates


def main():

    print("=" * 70)
    print("WEEK 2 DATA VALIDATION")
    print("=" * 70)

    baseline = load_jsonl(BASELINE_FILE)
    trajectories = load_jsonl(TRAJECTORY_FILE)
    candidates = load_jsonl(CANDIDATE_FILE)

    print()
    print("FILES")
    print("-" * 70)
    print(f"Baseline      : {len(baseline)}")
    print(f"Trajectories  : {len(trajectories)}")
    print(f"Candidates    : {len(candidates)}")

    # ---------------------------------------------------------
    # BASELINE
    # ---------------------------------------------------------

    print()
    print("BASELINE")
    print("-" * 70)

    baseline_ids = {
        x.get("id")
        for x in baseline
    }

    print(
        "Teacher correct:",
        sum(x.get("teacher_correct") is True for x in baseline)
    )

    print(
        "Student correct:",
        sum(x.get("student_correct") is True for x in baseline)
    )

    eligible_ids = {
        x.get("id")
        for x in baseline
        if x.get("teacher_correct") is True
        and x.get("student_correct") is False
    }

    print(
        "Teacher-correct / Student-wrong:",
        len(eligible_ids)
    )

    # ---------------------------------------------------------
    # TRAJECTORIES
    # ---------------------------------------------------------

    print()
    print("TRAJECTORIES")
    print("-" * 70)

    trajectory_duplicates = check_unique_keys(
        trajectories,
        ["question_id", "trajectory_id"],
    )

    print(
        "Duplicate (question_id, trajectory_id):",
        len(trajectory_duplicates)
    )

    question_counts = Counter(
        x.get("question_id")
        for x in trajectories
    )

    print(
        "Unique questions:",
        len(question_counts)
    )

    print(
        "Trajectory distribution:",
        Counter(question_counts.values())
    )

    print(
        "Correct:",
        sum(x.get("correct") is True for x in trajectories)
    )

    print(
        "Incorrect:",
        sum(x.get("correct") is False for x in trajectories)
    )

    print(
        "Null answer:",
        sum(
            x.get("predicted_answer") is None
            for x in trajectories
        )
    )

    # ---------------------------------------------------------
    # CANDIDATES
    # ---------------------------------------------------------

    print()
    print("CANDIDATE POOL")
    print("-" * 70)

    candidate_duplicates = check_unique_keys(
        candidates,
        ["question_id", "trajectory_id"],
    )

    print(
        "Duplicate candidate keys:",
        len(candidate_duplicates)
    )

    candidate_question_ids = {
        x.get("question_id")
        for x in candidates
    }

    print(
        "Unique candidate questions:",
        len(candidate_question_ids)
    )

    invalid_candidates = [
        x
        for x in candidates
        if x.get("question_id") not in eligible_ids
    ]

    print(
        "Candidates outside eligible baseline:",
        len(invalid_candidates)
    )

    print(
        "Candidate correct trajectories:",
        sum(
            x.get("trajectory_correct") is True
            for x in candidates
        )
    )

    print(
        "Candidate incorrect trajectories:",
        sum(
            x.get("trajectory_correct") is False
            for x in candidates
        )
    )

    print(
        "Candidate null answers:",
        sum(
            x.get("predicted_answer") is None
            for x in candidates
        )
    )

    # ---------------------------------------------------------
    # TRAJECTORY COUNT PER CANDIDATE QUESTION
    # ---------------------------------------------------------

    print()
    print("CANDIDATE TRAJECTORIES PER QUESTION")
    print("-" * 70)

    candidate_counts = Counter(
        x.get("question_id")
        for x in candidates
    )

    print(
        "Distribution:",
        Counter(candidate_counts.values())
    )

    for question_id, count in sorted(
        candidate_counts.items()
    ):
        print(
            f"{question_id}: {count}"
        )

    # ---------------------------------------------------------
    # DIFFICULTY
    # ---------------------------------------------------------

    print()
    print("DIFFICULTY")
    print("-" * 70)

    print(
        "Candidate difficulty:",
        Counter(
            x.get("difficulty")
            for x in candidates
        )
    )

    print(
        "Candidate difficulty score:",
        Counter(
            x.get("difficulty_score")
            for x in candidates
        )
    )

    # ---------------------------------------------------------
    # SKILL GAP
    # ---------------------------------------------------------

    print()
    print("SKILL GAP")
    print("-" * 70)

    if SKILL_GAP_FILE.exists():

        with SKILL_GAP_FILE.open(
            "r",
            encoding="utf-8",
        ) as f:
            skill_gap = json.load(f)

        print(
            "Teacher-correct / Student-wrong:",
            skill_gap.get(
                "num_wrong_teacher_correct"
            )
        )

        profile = skill_gap.get(
            "skill_profile",
            {}
        )

        for skill, value in profile.items():
            print(
                f"{skill:15s}"
                f" score={value.get('score')}"
                f" gap={value.get('normalized_gap'):.3f}"
            )

    else:
        print(
            "student_skill_gap.json not found"
        )

    # ---------------------------------------------------------
    # CONSISTENCY
    # ---------------------------------------------------------

    print()
    print("CONSISTENCY CHECKS")
    print("-" * 70)

    candidate_ids_not_in_baseline = (
        candidate_question_ids - baseline_ids
    )

    print(
        "Candidate IDs missing from baseline:",
        len(candidate_ids_not_in_baseline)
    )

    trajectory_ids_not_in_baseline = (
        {
            x.get("question_id")
            for x in trajectories
        }
        - baseline_ids
    )

    print(
        "Trajectory question IDs missing from baseline:",
        len(trajectory_ids_not_in_baseline)
    )

    print()
    print("=" * 70)
    print("VALIDATION COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    main()