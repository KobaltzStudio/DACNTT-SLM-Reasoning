import json
import sys
from pathlib import Path


ALLOWED_CAPABILITIES = {
    "addition",
    "subtraction",
    "multiplication",
    "division",
    "percentage",
    "fraction",
    "ratio",
}

ALLOWED_EDGE_TYPES = {
    "prerequisite",
    "transfer",
}


def fail(message):
    print(f"INVALID: {message}")
    raise SystemExit(1)


def main():
    if len(sys.argv) != 2:
        print(
            "Usage: python validate_graph.py <graph.json>"
        )
        raise SystemExit(2)

    path = Path(sys.argv[1])

    if not path.exists():
        fail(f"File not found: {path}")

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        fail(f"Invalid JSON: {exc}")

    required = {
        "graph_id",
        "student_checkpoint",
        "nodes",
        "edges",
    }

    missing = required - set(data)

    if missing:
        fail(f"Missing fields: {sorted(missing)}")

    if not isinstance(data["nodes"], list):
        fail("'nodes' must be a list")

    if not isinstance(data["edges"], list):
        fail("'edges' must be a list")

    node_ids = set()

    for node in data["nodes"]:
        for field in ("node_id", "capability"):
            if field not in node:
                fail(f"Node missing field: {field}")

        capability = node["capability"]

        if capability not in ALLOWED_CAPABILITIES:
            fail(
                f"Unknown capability: {capability}"
            )

        node_id = node["node_id"]

        if node_id in node_ids:
            fail(f"Duplicate node_id: {node_id}")

        node_ids.add(node_id)

        if "mastery" in node and node["mastery"] is not None:
            if not 0 <= node["mastery"] <= 1:
                fail(
                    f"Invalid mastery for {node_id}"
                )

        if "deficit" in node and node["deficit"] is not None:
            if not 0 <= node["deficit"] <= 1:
                fail(
                    f"Invalid deficit for {node_id}"
                )

    for edge in data["edges"]:
        for field in ("source", "target", "type"):
            if field not in edge:
                fail(f"Edge missing field: {field}")

        if edge["source"] not in node_ids:
            fail(
                f"Unknown edge source: {edge['source']}"
            )

        if edge["target"] not in node_ids:
            fail(
                f"Unknown edge target: {edge['target']}"
            )

        if edge["type"] not in ALLOWED_EDGE_TYPES:
            fail(
                f"Unknown edge type: {edge['type']}"
            )

        if "score" in edge and edge["score"] is not None:
            if not isinstance(edge["score"], (int, float)):
                fail("Edge score must be numeric or null")

    print(f"VALID: {path}")
    print(f"Nodes validated: {len(data['nodes'])}")
    print(f"Edges validated: {len(data['edges'])}")


if __name__ == "__main__":
    main()