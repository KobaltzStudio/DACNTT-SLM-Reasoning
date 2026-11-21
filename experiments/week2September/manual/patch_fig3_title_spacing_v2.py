from pathlib import Path
import re

path = Path("scripts/build_figures.py")
source = path.read_text(encoding="utf-8")

start = source.find("def fig_selection(")
end = source.find("\ndef fig_final(", start)

if start < 0 or end < 0:
    raise SystemExit("ERROR: Cannot locate fig_selection().")

section = source[start:end]

# Locate the main title and subtitle blocks.
title_start = section.find("    fig.suptitle(")
text_start = section.find("    fig.text(", title_start)

if title_start < 0 or text_start < 0:
    raise SystemExit("ERROR: Cannot locate title/subtitle blocks.")

title_block = section[title_start:text_start]

# Remove any previous y= setting to avoid duplicate keyword arguments.
title_block = re.sub(
    r"^\s*y\s*=\s*[^,\n]+,\s*\n",
    "",
    title_block,
    flags=re.MULTILINE,
)

# Set the main title higher.
if "x=0.06," in title_block:
    title_block = title_block.replace(
        "x=0.06,",
        "x=0.06,\n        y=0.985,",
        1,
    )
else:
    raise SystemExit("ERROR: Cannot locate x position in fig.suptitle().")

# Locate the subtitle block.
text_end = section.find("    fig.tight_layout(", text_start)
if text_end < 0:
    raise SystemExit("ERROR: Cannot locate fig.tight_layout().")

text_block = section[text_start:text_end]

# Change the subtitle's vertical coordinate to 0.855.
pattern = r"(fig\.text\(\s*\n\s*0\.06,\s*\n\s*)([-+]?\d*\.?\d+)(\s*,)"
text_block, count = re.subn(
    pattern,
    r"\g<1>0.855\g<3>",
    text_block,
    count=1,
)

if count != 1:
    raise SystemExit("ERROR: Cannot locate subtitle y-coordinate.")

# Reassemble only fig_selection().
section = (
    section[:title_start]
    + title_block
    + text_block
    + section[text_end:]
)

source = source[:start] + section + source[end:]
path.write_text(source, encoding="utf-8")

print("SUCCESS: title and subtitle positions updated.")
print("Main title y = 0.985")
print("Subtitle y = 0.855")
