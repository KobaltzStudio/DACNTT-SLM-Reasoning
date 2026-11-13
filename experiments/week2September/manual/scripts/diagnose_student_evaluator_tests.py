from pathlib import Path
import ast

path = Path(
    r"C:\KLTN-SLM-Reasoning\experiments\week2September\manual"
    r"\scripts\test_student_capability_evaluator_2026_11_17.py"
)

if not path.is_file():
    print("TEST_FILE_STATUS: MISSING")
    raise SystemExit(0)

source = path.read_text(encoding="utf-8-sig")
tree = ast.parse(source)

print("TEST_FILE:", path)
print("TEST_FUNCTIONS:")
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
        print(f"- {node.name}: line {node.lineno}")

print("\nREFERENCED_EVALUATOR_FUNCTIONS:")
for name in (
    "assert_unique_ids",
    "parse_capabilities",
    "wilson_interval",
    "calculate_coverage",
):
    print(f"{name}: {name in source}")

print("\nTEST_SYNTAX_STATUS: PASS")
