from pathlib import Path
import ast
import sys

ROOT = Path("experiments/week2September/manual/scripts")
FIG4 = ROOT / "build_figures.py"
FIG7 = ROOT / "capability_mastery.py"


def read_source(path):
    return path.read_text(encoding="utf-8-sig")


def replace_once(source, old, new, description):
    count = source.count(old)
    if count != 1:
        raise RuntimeError(
            f"{description}: expected 1 occurrence, found {count}"
        )
    return source.replace(old, new, 1)


def patch_fig4(source):
    start = source.find("def fig_final(")
    end = source.find("\ndef ", start + 1)

    if start < 0 or end < 0:
        raise RuntimeError("Cannot locate fig_final()")

    before, section, after = source[:start], source[start:end], source[end:]

    section = replace_once(
        section,
        "def fig_final(plt, acc_rows, final_t, out):\n",
        "def fig_final(plt, acc_rows, final_t, out):\n"
        "    from matplotlib.ticker import PercentFormatter\n",
        "Figure 4 formatter import",
    )

    # Actual source uses a single-line annotate statement.
    section = replace_once(
        section,
        '        ax.annotate(f"{mean:.3f}", (x + 0.3, mean), color=INK, fontsize=9, va="center")\n',
        '        ax.annotate(f"{mean * 100:.1f}%", (x + 0.3, mean), color=INK, fontsize=9, va="center")\n',
        "Figure 4 point labels",
    )

    section = replace_once(
        section,
        '    ax.set_ylabel("strict accuracy", color=INK2, fontsize=9)\n',
        '    ax.set_ylabel("Strict accuracy (%)", color=INK2, fontsize=9)\n'
        '    ax.yaxis.set_major_formatter(PercentFormatter(xmax=1.0))\n',
        "Figure 4 Y-axis",
    )

    return before + section + after


def patch_fig7(source):
    start = source.find("def fig_selection(")
    end = source.find("\ndef ", start + 1)

    if start < 0 or end < 0:
        raise RuntimeError("Cannot locate fig_selection()")

    before, section, after = source[:start], source[start:end], source[end:]

    section = replace_once(
        section,
        "def fig_selection(plt, rows, pool_share, out):\n",
        "def fig_selection(plt, rows, pool_share, out):\n"
        "    from matplotlib.ticker import PercentFormatter\n",
        "Figure 7 formatter import",
    )

    old = (
        '    ax.set_ylabel("share of selected trajectories", color=INK2, fontsize=9)\n'
        '    ax.legend(frameon=False, fontsize=9, labelcolor=INK, ncol=len(methods) + 1, loc="upper center",\n'
        '              bbox_to_anchor=(0.5, -0.12))\n'
        '    fig.tight_layout()\n'
    )

    new = (
        '    ax.set_ylabel("Share of selected trajectories (%)", color=INK2, fontsize=9)\n'
        '    ax.yaxis.set_major_formatter(PercentFormatter(xmax=1.0))\n'
        '    observed_max = max(\n'
        '        [r["share"] for r in rows] + list(pool_share.values()) + [0.8]\n'
        '    )\n'
        '    upper = max(0.8, min(1.0, observed_max * 1.08))\n'
        '    ax.set_ylim(0, upper)\n'
        '    ax.legend(frameon=False, fontsize=9, labelcolor=INK, ncol=len(methods) + 1, loc="upper center",\n'
        '              bbox_to_anchor=(0.5, -0.12))\n'
        '    fig.text(\n'
        '        0.5, 0.015,\n'
        '        "Caution: Capability extractor recall = 0.3601; incomplete labels may underestimate capability coverage.",\n'
        '        ha="center", va="bottom", fontsize=8, color=INK2,\n'
        '    )\n'
        '    fig.tight_layout(rect=(0, 0.09, 1, 1))\n'
    )

    section = replace_once(
        section, old, new, "Figure 7 percentage axis and warning"
    )

    return before + section + after


def main():
    for path in (FIG4, FIG7):
        if not path.exists():
            raise FileNotFoundError(path)

    original4 = read_source(FIG4)
    original7 = read_source(FIG7)

    # Prepare both changes before writing either file.
    updated4 = patch_fig4(original4)
    updated7 = patch_fig7(original7)

    # Syntax validation before writing.
    ast.parse(updated4, filename=str(FIG4))
    ast.parse(updated7, filename=str(FIG7))

    # Write UTF-8 with BOM to preserve the original file encoding style.
    FIG4.write_text(updated4, encoding="utf-8-sig")
    FIG7.write_text(updated7, encoding="utf-8-sig")

    # Read back and verify the actual files.
    check4 = read_source(FIG4)
    check7 = read_source(FIG7)

    required4 = [
        "PercentFormatter(xmax=1.0)",
        'f"{mean * 100:.1f}%"',
        'Strict accuracy (%)',
    ]
    required7 = [
        "PercentFormatter(xmax=1.0)",
        "Share of selected trajectories (%)",
        "Capability extractor recall = 0.3601",
        "fig.tight_layout(rect=(0, 0.09, 1, 1))",
    ]

    for item in required4:
        if item not in check4:
            raise RuntimeError(f"Figure 4 verification failed: {item}")

    for item in required7:
        if item not in check7:
            raise RuntimeError(f"Figure 7 verification failed: {item}")

    ast.parse(check4, filename=str(FIG4))
    ast.parse(check7, filename=str(FIG7))

    print("[OK] Figure 4 patched and verified")
    print("[OK] Figure 7 patched and verified")
    print("[OK] Both Python files passed AST syntax validation")
    print("PATCH SUCCESSFUL")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"PATCH FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
