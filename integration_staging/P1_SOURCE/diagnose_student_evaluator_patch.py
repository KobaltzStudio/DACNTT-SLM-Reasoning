from pathlib import Path
import ast
import hashlib
import sys

path = Path(
    r"C:\KLTN-SLM-Reasoning\experiments\week2September\manual"
    r"\scripts\evaluate_student_capabilities.py"
)

if not path.is_file():
    raise SystemExit(f"EVALUATOR_NOT_FOUND: {path}")

raw = path.read_bytes()
source = raw.decode("utf-8-sig")

print("FILE:", path)
print("SIZE_BYTES:", len(raw))
print("SHA256:", hashlib.sha256(raw).hexdigest())
print("CRLF_COUNT:", raw.count(b"\r\n"))
print("LF_COUNT:", raw.count(b"\n"))
print("HAS_BOM:", raw.startswith(b"\xef\xbb\xbf"))

try:
    tree = ast.parse(source)
    print("\nAST_STATUS: PASS")
except SyntaxError as exc:
    print("\nAST_STATUS: FAIL")
    print("SYNTAX_ERROR:", exc)
    raise

print("\nTOP_LEVEL_FUNCTIONS:")
for node in tree.body:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        print(
            f"{node.name}: lines {node.lineno}-{node.end_lineno}"
        )

print("\nRELEVANT_SOURCE_LINES:")
keywords = (
    "assert_unique_ids",
    "calculate_coverage",
    "predictions_outside_dev",
    "gold_ids =",
    "matched_ids =",
    "missing_prediction_ids =",
    "predictions_without_confirmed_gold",
    "prediction_ids",
)

for number, line in enumerate(source.splitlines(), 1):
    if any(key in line for key in keywords):
        print(f"{number:04d}: {line}")

print("\nFUNCTION_SIGNATURE_CANDIDATES:")
for line in source.splitlines():
    stripped = line.strip()
    if stripped.startswith("def ") and (
        "assert" in stripped
        or "coverage" in stripped
        or "unique" in stripped
    ):
        print(repr(line))

print("\nDIAGNOSTIC_STATUS: PASS")
