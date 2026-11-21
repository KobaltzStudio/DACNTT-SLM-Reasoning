from pathlib import Path

p = Path("scripts/build_figures.py")
s = p.read_text(encoding="utf-8")

start = s.index("def fig_selection(")
end = s.index("\ndef fig_final(", start)

section = s[start:end]

old_title = """        x=0.06,
        ha="left",
    )

    fig.text(
        0.06,
        0.925,"""

new_title = """        x=0.06,
        y=0.985,
        ha="left",
    )

    fig.text(
        0.06,
        0.895,"""

if old_title not in section:
    raise SystemExit("Cannot find expected title/subtitle positions. No changes made.")

section = section.replace(old_title, new_title, 1)
s = s[:start] + section + s[end:]

p.write_text(s, encoding="utf-8")
print("Updated title spacing in fig_selection().")
