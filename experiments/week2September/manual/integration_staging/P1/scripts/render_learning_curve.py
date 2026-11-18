import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt


CAPABILITIES = [
    "addition",
    "subtraction",
    "multiplication",
    "division",
    "percentage",
    "fraction",
    "ratio",
]


def load_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def build_checkpoint_order(data):
    return [
        checkpoint["checkpoint_id"]
        for checkpoint in sorted(
            data["checkpoints"],
            key=lambda x: x["order"]
        )
    ]


def build_series(capability_data):
    observations = capability_data["observations"]

    x = list(range(len(observations)))
    y = [obs["mastery"] for obs in observations]

    return x, y


def main():

    parser = argparse.ArgumentParser(
        description="Render Student capability learning dynamics."
    )

    parser.add_argument(
        "input",
        type=Path
    )

    parser.add_argument(
        "output",
        type=Path
    )

    args = parser.parse_args()

    data = load_json(args.input)

    checkpoint_ids = build_checkpoint_order(data)

    threshold = data.get(
        "anomaly_threshold",
        None
    )

    plt.figure(
        figsize=(14, 8)
    )

    for capability_data in data["capabilities"]:

        capability = capability_data["capability"]

        x, y = build_series(capability_data)

        plt.plot(
            x,
            y,
            marker="o",
            linewidth=2,
            label=capability
        )

        for index, observation in enumerate(
            capability_data["observations"]
        ):

            if observation.get("is_anomaly", False):

                plt.scatter(
                    index,
                    observation["mastery"],
                    marker="X",
                    s=100,
                    zorder=5
                )

                state = observation.get(
                    "state",
                    "anomaly"
                )

                plt.annotate(
                    state,
                    (
                        index,
                        observation["mastery"]
                    ),
                    xytext=(0, 10),
                    textcoords="offset points",
                    ha="center",
                    fontsize=8
                )

    if "overall_mastery" in data:

        overall = data["overall_mastery"]

        x = list(range(len(overall)))
        y = [
            observation["mastery"]
            for observation in overall
        ]

        plt.plot(
            x,
            y,
            marker="o",
            linewidth=3,
            linestyle="--",
            label="overall_mastery"
        )

    plt.xticks(
        range(len(checkpoint_ids)),
        checkpoint_ids
    )

    plt.xlabel(
        "Student checkpoint"
    )

    plt.ylabel(
        "Capability mastery"
    )

    plt.ylim(
        0.0,
        1.0
    )

    title = "Student Capability Learning Dynamics"

    if data.get("status") == "synthetic":
        title += " - Synthetic Example"

    plt.title(title)

    if threshold is not None:
        plt.figtext(
            0.5,
            0.01,
            f"Potential anomaly threshold: |ΔM| >= {threshold:.2f}",
            ha="center",
            fontsize=9
        )

    plt.grid(
        True,
        alpha=0.25
    )

    plt.legend(
        loc="best"
    )

    plt.tight_layout(
        rect=[0, 0.03, 1, 1]
    )

    args.output.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    plt.savefig(
        args.output,
        dpi=200,
        bbox_inches="tight"
    )

    plt.close()

    print(
        f"Created: {args.output}"
    )


if __name__ == "__main__":
    main()