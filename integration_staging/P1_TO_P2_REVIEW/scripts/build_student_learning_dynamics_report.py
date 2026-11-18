from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

CAPABILITIES = [
    "addition",
    "subtraction",
    "multiplication",
    "division",
    "percentage",
    "fraction",
    "ratio",
]


def read_csv(path: Path):
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def fmt(value, digits=4):
    if value is None or value == "":
        return "—"
    return f"{float(value):.{digits}f}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manual", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    manual = Path(args.manual).resolve()
    output_dir = Path(args.output).resolve()

    csv_path = output_dir / "capability_learning_curves.csv"
    graph_path = output_dir / "capability_graph.json"
    ledger_path = output_dir / "graph_evidence_ledger.csv"
    protocol_path = manual / "config" / "proposal1_graph_protocol.md"

    for path in (csv_path, graph_path, ledger_path, protocol_path):
        if not path.is_file():
            raise FileNotFoundError(f"Required input not found: {path}")

    rows = read_csv(csv_path)

    if len(rows) != 21:
        raise ValueError(f"Expected 21 learning curve records, got {len(rows)}")

    required_columns = {
        "method",
        "seed",
        "round",
        "checkpoint",
        "capability",
        "n_support",
        "n_correct",
        "mastery",
        "deficit",
        "delta_vs_previous",
        "delta_classification",
        "total_change_round0_to_round2",
        "trend_label",
    }

    if not rows:
        raise ValueError("Learning curve CSV is empty")

    missing = required_columns - set(rows[0])
    if missing:
        raise ValueError(f"CSV missing columns: {sorted(missing)}")

    by_capability = defaultdict(list)

    for row in rows:
        by_capability[row["capability"]].append(row)

    if set(by_capability) != set(CAPABILITIES):
        raise ValueError("CSV capability taxonomy mismatch")

    for capability in CAPABILITIES:
        by_capability[capability].sort(
            key=lambda item: int(item["round"])
        )

        if len(by_capability[capability]) != 3:
            raise ValueError(
                f"{capability} must have exactly 3 checkpoint records"
            )

    methods = {row["method"] for row in rows}
    seeds = {row["seed"] for row in rows}

    if methods != {"B4"}:
        raise ValueError(f"Unexpected methods: {methods}")

    if seeds != {"13"}:
        raise ValueError(f"Unexpected seeds: {seeds}")

    graph = __import__("json").loads(
        graph_path.read_text(encoding="utf-8")
    )

    ledger = read_csv(ledger_path)

    if len(graph["nodes"]) != 7 or len(graph["edges"]) != 0:
        raise ValueError("Graph must contain 7 nodes and 0 edges")

    if len(ledger) != 84:
        raise ValueError("Evidence ledger must contain 84 records")

    lines = []

    def add(text=""):
        lines.append(text)

    add("# Student Learning Dynamics")
    add()
    add("## 1. Experimental Setting")
    add()
    add("- Method: B4")
    add("- Seed: 13")
    add("- Student checkpoints: 3")
    add("- Observed rounds: 0, 1, 2")
    add("- Capability taxonomy: 7 frozen capabilities")
    add("- Evaluation observations: 21 (7 capabilities × 3 checkpoints)")
    add()
    add(
        "This report describes the observed evaluation results for one "
        "Student training chain. It does not claim statistical "
        "generalization across seeds or training methods."
    )
    add()
    add("## 2. Checkpoint Identity and Round Normalization")
    add()
    add(
        "The first evaluation manifest records the checkpoint round as "
        "`round_unknown`. The Learning Curves builder normalizes this "
        "observation to Round 0 only after checking the checkpoint identity "
        "against `student_ckpt_001` and verifying its Round 0 training "
        "lineage through the corresponding train log, train-set path, "
        "and train-set SHA256."
    )
    add()
    add(
        "The original evaluation manifest is not modified. "
        "The normalized round is an analytical mapping in the generated "
        "learning-curve dataset."
    )
    add()
    add("| Round | Checkpoint |")
    add("|---:|---|")

    checkpoint_by_round = {}

    for row in rows:
        checkpoint_by_round[int(row["round"])] = row["checkpoint"]

    for round_index in sorted(checkpoint_by_round):
        add(
            f"| {round_index} | "
            f"`{checkpoint_by_round[round_index]}` |"
        )

    add()
    add("## 3. Metric Definitions")
    add()
    add(
        "Capability mastery is computed as the number of correct "
        "evaluation examples divided by the support for that capability:"
    )
    add()
    add("`M(c | S_t) = correct_c / n_support_c`")
    add()
    add("Capability deficit is:")
    add()
    add("`D(c | S_t) = 1 - M(c | S_t)`")
    add()
    add("For each transition after the first checkpoint:")
    add()
    add("`DeltaM(c, t) = M(c | S_t) - M(c | S_(t-1))`")
    add()
    add(
        "Confidence intervals in the CSV are Wilson intervals. They are "
        "descriptive uncertainty intervals for each checkpoint-level "
        "proportion; overlap or non-overlap is not treated here as a "
        "paired significance test."
    )
    add()
    add("## 4. Capability-Level Results")
    add()
    add(
        "| Capability | Round 0 | Round 1 | Round 2 | "
        "Total change | Trend |"
    )
    add(
        "|---|---:|---:|---:|---:|---|"
    )

    for capability in CAPABILITIES:
        items = by_capability[capability]
        values = [fmt(item["mastery"]) for item in items]
        total_change = fmt(items[-1]["total_change_round0_to_round2"])
        trend = items[-1]["trend_label"]

        add(
            f"| {capability} | {values[0]} | {values[1]} | "
            f"{values[2]} | {total_change} | {trend} |"
        )

    add()
    add("### 4.1. Evaluation Support")
    add()
    add("| Capability | Support | Correct at Round 0 |")
    add("|---|---:|---:|")

    for capability in CAPABILITIES:
        first = by_capability[capability][0]
        add(
            f"| {capability} | {first['n_support']} | "
            f"{first['n_correct']} |"
        )

    add()
    add("## 5. Transition-Level Dynamics")
    add()
    add(
        "The following table reports the transition classification "
        "recorded in the source CSV. These labels are descriptive "
        "operational categories, not statistical hypothesis-test results."
    )
    add()
    add(
        "| Capability | Round 0 → 1 delta | Classification | "
        "Round 1 → 2 delta | Classification |"
    )
    add("|---|---:|---|---:|---|")

    for capability in CAPABILITIES:
        items = by_capability[capability]
        first, second = items[1], items[2]

        add(
            f"| {capability} | "
            f"{fmt(first['delta_vs_previous'])} | "
            f"{first['delta_classification']} | "
            f"{fmt(second['delta_vs_previous'])} | "
            f"{second['delta_classification']} |"
        )

    add()
    add("## 6. Observations")
    add()

    improved = []
    regressed = []
    stable = []

    for capability in CAPABILITIES:
        items = by_capability[capability]
        total = float(items[-1]["total_change_round0_to_round2"])

        if total > 0:
            improved.append(capability)
        elif total < 0:
            regressed.append(capability)
        else:
            stable.append(capability)

    add(
        "- Capabilities with positive Round 0-to-Round 2 change: "
        + (", ".join(improved) if improved else "None")
        + "."
    )
    add(
        "- Capabilities with negative Round 0-to-Round 2 change: "
        + (", ".join(regressed) if regressed else "None")
        + "."
    )
    add(
        "- Capabilities with zero Round 0-to-Round 2 change: "
        + (", ".join(stable) if stable else "None")
        + "."
    )
    add()
    add(
        "These comparisons describe only the measured checkpoints. "
        "They do not establish why a capability improved or regressed."
    )
    add()
    add("## 7. Graph Interpretation")
    add()
    add("- Graph nodes: 7")
    add("- Established graph edges: 0")
    add("- Evidence ledger records: 84")
    add("- Established prerequisite relationships: 0")
    add("- Established transfer relationships: 0")
    add()
    add(
        "The graph contains the seven capability identities defined by "
        "the frozen manual taxonomy. No prerequisite edge is added because "
        "the current evidence does not establish a validated prerequisite "
        "relationship. No transfer edge is added because the available "
        "learning curves are observational and no controlled intervention "
        "on a source capability with measured downstream change has been "
        "provided."
    )
    add()
    add(
        "Co-movement, correlation, mastery ordering, or simultaneous "
        "regression between capabilities is not treated as proof of "
        "prerequisite or transfer relationships."
    )
    add()
    add("## 8. Limitations")
    add()
    add(
        "1. The current analysis contains one method (B4), one seed (13), "
        "and three checkpoints."
    )
    add(
        "2. Capability-specific evaluation support is small and differs "
        "between capabilities."
    )
    add(
        "3. The results are descriptive observations and should not be "
        "interpreted as statistically significant improvements or "
        "regressions."
    )
    add(
        "4. Separate checkpoint confidence intervals do not replace a "
        "paired analysis over problem-level correctness."
    )
    add(
        "5. No controlled intervention experiment is available to "
        "estimate student-specific transfer."
    )
    add(
        "6. The current evidence is insufficient to identify transfer "
        "bottlenecks."
    )
    add()
    add("## 9. Conclusion and Next Research Steps")
    add()
    add(
        "The current experiment provides a checkpoint-level description "
        "of mastery across seven capabilities for B4 seed 13. The "
        "learning-curve dataset contains 21 observations. The associated "
        "capability graph contains seven nodes and no established edges."
    )
    add()
    add(
        "Further work should evaluate additional seeds and checkpoints, "
        "retain problem-level paired evaluation outcomes, and conduct "
        "controlled capability interventions before making claims about "
        "prerequisite dependencies or transfer effects."
    )
    add()
    add("---")
    add()
    add(
        "Generated from `capability_learning_curves.csv`, "
        "`capability_graph.json`, and `graph_evidence_ledger.csv`."
    )

    report_path = output_dir / "student_learning_dynamics.md"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("LEARNING DYNAMICS REPORT BUILD: PASS")
    print(f"OBSERVATIONS: {len(rows)}")
    print(f"CAPABILITIES: {len(by_capability)}")
    print(f"CHECKPOINTS: {len(checkpoint_by_round)}")
    print(f"OUTPUT: {report_path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(
            f"LEARNING DYNAMICS REPORT BUILD: FAIL: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)
