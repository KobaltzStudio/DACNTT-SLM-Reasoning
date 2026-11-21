import json
from pathlib import Path


SKILL_GAP_FILE = Path(
    "experiments/week2September/processed/student_skill_gap.json"
)

TRAJECTORY_FILE = Path(
    "experiments/week2September/processed/teacher_trajectories_with_skills_50x5.jsonl"
)

OUTPUT_FILE = Path(
    "experiments/week2September/processed/automatic_selected_traces.jsonl"
)

TOP_K = 2


def load_jsonl(path):

    with path.open(
        "r",
        encoding="utf-8",
    ) as f:

        return [
            json.loads(line)
            for line in f
            if line.strip()
        ]


def main():

    with SKILL_GAP_FILE.open(
        "r",
        encoding="utf-8",
    ) as f:

        skill_data = json.load(f)

    gap = {
        skill: value["normalized_gap"]
        for skill, value
        in skill_data["skill_profile"].items()
    }

    trajectories = load_jsonl(
        TRAJECTORY_FILE
    )

    candidates = [
        x
        for x in trajectories
        if x.get("correct") is True
    ]

    ranked = []

    for trajectory in candidates:

        skill_score = 0.0

        for skill in trajectory.get(
            "skill_set",
            []
        ):

            skill_score += gap.get(
                skill,
                0.0,
            )

        # Reasoning quality factors
        length = trajectory.get(
            "trajectory_length",
            0
        ) or 0

        steps = trajectory.get(
            "number_of_steps",
            0
        ) or 0

        quality_score = 0.0

        if steps > 0:
            quality_score += min(
                steps / 10.0,
                1.0
            )

        if length > 50:
            quality_score += 0.1

        final_score = (
            skill_score
            + 0.1 * quality_score
        )

        item = dict(trajectory)

        item["selection_score"] = round(
            final_score,
            6,
        )

        item["skill_match_score"] = round(
            skill_score,
            6,
        )

        ranked.append(item)

    ranked.sort(
        key=lambda x: (
            x["selection_score"],
            x.get("skill_match_score", 0),
        ),
        reverse=True,
    )

    selected = ranked[:TOP_K]

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
    ) as f:

        for rank, item in enumerate(
            selected,
            start=1,
        ):

            output = {
                "rank": rank,
                "question_id":
                    item["question_id"],
                "trajectory_id":
                    item["trajectory_id"],
                "selection_score":
                    item["selection_score"],
                "skill_match_score":
                    item["skill_match_score"],
                "skills":
                    item.get("skill_set", []),
                "difficulty":
                    item.get("difficulty"),
                "difficulty_score":
                    item.get("difficulty_score"),
                "trajectory_length":
                    item.get("trajectory_length"),
                "number_of_steps":
                    item.get("number_of_steps"),
                "trajectory":
                    item["trajectory"],
            }

            f.write(
                json.dumps(
                    output,
                    ensure_ascii=False,
                ) + "\n"
            )

    print("=" * 60)
    print("AUTOMATIC TRACE SELECTION")
    print("=" * 60)

    print(
        f"Candidate traces : {len(candidates)}"
    )

    print(
        f"Top-K            : {TOP_K}"
    )

    print()

    for item in selected:

        print(
            f"Rank {selected.index(item)+1}: "
            f"{item['question_id']} "
            f"T{item['trajectory_id']} "
            f"score={item['selection_score']}"
        )

    print()

    print(
        f"Output: {OUTPUT_FILE}"
    )

    print("=" * 60)


if __name__ == "__main__":
    main()