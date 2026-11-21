import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx


def main():
    if len(sys.argv) != 3:
        print(
            "Usage: python render_graph.py <input.json> <output.png>"
        )
        raise SystemExit(2)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])

    with input_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    graph = nx.DiGraph()

    for node in data["nodes"]:
        graph.add_node(
            node["node_id"],
            capability=node["capability"],
        )

    for edge in data["edges"]:
        graph.add_edge(
            edge["source"],
            edge["target"],
            type=edge["type"],
            score=edge.get("score"),
        )

    positions = nx.spring_layout(
        graph,
        seed=42
    )

    plt.figure(figsize=(10, 7))

    nx.draw_networkx_nodes(
        graph,
        positions,
        node_size=2200,
    )

    nx.draw_networkx_labels(
        graph,
        positions,
        labels={
            node: node
            for node in graph.nodes
        },
        font_size=9,
    )

    prerequisite_edges = [
        (u, v)
        for u, v, d in graph.edges(data=True)
        if d["type"] == "prerequisite"
    ]

    transfer_edges = [
        (u, v)
        for u, v, d in graph.edges(data=True)
        if d["type"] == "transfer"
    ]

    if prerequisite_edges:
        nx.draw_networkx_edges(
            graph,
            positions,
            edgelist=prerequisite_edges,
            arrows=True,
            width=1.5,
        )

    if transfer_edges:
        nx.draw_networkx_edges(
            graph,
            positions,
            edgelist=transfer_edges,
            arrows=True,
            width=2.5,
            style="dashed",
        )

    edge_labels = {}

    for u, v, d in graph.edges(data=True):
        if d["score"] is not None:
            edge_labels[(u, v)] = (
                f"{d['type']}: {d['score']:.2f}"
            )
        else:
            edge_labels[(u, v)] = d["type"]

    nx.draw_networkx_edge_labels(
        graph,
        positions,
        edge_labels=edge_labels,
        font_size=8,
    )

    plt.title(
        f"Capability Graph - "
        f"{data['student_checkpoint']}"
    )

    plt.axis("off")

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    plt.tight_layout()
    plt.savefig(
        output_path,
        dpi=200,
        bbox_inches="tight",
    )

    plt.close()

    print(f"Created: {output_path}")


if __name__ == "__main__":
    main()