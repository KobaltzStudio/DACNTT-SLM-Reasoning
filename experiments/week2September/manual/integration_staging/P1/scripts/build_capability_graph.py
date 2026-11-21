from __future__ import annotations

import argparse
import json
import sys
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


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def validate_graph(graph: dict, schema: dict):
    required = schema["required"]

    for key in required:
        if key not in graph:
            raise ValueError(f"Graph missing required field: {key}")

    if graph["status"] not in schema["properties"]["status"]["enum"]:
        raise ValueError("Invalid graph status")

    if len(graph["nodes"]) != len(CAPABILITIES):
        raise ValueError("Graph must contain exactly 7 nodes")

    actual = [node["capability"] for node in graph["nodes"]]

    if actual != CAPABILITIES:
        raise ValueError(
            f"Capability taxonomy mismatch: {actual}"
        )

    if len(graph["edges"]) != 0:
        raise ValueError(
            "Current observational evidence does not authorize graph edges"
        )

    node_schema = schema["properties"]["nodes"]["items"]

    for index, node in enumerate(graph["nodes"]):
        for key in node_schema["required"]:
            if key not in node:
                raise ValueError(
                    f"Node {index} missing required field: {key}"
                )

        if node.get("capability") not in CAPABILITIES:
            raise ValueError(
                f"Invalid capability in node {index}"
            )

        if node_schema.get("additionalProperties") is False:
            extra = set(node) - set(node_schema["properties"])
            if extra:
                raise ValueError(
                    f"Unexpected node fields at index {index}: {extra}"
                )

    if schema.get("additionalProperties") is False:
        extra = set(graph) - set(schema["properties"])
        if extra:
            raise ValueError(f"Unexpected graph fields: {extra}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manual", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    manual = Path(args.manual).resolve()
    output_dir = Path(args.output).resolve()

    protocol_path = manual / "config" / "proposal1_graph_protocol.md"
    schema_path = manual / "schemas" / "capability_graph_schema.json"
    curve_path = output_dir / "capability_learning_curves.csv"
    output_path = output_dir / "capability_graph.json"

    for path in (
        protocol_path,
        schema_path,
        curve_path,
    ):
        if not path.is_file():
            raise FileNotFoundError(f"Required input not found: {path}")

    protocol = protocol_path.read_text(encoding="utf-8")

    required_protocol_terms = [
        "Capability Taxonomy",
        "Prerequisite Edge",
        "Transfer Edge",
        "controlled intervention",
        "Research Integrity Constraint",
    ]

    for term in required_protocol_terms:
        if term.lower() not in protocol.lower():
            raise ValueError(
                f"Protocol does not contain expected concept: {term}"
            )

    schema = load_json(schema_path)

    graph = {
        "graph_id": "proposal1_capability_graph",
        "student_checkpoint": "B4_seed13_ckpt003",
        "status": "empirical",
        "nodes": [
            {
                "node_id": capability,
                "capability": capability,
            }
            for capability in CAPABILITIES
        ],
        "edges": [],
    }

    validate_graph(graph, schema)

    output_dir.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(graph, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print("CAPABILITY GRAPH BUILD: PASS")
    print(f"NODES: {len(graph['nodes'])}")
    print(f"EDGES: {len(graph['edges'])}")
    print(f"SCHEMA: {schema_path}")
    print(f"OUTPUT: {output_path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"CAPABILITY GRAPH BUILD: FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
