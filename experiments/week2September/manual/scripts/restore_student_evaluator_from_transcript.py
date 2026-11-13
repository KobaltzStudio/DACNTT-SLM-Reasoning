from pathlib import Path
import ast
import hashlib
import sys

transcript = Path(
    r"C:\KLTN-SLM-Reasoning\experiments\week2September\manual"
    r"\reports\capability\student_eval_2026-11-17"
    r"\evaluator_source_transcript.txt"
)
output = Path(
    r"C:\KLTN-SLM-Reasoning\experiments\week2September\manual"
    r"\scripts\evaluate_student_capabilities.py"
)

if not transcript.is_file():
    raise SystemExit(f"TRANSCRIPT_NOT_FOUND: {transcript}")

lines = transcript.read_text(encoding="utf-8-sig").splitlines()

start_marker = ">> from __future__ import annotations"
end_marker = ">> '@ | Set-Content -Path $EvaluatorPath -Encoding UTF8"

start = next(
    (i for i, line in enumerate(lines) if line.rstrip() == start_marker),
    None,
)
if start is None:
    raise SystemExit("SOURCE_START_MARKER_NOT_FOUND")

end = next(
    (
        i for i in range(start + 1, len(lines))
        if lines[i].rstrip() == end_marker
    ),
    None,
)
if end is None:
    raise SystemExit("SOURCE_END_MARKER_NOT_FOUND")

source_lines = []
for line in lines[start:end]:
    if not line.startswith(">>"):
        raise SystemExit(
            f"UNEXPECTED_TRANSCRIPT_LINE at {len(source_lines) + 1}: {line!r}"
        )
    content = line[2:]
    if content.startswith(" "):
        content = content[1:]
    source_lines.append(content)

source = "\n".join(source_lines).rstrip() + "\n"

if len(source.encode("utf-8")) < 5000:
    raise SystemExit(
        f"RECOVERED_SOURCE_TOO_SHORT: {len(source.encode('utf-8'))} bytes"
    )

tree = ast.parse(source)
functions = {
    node.name
    for node in tree.body
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
}
required = {
    "assert_unique_ids",
    "parse_capabilities",
    "wilson_interval",
    "load_confirmed_gold",
    "validate_expected_hashes",
    "evaluate",
    "self_test",
    "main",
}
missing = sorted(required - functions)
if missing:
    raise SystemExit(f"REQUIRED_FUNCTIONS_MISSING: {missing}")

output.parent.mkdir(parents=True, exist_ok=True)

# Preserve the current empty file as evidence before replacing it.
if output.exists() and output.stat().st_size == 0:
    empty_backup = output.with_suffix(".py.empty_backup")
    empty_backup.write_bytes(output.read_bytes())

output.write_text(source, encoding="utf-8", newline="\n")

written = output.read_bytes()
print("RESTORE_STATUS: PASS")
print("OUTPUT:", output)
print("SIZE_BYTES:", len(written))
print("SHA256:", hashlib.sha256(written).hexdigest())
print("FUNCTIONS:", ", ".join(sorted(functions)))
