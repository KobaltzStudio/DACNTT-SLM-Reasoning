from pathlib import Path

p = Path("scripts/capability_eval.py")
lines = p.read_text(encoding="utf-8").splitlines()

ranges = [
    (130, 220),
    (250, 320),
    (319, 530),
    (560, 675),
]

out = []
for start, end in ranges:
    out.append(f"\n{'='*24} LINES {start}-{end} {'='*24}")
    for i in range(start, min(end, len(lines)) + 1):
        out.append(f"{i:04d}: {lines[i-1]}")

Path("reports/p1p2_integration/capability_eval_source_sections.txt").write_text(
    "\n".join(out) + "\n",
    encoding="utf-8",
)
print("SOURCE_EXTRACT:", Path("reports/p1p2_integration/capability_eval_source_sections.txt").resolve())
