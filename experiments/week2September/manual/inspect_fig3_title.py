from pathlib import Path

p = Path("scripts/build_figures.py")
s = p.read_text(encoding="utf-8")

start = s.find("def fig_selection(")
end = s.find("\ndef fig_final(", start)

if start < 0:
    raise SystemExit("Cannot find fig_selection")

section = s[start:end]

print("========== FIG_SELECTION TITLE SECTION ==========")

for i, line in enumerate(section.splitlines(), 1):
    if any(x in line for x in (
        "suptitle", "fig.text", "tight_layout",
        "subplots_adjust", "bbox_to_anchor"
    )):
        print(f"{i:03}: {line}")

print("========== END ==========")
