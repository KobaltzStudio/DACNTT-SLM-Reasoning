from pathlib import Path

path = Path("scripts/build_figures.py")
source = path.read_text(encoding="utf-8")

start = source.find("    ax2.set_ylim(", source.find("def fig_selection("))
end = source.find("    fig.suptitle(", start)

if start < 0 or end < 0:
    raise SystemExit("ERROR: Cannot locate the y-limit and legend section.")

replacement = '''    # Reserve whitespace between the panel title and the bar columns.
    ax2.set_ylim(
        0,
        max(totals) * 1.38 if totals else 1,
    )

    # Place all legend entries inside the reserved upper whitespace.
    # This keeps the legend below the panel title and above the bars.
    ax2.legend(
        frameon=False,
        fontsize=9.5,
        labelcolor=INK,
        loc="upper right",
        bbox_to_anchor=(0.99, 0.99),
        ncol=3,
        borderaxespad=0.0,
        columnspacing=1.0,
        handlelength=1.5,
    )

'''

updated = source[:start] + replacement + source[end:]
path.write_text(updated, encoding="utf-8")
print("Updated legend position in:", path)
