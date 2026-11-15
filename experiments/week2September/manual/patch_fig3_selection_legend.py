from pathlib import Path

path = Path("scripts/build_figures.py")
source = path.read_text(encoding="utf-8")

start_marker = "def fig_selection(plt, runs, sel_rows, out):"
end_marker = "\ndef fig_final(plt, acc_rows, final_t, out):"

start = source.find(start_marker)
if start < 0:
    raise SystemExit("ERROR: Cannot find fig_selection()")

end = source.find(end_marker, start)
if end < 0:
    raise SystemExit("ERROR: Cannot find fig_final() boundary")

replacement = '''def fig_selection(plt, runs, sel_rows, out):
    b5 = [r for r in runs if r.method == "B5"]

    if not b5:
        return False

    n_rounds = min(len(r.rounds()) for r in b5)

    if n_rounds < 2:
        return False

    # Preserve the original pairwise Jaccard calculation.
    mat = [
        [
            statistics.mean(
                jaccard(
                    r.train_set(i)["trajectory_ids"],
                    r.train_set(j)["trajectory_ids"],
                )
                for r in b5
            )
            for j in range(n_rounds)
        ]
        for i in range(n_rounds)
    ]

    # Wider figure and more space between panels.
    fig, (ax1, ax2) = plt.subplots(
        1,
        2,
        figsize=(12.8, 5.0),
        facecolor=SURFACE,
        gridspec_kw={"width_ratios": [1, 1.55]},
    )

    # Reserve a dedicated top band for the legend.
    fig.subplots_adjust(
        left=0.075,
        right=0.985,
        bottom=0.16,
        top=0.77,
        wspace=0.48,
    )

    # Left panel: Jaccard heatmap.
    im = ax1.imshow(
        mat,
        cmap="Blues",
        vmin=0,
        vmax=1,
        aspect="equal",
    )

    round_labels = [f"Round {i}" for i in range(n_rounds)]

    ax1.set_xticks(
        range(n_rounds),
        round_labels,
        rotation=25,
        ha="right",
    )
    ax1.set_yticks(range(n_rounds), round_labels)
    ax1.tick_params(axis="both", labelsize=9.5, colors=INK2)

    for i in range(n_rounds):
        for j in range(n_rounds):
            value = mat[i][j]
            ax1.text(
                j,
                i,
                f"{value:.3f}",
                ha="center",
                va="center",
                fontsize=10,
                fontweight="bold",
                color=SURFACE if value > 0.55 else INK,
            )

    ax1.set_title(
        "Jaccard overlap between selected sets",
        color=INK,
        fontsize=11.5,
        fontweight="bold",
        loc="left",
        pad=10,
    )

    for spine in ax1.spines.values():
        spine.set_visible(False)

    cbar = fig.colorbar(im, ax=ax1, fraction=0.046, pad=0.04)
    cbar.set_label("Jaccard similarity", fontsize=9, color=INK2)
    cbar.ax.tick_params(labelsize=9, colors=INK2)

    # Right panel: trajectory composition.
    style(ax2, "Selected trajectories per round")

    parts = (
        ("new", "#2a78d6", "New"),
        ("retained", "#eb6834", "Retained"),
        ("readmitted", "#1baf7a", "Readmitted"),
    )

    bottoms = [0.0] * n_rounds
    totals = [0.0] * n_rounds

    for key, color, label in parts:
        vals = [
            statistics.mean(
                r[key]
                for r in sel_rows
                if r["method"] == "B5" and r["round"] == t
            )
            for t in range(n_rounds)
        ]

        ax2.bar(
            range(n_rounds),
            vals,
            bottom=bottoms,
            color=color,
            width=0.62,
            label=label,
            edgecolor=SURFACE,
            linewidth=1.2,
            zorder=3,
        )

        bottoms = [b + v for b, v in zip(bottoms, vals)]
        totals = [total + value for total, value in zip(totals, vals)]

    # Keep total labels above each stacked bar.
    for x, total in enumerate(totals):
        ax2.annotate(
            f"{total:.0f}",
            (x, total),
            xytext=(0, 5),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=9.5,
            color=INK,
            fontweight="bold",
            zorder=5,
        )

    ax2.set_xticks(
        range(n_rounds),
        [f"Round {t}" for t in range(n_rounds)],
    )
    ax2.set_ylabel(
        "Number of trajectories",
        color=INK2,
        fontsize=10,
        labelpad=7,
    )

    # Extra vertical headroom prevents labels from touching the top.
    ax2.set_ylim(0, max(totals) * 1.18 if totals else 1)

    # Legend is now outside the plotting area, above the bars.
    ax2.legend(
        frameon=False,
        fontsize=9.5,
        labelcolor=INK,
        loc="lower center",
        bbox_to_anchor=(0.5, 1.035),
        ncol=3,
        borderaxespad=0,
        columnspacing=1.4,
        handlelength=1.8,
    )

    fig.suptitle(
        "B5 selection dynamics",
        color=INK,
        fontsize=13,
        fontweight="bold",
        x=0.06,
        y=0.97,
        ha="left",
    )

    fig.text(
        0.06,
        0.925,
        "Jaccard overlap and trajectory composition (mean across seeds)",
        fontsize=9.5,
        color=INK2,
    )

    fig.savefig(
        out,
        dpi=300,
        bbox_inches="tight",
        facecolor=SURFACE,
    )
    fig.savefig(
        out.with_suffix(".pdf"),
        bbox_inches="tight",
        facecolor=SURFACE,
    )

    plt.close(fig)
    return True
'''

updated = source[:start] + replacement + source[end:]
path.write_text(updated, encoding="utf-8")
print("Updated:", path)
print("Replaced only fig_selection().")
