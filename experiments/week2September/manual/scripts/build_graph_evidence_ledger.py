from __future__ import annotations

import argparse
import csv
import json
import sys
from itertools import permutations
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

RELATIONSHIPS = [
    "prerequisite",
    "transfer",
]

FIELDS = [
    "source_capability",
    "target_capability",
    "relationship_type",
    "status",
    "evidence_available",
    "evidence_source",
    "decision_reason",
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manual", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    manual = Path(args.manual).resolve()
    output_dir = Path(args.output).resolve()

    protocol_path = manual / "config" / "proposal1_graph_protocol.md"
    graph_path = output_dir / "capability_graph.json"
    output_path = output_dir / "graph_evidence_ledger.csv"

    for path in (protocol_path, graph_path):
        if not path.is_file():
            raise FileNotFoundError(f"Required input not found: {path}")

    protocol = protocol_path.read_text(encoding="utf-8")
    graph = json.loads(graph_path.read_text(encoding="utf-8"))

    if len(graph.get("nodes", [])) != 7:
        raise ValueError("Graph must contain 7 nodes")

    if graph.get("edges") != []:
        raise ValueError("Graph must have 0 edges before ledger generation")

    if "controlled intervention" not in protocol.lower():
        raise ValueError(
            "Protocol does not document controlled intervention requirement"
        )

    rows = []

    for source, target in permutations(CAPABILITIES, 2):
        for relationship in RELATIONSHIPS:
            if relationship == "prerequisite":
                reason = (
                    "Not established: no validated prerequisite evidence "
                    "has been supplied for this directed pair."
                )
            else:
                reason = (
                    "Not established: no controlled intervention on the "
                    "source capability with measured downstream change "
                    "has been supplied for this directed pair."
                )

            rows.append({
                "source_capability": source,
                "target_capability": target,
                "relationship_type": relationship,
                "status": "not_established",
                "evidence_available": "false",
                "evidence_source": "",
                "decision_reason": reason,
            })

    if len(rows) != 84:
        raise ValueError(f"Expected 84 rows, got {len(rows)}")

    pair_set = {
        (row["source_capability"], row["target_capability"])
        for row in rows
    }

    if len(pair_set) != 42:
        raise ValueError("Expected exactly 42 directed capability pairs")

    if any(
        row["source_capability"] == row["target_capability"]
        for row in rows
    ):
        raise ValueError("Self-pair detected")

    if any(
        row["status"] != "not_established"
        or row["evidence_available"] != "false"
        for row in rows
    ):
        raise ValueError("Unverified relationship incorrectly established")

    output_dir.mkdir(parents=True, exist_ok=True)

    with output_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print("GRAPH EVIDENCE LEDGER BUILD: PASS")
    print(f"CAPABILITIES: {len(CAPABILITIES)}")
    print(f"DIRECTED PAIRS: {len(pair_set)}")
    print(f"RELATIONSHIP TYPES: {len(RELATIONSHIPS)}")
    print(f"RECORDS: {len(rows)}")
    print(f"ESTABLISHED RELATIONSHIPS: 0")
    print(f"OUTPUT: {output_path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"GRAPH EVIDENCE LEDGER BUILD: FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
