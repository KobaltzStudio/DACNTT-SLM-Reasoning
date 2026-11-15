from pathlib import Path
import re

path = Path("scripts/build_figures.py")
source = path.read_text(encoding="utf-8")

# Backup is already available, but create another safety copy.
backup = path.with_name("build_figures.py.before_title_spacing_fix_v3")
backup.write_text(source, encoding="utf-8")

# 1. Move the main title slightly upward.
title_pattern = r'fig\.suptitle\((.*?)\n\s*\)'
title_matches = list(re.finditer(title_pattern, source, re.S))

if len(title_matches) != 1:
    raise SystemExit(
        f"Expected exactly 1 fig.suptitle() in file, found {len(title_matches)}"
    )

title_block = title_matches[0].group(0)

# Remove an existing y= argument, if present.
title_block = re.sub(
    r'^\s*y\s*=\s*[^,\n]+,\s*\n',
    '',
    title_block,
    flags=re.M,
)

# Insert the new y coordinate after x=0.06.
if "x=0.06," not in title_block:
    raise SystemExit("Cannot find x=0.06 in main title.")

title_block = title_block.replace(
    "x=0.06,",
    "x=0.06,\n        y=0.985,",
    1,
)

source = source[:title_matches[0].start()] + title_block + source[title_matches[0].end():]

# 2. Move the subtitle downward.
subtitle_pattern = r'(fig\.text\(\s*0\.06,\s*)[-+]?\d*\.?\d+(\s*,)'
source, subtitle_count = re.subn(
    subtitle_pattern,
    r'\g<1>0.855\g<2>',
    source,
    count=1,
)

if subtitle_count != 1:
    raise SystemExit(
        f"Expected 1 subtitle coordinate to change, got {subtitle_count}"
    )

path.write_text(source, encoding="utf-8")

# Verify the written source.
check = path.read_text(encoding="utf-8")

if "y=0.985," not in check or not re.search(
    r'fig\.text\(\s*0\.06,\s*0\.855\s*,', check
):
    raise SystemExit("Verification failed after writing.")

print("PATCH SUCCESSFUL")
print("Main title y = 0.985")
print("Subtitle y = 0.855")
