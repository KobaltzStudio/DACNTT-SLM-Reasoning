#!/usr/bin/env python3
"""
Tables and paper figures from a runs directory (Plan.docx section 6: Figures 1-4, Tables 2-5). Missing runs
are reported and left out; nothing is imputed. Run score_learnability.py first for the learnability parts.

Tables (CSV, <out>/tables/)
  accuracy.csv            method, seed, checkpoint, split: strict / lenient accuracy, format compliance
  accuracy_summary.csv    mean and SD over seeds (B0 = S_0)
  b5_vs_b4.csv            per seed on D_test at the final checkpoint: accuracies, difference, discordant
                          pairs, exact McNemar p; then mean, SD and 95% t-interval of the difference
  learnability.csv        per run and checkpoint: ell* , sigma, IQR, mean L_proxy, Spearman of L_proxy with
                          the previous checkpoint of the same run (all trajectories)
  selection.csv           per method, seed, round: trajectories, tokens, new / retained / re-admitted /
                          dropped, Jaccard with the previous round, selection / training / NLL seconds
Figures (PNG, <out>/figures/)
  fig1_accuracy_curve.png       accuracy S_0..S_3, D_dev and D_test panels, mean +- SD over seeds
  fig2_learnability.png         distribution of ell at S_0, S_1, S_2 for B5 and B4 (all seeds pooled)
  fig3_selection_dynamics.png   B5: Jaccard between rounds (mean over seeds) and new / retained /
                                re-admitted trajectories per round
  fig4_final_accuracy.png       D_test accuracy at the final checkpoint: each seed and mean +- SD

Usage (from experiments/week2September/manual/):
  python scripts/score_learnability.py runs/main
  python scripts/build_figures.py runs/main --out reports/task7/main_results
Needs matplotlib for the figures (tables are written without it).
"""
import argparse
import csv
import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_layout import discover, jaccard, load_eval, load_timing, spearman  # noqa: E402
from student_common import read_jsonl  # noqa: E402

METHODS = ("B5", "B4", "B2", "B3")
# Reference categorical palette (dataviz skill), fixed slot per method; validated: all checks pass in light
# mode, contrast WARN for slots 3-4 -> every series also has a marker shape and a legend, and every value is
# in the CSV tables.
COLOR = {"B5": "#2a78d6", "B4": "#eb6834", "B2": "#1baf7a", "B3": "#eda100"}
MARKER = {"B5": "o", "B4": "s", "B2": "^", "B3": "D"}
LABEL = {"B5": "B5 dynamic L_proxy", "B4": "B4 static L_proxy", "B2": "B2 random", "B3": "B3 shortest"}
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
T975 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262}


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def mean_sd(values):
    return (statistics.mean(values), statistics.stdev(values) if len(values) > 1 else float("nan"))


def mcnemar_exact(b, c):
    """Two-sided exact McNemar p on the discordant pairs b (only A right) and c (only B right)."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


# ---------------------------------------------------------------------------------------------- tables
def accuracy_table(runs, runs_dir):
    rows, per_problem = [], {}
    for split in ("dev", "test"):
        res, s = load_eval(runs_dir / "S0", split)
        if s:
            rows.append({"method": "B0", "seed": "", "checkpoint": 0, "split": split, "accuracy": s["accuracy"],
                         "lenient_accuracy": s["lenient_accuracy"], "format_compliance": s["format_compliance"],
                         "n_problems": s["n_problems"]})
            per_problem[("S0", 0, split)] = {r["problem_id"]: r["status"] == "valid" for r in res}
    for run in runs:
        for t in range(1, len(run.rounds()) + 1):
            for split in ("dev", "test"):
                res, s = load_eval(run.checkpoint_dir(t, runs_dir), split)
                if s is None:
                    print(f"[missing] {run.name} S{t} {split}")
                    continue
                rows.append({"method": run.method, "seed": run.seed, "checkpoint": t, "split": split,
                             "accuracy": s["accuracy"], "lenient_accuracy": s["lenient_accuracy"],
                             "format_compliance": s["format_compliance"], "n_problems": s["n_problems"]})
                per_problem[(run.name, t, split)] = {r["problem_id"]: r["status"] == "valid" for r in res}
    return rows, per_problem


def summarize_accuracy(rows):
    groups = defaultdict(list)
    for r in rows:
        groups[(r["method"], r["checkpoint"], r["split"])].append(r)
    out = []
    for (method, t, split), rs in sorted(groups.items(), key=lambda kv: (kv[0][2], kv[0][0], kv[0][1])):
        row = {"method": method, "checkpoint": t, "split": split, "n_seeds": len(rs)}
        for key in ("accuracy", "lenient_accuracy", "format_compliance"):
            m, sd = mean_sd([r[key] for r in rs])
            row[f"{key}_mean"], row[f"{key}_sd"] = m, sd
        out.append(row)
    return out


def b5_vs_b4(runs, per_problem, final_t):
    seeds = sorted({r.seed for r in runs if r.method == "B5"} & {r.seed for r in runs if r.method == "B4"})
    rows, diffs = [], []
    for seed in seeds:
        a = per_problem.get((f"B4_seed{seed}", final_t, "test"))
        b = per_problem.get((f"B5_seed{seed}", final_t, "test"))
        if not a or not b:
            print(f"[missing] B4/B5 seed {seed} S{final_t} test")
            continue
        ids = sorted(set(a) & set(b))
        only_b4 = sum(a[i] and not b[i] for i in ids)
        only_b5 = sum(b[i] and not a[i] for i in ids)
        acc4, acc5 = sum(a[i] for i in ids) / len(ids), sum(b[i] for i in ids) / len(ids)
        diffs.append(acc5 - acc4)
        rows.append({"seed": seed, "n_problems": len(ids), "B4_accuracy": acc4, "B5_accuracy": acc5,
                     "difference_B5_minus_B4": acc5 - acc4, "only_B4_correct": only_b4,
                     "only_B5_correct": only_b5, "mcnemar_exact_p": mcnemar_exact(only_b4, only_b5)})
    if len(diffs) >= 2:
        m, sd = mean_sd(diffs)
        half = T975[len(diffs) - 1] * sd / math.sqrt(len(diffs))
        rows.append({"seed": "mean", "difference_B5_minus_B4": m, "difference_sd": sd,
                     "ci95_low": m - half, "ci95_high": m + half, "n_seeds": len(diffs)})
    return rows


def learnability_table(runs, runs_dir):
    """Rows and {(run, t): {trajectory_id: (ell, l_proxy)}} from score_learnability.py outputs."""
    def load(ckpt_dir):
        path = ckpt_dir / "learnability.jsonl"
        if not path.exists():
            return None, None
        summary = json.loads(path.with_suffix(".summary.json").read_text(encoding="utf-8"))
        return {r["trajectory_id"]: (r["ell"], r["l_proxy"]) for r in read_jsonl(path)}, summary

    s0, s0_summary = load(runs_dir / "S0")
    if s0 is None:
        print("[missing] S0/learnability.jsonl: run score_learnability.py first")
        return [], {}
    scores, rows = {}, []
    for run in runs:
        prev = s0
        scores[(run.name, 0)] = s0
        for t in range(0, 3):
            cur, summary = (s0, s0_summary) if t == 0 else load(run.path / f"S{t}")
            if cur is None:
                break
            scores[(run.name, t)] = cur
            ids = sorted(cur)
            rho = None if t == 0 else spearman([prev[i][1] for i in ids], [cur[i][1] for i in ids])
            rows.append({"run": run.name, "method": run.method, "seed": run.seed, "checkpoint": t,
                         "n_reference": summary["n_reference"], "ell_star": summary["ell_star"],
                         "q1": summary["q1"], "q3": summary["q3"], "sigma": summary["sigma"],
                         "ell_mean": summary["ell"]["mean"], "l_proxy_mean": summary["l_proxy"]["mean"],
                         "l_proxy_sd": summary["l_proxy"]["sd"], "spearman_l_proxy_vs_previous": rho})
            prev = cur
    return rows, scores


def selection_table(runs, runs_dir):
    timing = defaultdict(float)
    for r in load_timing(runs_dir):
        timing[(Path(r["scope"]).name, r["step"])] += r["elapsed_seconds"]
    rows = []
    for run in runs:
        seen, prev = set(), set()
        for t in run.rounds():
            ts = run.train_set(t)
            cur = set(ts["trajectory_ids"])
            rows.append({
                "method": run.method, "seed": run.seed, "round": t, "n_selected": len(cur),
                "tokens_used": ts["tokens_used"], "budget": ts["beta_round_tokens"],
                "new": len(cur - seen), "retained": len(cur & prev), "readmitted": len((cur & seen) - prev),
                "dropped": len(prev - cur), "jaccard_previous": jaccard(cur, prev) if t else None,
                "select_seconds": timing.get((run.name, f"select_{t}")),
                "train_seconds": timing.get((run.name, f"train_{t}")),
                "nll_seconds_next": timing.get((run.name, f"nll_{run.name}_S{t + 1}")),
            })
            seen |= cur
            prev = cur
    return rows


# --------------------------------------------------------------------------------------------- figures

def style(ax, title=None):
    ax.set_facecolor(SURFACE)

    for side in ("top", "right"):
        ax.spines[side].set_visible(False)

    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
        ax.spines[side].set_linewidth(0.9)

    ax.tick_params(
        axis="both",
        colors=INK2,
        labelsize=10,
        length=3.5,
        width=0.8,
        pad=4,
    )

    ax.grid(
        axis="y",
        color=GRID,
        linewidth=0.75,
        alpha=0.85,
    )

    ax.set_axisbelow(True)

    if title:
        ax.set_title(
            title,
            color=INK,
            fontsize=12,
            fontweight="semibold",
            loc="left",
            pad=9,
        )




def fig_accuracy(plt, summary, out):
    from matplotlib.ticker import PercentFormatter

    fig, axes = plt.subplots(
        1,
        2,
        figsize=(11, 4.8),
        facecolor=SURFACE,
        sharey=True,
    )

    for ax, split in zip(axes, ("dev", "test")):
        style(ax, f"D_{split}")

        base = [
            r for r in summary
            if r["method"] == "B0" and r["split"] == split
        ]

        for m in METHODS:
            pts = sorted(
                (
                    r for r in summary
                    if r["method"] == m and r["split"] == split
                ),
                key=lambda r: r["checkpoint"],
            )

            if not pts:
                continue

            xs = (
                [0] + [r["checkpoint"] for r in pts]
                if base else
                [r["checkpoint"] for r in pts]
            )

            ys = (
                [base[0]["accuracy_mean"]]
                if base else []
            ) + [r["accuracy_mean"] for r in pts]

            sds = (
                [0.0] if base else []
            ) + [
                0.0 if math.isnan(r["accuracy_sd"]) else r["accuracy_sd"]
                for r in pts
            ]

            ax.plot(
                xs,
                ys,
                color=COLOR[m],
                linewidth=2.2,
                marker=MARKER[m],
                markersize=7,
                markeredgecolor=SURFACE,
                markeredgewidth=1.5,
                label=LABEL[m],
                zorder=4,
            )

            lower = [
                max(0.0, y - sd)
                for y, sd in zip(ys, sds)
            ]

            upper = [
                min(1.0, y + sd)
                for y, sd in zip(ys, sds)
            ]

            ax.fill_between(
                xs,
                lower,
                upper,
                color=COLOR[m],
                alpha=0.10,
                linewidth=0,
                zorder=2,
            )

        ax.set_xticks(
            [0, 1, 2, 3],
            ["S0\n(B0)", "S1", "S2", "S3"],
        )

        ax.set_xlim(-0.15, 3.15)
        ax.set_ylabel(
            "Strict exact-match accuracy",
            color=INK2,
            fontsize=10,
            labelpad=7,
        )

        ax.yaxis.set_major_formatter(
            PercentFormatter(xmax=1.0)
        )

        ax.margins(y=0.08)

    handles, labels = axes[0].get_legend_handles_labels()

    if handles:
        fig.legend(
            handles,
            labels,
            loc="lower center",
            ncol=4,
            frameon=False,
            fontsize=9.5,
            labelcolor=INK,
            bbox_to_anchor=(0.5, 0.005),
            columnspacing=1.5,
            handlelength=2.4,
        )

    fig.suptitle(
        "Student accuracy by checkpoint",
        color=INK,
        fontsize=13,
        fontweight="semibold",
        x=0.06,
        ha="left",
    )

    fig.text(
        0.06,
        0.925,
        "Mean Â± SD across three training seeds",
        fontsize=9.5,
        color=INK2,
    )

    fig.tight_layout(
        rect=(0.035, 0.13, 0.99, 0.89),
        w_pad=2.0,
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



def fig_learnability(plt, scores, runs, out):
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), facecolor=SURFACE, sharey=True)
    drawn = False
    for ax, m in zip(axes, ("B5", "B4")):
        style(ax, LABEL[m])
        data, labels = [], []
        for t in (0, 1, 2):
            vals = [v[0] for run in runs if run.method == m for v in scores.get((run.name, t), {}).values()]
            if t == 0:  # S_0 is shared: count it once, not once per seed
                first = next((run for run in runs if run.method == m and (run.name, 0) in scores), None)
                vals = [v[0] for v in scores[(first.name, 0)].values()] if first else []
            if vals:
                data.append(vals)
                labels.append(f"S{t}")
        if not data:
            continue
        drawn = True
        bp = ax.boxplot(data, widths=0.5, patch_artist=True, showfliers=False,
                        medianprops={"color": INK, "linewidth": 1.5},
                        whiskerprops={"color": INK2}, capprops={"color": INK2})
        for patch in bp["boxes"]:
            patch.set_facecolor(COLOR[m])
            patch.set_alpha(0.35)
            patch.set_edgecolor(COLOR[m])
        ax.set_xticks(range(1, len(labels) + 1), labels)
        ax.set_ylabel("length-normalized NLL â„“", color=INK2, fontsize=9)
    if drawn:
        fig.suptitle("Learnability distribution across checkpoints (all seeds pooled, whiskers 1.5 IQR)",
                     color=INK, fontsize=12, x=0.01, ha="left")
        fig.tight_layout(rect=(0, 0, 1, 0.94))
        fig.savefig(out, dpi=200, facecolor=SURFACE)
    plt.close(fig)
    return drawn



def fig_selection(plt, runs, sel_rows, out):
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
    # Reserve whitespace between the panel title and the bar columns.
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
        bbox_to_anchor=(0.99, 0.92),
        ncol=3,
        borderaxespad=0.0,
        columnspacing=1.0,
        handlelength=1.5,
    )

    fig.suptitle(
        "B5 selection dynamics",
        color=INK,
        fontsize=13,
        fontweight="bold",
        x=0.06,
        y=0.985,
        ha="left",
    )

    fig.text(
        0.06,
        0.88,
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

def fig_final(plt, acc_rows, final_t, out):
    from matplotlib.ticker import PercentFormatter
    fig, ax = plt.subplots(figsize=(6, 4), facecolor=SURFACE)
    style(ax, f"D_test accuracy at S{final_t} (equal token budget)")
    base = [r for r in acc_rows if r["method"] == "B0" and r["split"] == "test"]
    names = (["B0"] if base else []) + [m for m in METHODS
                                         if any(r["method"] == m and r["checkpoint"] == final_t and r["split"] == "test"
                                                for r in acc_rows)]
    for x, m in enumerate(names):
        vals = [r["accuracy"] for r in (base if m == "B0" else acc_rows)
                if m == "B0" or (r["method"] == m and r["checkpoint"] == final_t and r["split"] == "test")]
        color = INK2 if m == "B0" else COLOR[m]
        ax.scatter([x] * len(vals), vals, color=color, s=28, alpha=0.6, zorder=3, edgecolor=SURFACE)
        mean, sd = mean_sd(vals)
        ax.errorbar([x + 0.18], [mean], yerr=[0 if math.isnan(sd) else sd], fmt=MARKER.get(m, "o"), color=color,
                    markersize=8, capsize=4, linewidth=2, zorder=4)
        ax.annotate(f"{mean * 100:.1f}%", (x + 0.3, mean), color=INK, fontsize=9, va="center")
    ax.set_xticks(range(len(names)), ["B0\n(S0)" if m == "B0" else m for m in names])
    ax.set_xlim(-0.5, len(names) - 0.2)
    ax.set_ylabel("Strict accuracy (%)", color=INK2, fontsize=9)
    ax.yaxis.set_major_formatter(PercentFormatter(xmax=1.0))
    fig.tight_layout()
    fig.savefig(out, dpi=200, facecolor=SURFACE)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs_dir", type=Path)
    ap.add_argument("--out", type=Path, default=Path("reports/task7/main_results"))
    ap.add_argument("--final-checkpoint", type=int, default=3)
    args = ap.parse_args()

    runs = [r for r in discover(args.runs_dir) if r.method in METHODS]
    tables = args.out / "tables"
    acc_rows, per_problem = accuracy_table(runs, args.runs_dir)
    summary = summarize_accuracy(acc_rows)
    sel_rows = selection_table(runs, args.runs_dir)
    learn_rows, scores = learnability_table(runs, args.runs_dir)
    write_csv(tables / "accuracy.csv", acc_rows)
    write_csv(tables / "accuracy_summary.csv", summary)
    write_csv(tables / "b5_vs_b4.csv", b5_vs_b4(runs, per_problem, args.final_checkpoint))
    write_csv(tables / "learnability.csv", learn_rows)
    write_csv(tables / "selection.csv", sel_rows)
    print(f"tables -> {tables}")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed: figures skipped")
        return
    figs = args.out / "figures"
    figs.mkdir(parents=True, exist_ok=True)
    fig_accuracy(plt, summary, figs / "fig1_accuracy_curve.png")
    if not fig_learnability(plt, scores, runs, figs / "fig2_learnability.png"):
        print("[skip] fig2: no learnability.jsonl")
    if not fig_selection(plt, runs, sel_rows, figs / "fig3_selection_dynamics.png"):
        print("[skip] fig3: B5 needs at least two rounds")
    fig_final(plt, acc_rows, args.final_checkpoint, figs / "fig4_final_accuracy.png")
    print(f"figures -> {figs}")


if __name__ == "__main__":
    main()

