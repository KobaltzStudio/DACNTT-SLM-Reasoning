from pathlib import Path
import ast

files = [
    Path("experiments/week2September/manual/scripts/build_figures.py"),
    Path("experiments/week2September/manual/scripts/capability_mastery.py"),
]

keywords = (
    "fig_final",
    "selection_capabilities",
    "fig_selection",
)

for path in files:
    if not path.exists():
        print(f"\n[NOT FOUND] {path}")
        continue

    source = path.read_text(encoding="utf-8")
    lines = source.splitlines()
    tree = ast.parse(source)

    print(f"\n{'=' * 90}")
    print(f"FILE: {path}")
    print(f"{'=' * 90}")

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if any(k in node.name.lower() for k in keywords):
                start = node.lineno
                end = node.end_lineno

                print(f"\n--- FUNCTION: {node.name} (lines {start}-{end}) ---")
                for i in range(start - 1, end):
                    print(f"{i + 1:4}: {lines[i]}")
