from pathlib import Path
import re

path = Path("scripts/build_figures.py")
source = path.read_text(encoding="utf-8")

# Restrict all modifications to fig_selection().
start = source.find("def fig_selection(")
end = source.find("\ndef fig_final(", start)

if start < 0 or end < 0:
    raise SystemExit("ERROR: Cannot identify fig_selection boundaries.")

section = source[start:end]

# Backup current source.
backup = path.with_name("build_figures.py.before_title_spacing_fix_v4")
backup.write_text(source, encoding="utf-8")

# Find the main title only inside fig_selection().
title_start = section.find("    fig.suptitle(")
if title_start < 0:
    raise SystemExit("ERROR: Figure 3 suptitle not found.")

# Find the end of the suptitle call.
title_end = section.find("\n    )", title_start)
if title_end < 0:
    raise SystemExit("ERROR: Cannot identify end of Figure 3 suptitle.")

title_block = section[title_start:title_end]

# Remove an existing y argument to avoid duplicate arguments.
title_block = re.sub(
    r"^\s*y\s*=\s*[^,\n]+,\s*\n",
    "",
    title_block,
    flags=re.MULTILINE,
)

if "x=0.06," not in title_block:
    raise SystemExit("ERROR: Expected x=0.06 in Figure 3 title.")

title_block = title_block.replace(
    "x=0.06,",
    "x=0.06,\n        y=0.985,",
    1,
)

section = (
    section[:title_start]
    + title_block
    + section[title_end:]
)

# Locate the subtitle only inside fig_selection().
subtitle_start = section.find("    fig.text(")
if subtitle_start < 0:
    raise SystemExit("ERROR: Figure 3 subtitle not found.")

subtitle_end = section.find("\n    )", subtitle_start)
if subtitle_end < 0:
    raise SystemExit("ERROR: Cannot identify subtitle block.")

subtitle_block = section[subtitle_start:subtitle_end]

# Replace only the subtitle's y coordinate.
subtitle_pattern = r"(fig\.text\(\s*0\.06,\s*)[-+]?\d*\.?\d+(\s*,)"

subtitle_block, count = re.subn(
    subtitle_pattern,
    r"\g<1>0.88\g<2>",
    subtitle_block,
    count=1,
)

if count != 1:
    raise SystemExit("ERROR: Could not update subtitle coordinate.")

section = (
    section[:subtitle_start]
    + subtitle_block
    + section[subtitle_end:]
)

# Write back only the modified function.
updated = source[:start] + section + source[end:]
path.write_text(updated, encoding="utf-8")

# Verify the result.
check = path.read_text(encoding="utf-8")
check_start = check.find("def fig_selection(")
check_end = check.find("\ndef fig_final(", check_start)
check_section = check[check_start:check_end]

if "y=0.985," not in check_section:
    raise SystemExit("ERROR: Main title verification failed.")

if not re.search(r"fig\.text\(\s*0\.06,\s*0\.88\s*,", check_section):
    raise SystemExit("ERROR: Subtitle verification failed.")

print("PATCH SUCCESSFUL")
print("Figure 3 title y: 0.985")
print("Figure 3 subtitle y: 0.88")
print("Other figure functions were not modified.")
