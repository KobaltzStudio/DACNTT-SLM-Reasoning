#!/usr/bin/env python3
"""
Proposal 1 analyses on the Proposal 2 runs (KeHoach_PhanCong 4.4): mastery by capability at every checkpoint,
and the capability make-up of the selected trajectories. Descriptive only; no GPU, no torch.

Mastery M(c, S_t) = correct_c / total_c on the D_dev problems that have manual capability labels (85
supplement problems). A problem with several capabilities counts once for each of them. Every value comes
with its support n and a Wilson 95% interval; with n this small (ratio especially) differences between
methods are not tests. D_test has no manual labels and is not used here.

Label sets (choose the one the group fixes; both can be written for comparison, the paper reports one):
  v2       data/supplement/supplement_annotations_v2.jsonl (what eval_student.py uses)
  vfinal   data/gold_vfinal/supplement_annotations_vfinal.jsonl (D3 Gold vFinal)

Selection make-up: share of the selected trajectories of each method, seed and round whose capability set
C(tau) (rules v2 on the Teacher output, pool field "capabilities", T6-6) contains c, against the same share
in the whole eligible pool.

Usage (from experiments/week2September/manual/):
  python scripts/capability_mastery.py runs/main --labels vfinal --out reports/task7/main_results
  python scripts/capability_mastery.py runs/main --labels v2 vfinal
Outputs (<out>/tables, <out>/figures):
  capability_mastery_<labels>.csv, capability_mastery_summary_<labels>.csv, fig6_capability_mastery_<labels>.png
  selection_capabilities.csv, fig7_selection_capabilities.png
"""
import argparse
import csv
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_layout import discover, load_eval  # noqa: E402
from student_common import DEV_IDS, MANUAL_DIR, POOL_VERIFIED, read_jsonl  # noqa: E402

LABEL_FILES = {
    "v2": MANUAL_DIR / "data" / "supplement" / "supplement_annotations_v2.jsonl",
    "vfinal": MANUAL_DIR / "data" / "gold_vfinal" / "supplement_annotations_vfinal.jsonl",
}
CAPABILITIES = ("addition", "subtraction", "multiplication", "division", "fraction", "percentage", "ratio")
METHODS = ("B5", "B4", "B2", "B3")
COLOR = {"B5": "#2a78d6", "B4": "#eb6834", "B2": "#1baf7a", "B3": "#eda100", "B0": "#52514e"}
MARKER = {"B5": "o", "B4": "s", "B2": "^", "B3": "D"}
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"


def load_labels(name):
    dev = set(DEV_IDS.read_text(encoding="utf-8").split())
    rows = read_jsonl(LABEL_FILES[name])
    outside = [r["problem_id"] for r in rows if r["problem_id"] not in dev]
    if outside:
        raise ValueError(f"{LABEL_FILES[name]}: {len(outside)} problems outside D_dev")
    return {r["problem_id"]: set(r["capabilities_manual"]) for r in rows}


def wilson(k, n, z=1.96):
    if n == 0:
        return float("nan"), float("nan")
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return centre - half, centre + half


def mastery_rows(eval_rows, labels, method, seed, t):
    correct = {r["problem_id"]: r["status"] == "valid" for r in eval_rows}
    out = []
    for c in CAPABILITIES:
        ids = [p for p, caps in labels.items() if c in caps and p in correct]
        k = sum(correct[p] for p in ids)
        lo, hi = wilson(k, len(ids))
        out.append({"method": method, "seed": seed, "checkpoint": t, "capability": c, "n_support": len(ids),
                    "n_correct": k, "mastery": k / len(ids) if ids else float("nan"), "ci95_low": lo, "ci95_high": hi,
                    "deficit": 1 - k / len(ids) if ids else float("nan")})
    return out


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(k for r in rows for k in r))
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def mastery_tables(runs, runs_dir, labels):
    rows = []
    s0, _ = load_eval(Path(runs_dir) / "S0", "dev")
    if s0:
        rows += mastery_rows(s0, labels, "B0", "", 0)
    for run in runs:
        for t in range(1, len(run.rounds()) + 1):
            res, _ = load_eval(run.checkpoint_dir(t, runs_dir), "dev")
            if res is None:
                print(f"[missing] {run.name} S{t} dev")
                continue
            rows += mastery_rows(res, labels, run.method, run.seed, t)
    groups = defaultdict(list)
    for r in rows:
        groups[(r["method"], r["checkpoint"], r["capability"])].append(r)
    summary = []
    for (m, t, c), rs in groups.items():
        vals = [r["mastery"] for r in rs if not math.isnan(r["mastery"])]
        summary.append({"method": m, "checkpoint": t, "capability": c, "n_support": rs[0]["n_support"],
                        "n_seeds": len(rs), "mastery_mean": statistics.mean(vals) if vals else float("nan"),
                        "mastery_sd": statistics.stdev(vals) if len(vals) > 1 else float("nan")})
    return rows, summary


def selection_rows(runs):
    pool = {r["trajectory_id"]: set(r.get("capabilities") or []) for r in read_jsonl(POOL_VERIFIED)}
    pool_share = {c: sum(c in caps for caps in pool.values()) / len(pool) for c in CAPABILITIES}
    rows = []
    for run in runs:
        for t in run.rounds():
            ids = run.train_set(t)["trajectory_ids"]
            for c in CAPABILITIES:
                k = sum(c in pool.get(i, set()) for i in ids)
                rows.append({"method": run.method, "seed": run.seed, "round": t, "capability": c,
                             "n_selected": len(ids), "n_with_capability": k, "share": k / len(ids) if ids else 0,
                             "pool_share": pool_share[c]})
    return rows, pool_share



def style(ax, title):
    ax.set_facecolor(SURFACE)

    for side in ("top", "right"):
        ax.spines[side].set_visible(False)

    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
        ax.spines[side].set_linewidth(0.9)

    ax.grid(
        axis="y",
        color=GRID,
        linewidth=0.75,
        alpha=0.85,
    )

    ax.set_axisbelow(True)

    ax.tick_params(
        axis="both",
        colors=INK2,
        labelsize=9.5,
        length=3,
        width=0.8,
        pad=4,
    )

    ax.set_title(
        title,
        color=INK,
        fontsize=11,
        fontweight="semibold",
        loc="left",
        pad=8,
    )




def fig_mastery(plt, summary, out, label_name):
    from matplotlib.ticker import PercentFormatter

    # 7 capability panels + 1 legend panel.
    # Keep the 4 + 3 layout, but enlarge each panel.
    fig, axes = plt.subplots(
        2,
        4,
        figsize=(14, 7.5),
        facecolor=SURFACE,
        sharey=True,
    )

    base = {
        r["capability"]: r
        for r in summary
        if r["method"] == "B0"
    }

    for ax, c in zip(axes.flat, CAPABILITIES):
        n = (
            base[c]["n_support"]
            if c in base
            else next(
                (
                    r["n_support"]
                    for r in summary
                    if r["capability"] == c
                ),
                0,
            )
        )

        style(ax, f"{c.capitalize()} (n = {n})")

        for m in METHODS:
            pts = sorted(
                (
                    r for r in summary
                    if r["method"] == m
                    and r["capability"] == c
                ),
                key=lambda r: r["checkpoint"],
            )

            if not pts:
                continue

            xs = (
                [0] + [r["checkpoint"] for r in pts]
                if c in base
                else [r["checkpoint"] for r in pts]
            )

            ys = (
                [base[c]["mastery_mean"]]
                if c in base
                else []
            ) + [
                r["mastery_mean"] for r in pts
            ]

            # SD across seeds. S0 is the shared baseline,
            # so it has no across-seed SD.
            sds = (
                [0.0] if c in base else []
            ) + [
                (
                    0.0
                    if math.isnan(r["mastery_sd"])
                    else r["mastery_sd"]
                )
                for r in pts
            ]

            ax.plot(
                xs,
                ys,
                color=COLOR[m],
                marker=MARKER[m],
                markersize=5.5,
                linewidth=1.9,
                label=m,
                markeredgecolor=SURFACE,
                markeredgewidth=1.0,
                zorder=4,
            )

            # Show seed variability without changing the mean values.
            ax.errorbar(
                xs,
                ys,
                yerr=sds,
                fmt="none",
                ecolor=COLOR[m],
                elinewidth=1.0,
                capsize=2.5,
                alpha=0.65,
                zorder=3,
            )

        ax.set_xticks(
            [0, 1, 2, 3],
            ["S0", "S1", "S2", "S3"],
        )

        ax.set_xlim(-0.15, 3.15)
        ax.set_ylim(0, 1.0)

        ax.yaxis.set_major_formatter(
            PercentFormatter(xmax=1.0)
        )

        ax.set_yticks(
            [0, 0.25, 0.50, 0.75, 1.0]
        )

        ax.set_ylabel(
            "Mastery",
            fontsize=9.5,
            color=INK2,
        )

    # The eighth panel is reserved for the shared legend.
    legend_ax = axes.flat[-1]
    legend_ax.axis("off")

    handles, labels = axes.flat[0].get_legend_handles_labels()

    if handles:
        legend_ax.legend(
            handles,
            labels,
            loc="center",
            frameon=False,
            fontsize=11,
            labelcolor=INK,
            title="Training method",
            title_fontsize=10,
        )

    fig.suptitle(
        "Capability mastery across checkpoints",
        color=INK,
        fontsize=14,
        fontweight="semibold",
        x=0.055,
        ha="left",
    )

    fig.text(
        0.055,
        0.925,
        (
            f"Gold {label_name} labels | "
            "Mean ± SD across training seeds | "
            "Descriptive analysis"
        ),
        fontsize=9.5,
        color=INK2,
    )

    fig.tight_layout(
        rect=(0.025, 0.035, 0.99, 0.89),
        w_pad=1.8,
        h_pad=2.0,
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



def fig_selection(plt, rows, pool_share, out):
    fig, ax = plt.subplots(figsize=(10, 4), facecolor=SURFACE)
    style(ax, "Capability make-up of selected trajectories (mean over seeds and rounds) vs whole pool")
    methods = [m for m in METHODS if any(r["method"] == m for r in rows)]
    width = 0.8 / max(len(methods), 1)
    for k, m in enumerate(methods):
        xs, ys = [], []
        for i, c in enumerate(CAPABILITIES):
            vals = [r["share"] for r in rows if r["method"] == m and r["capability"] == c]
            xs.append(i - 0.4 + width * (k + 0.5))
            ys.append(statistics.mean(vals))
        ax.bar(xs, ys, width=width, color=COLOR[m], label=m, edgecolor=SURFACE, linewidth=1)
    for i, c in enumerate(CAPABILITIES):
        ax.hlines(pool_share[c], i - 0.45, i + 0.45, color=INK, linewidth=1.5, label="pool" if i == 0 else None)
    ax.set_xticks(range(len(CAPABILITIES)), CAPABILITIES)
    ax.set_ylabel("share of selected trajectories", color=INK2, fontsize=9)
    ax.legend(frameon=False, fontsize=9, labelcolor=INK, ncol=len(methods) + 1, loc="upper center",
              bbox_to_anchor=(0.5, -0.12))
    fig.tight_layout()
    fig.savefig(out, dpi=200, facecolor=SURFACE)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs_dir", type=Path)
    ap.add_argument("--labels", nargs="+", choices=sorted(LABEL_FILES), required=True)
    ap.add_argument("--out", type=Path, default=Path("reports/task7/main_results"))
    args = ap.parse_args()

    runs = [r for r in discover(args.runs_dir) if r.method in METHODS]
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        plt = None
        print("matplotlib not installed: figures skipped")
    (args.out / "figures").mkdir(parents=True, exist_ok=True)
    for name in args.labels:
        labels = load_labels(name)
        rows, summary = mastery_tables(runs, args.runs_dir, labels)
        write_csv(args.out / "tables" / f"capability_mastery_{name}.csv", rows)
        write_csv(args.out / "tables" / f"capability_mastery_summary_{name}.csv", summary)
        support = {c: sum(c in caps for caps in labels.values()) for c in CAPABILITIES}
        print(f"labels {name}: {len(labels)} problems, support {support}")
        if plt and summary:
            fig_mastery(plt, summary, args.out / "figures" / f"fig6_capability_mastery_{name}.png", name)
    sel, pool_share = selection_rows(runs)
    if sel:
        write_csv(args.out / "tables" / "selection_capabilities.csv", sel)
        if plt:
            fig_selection(plt, sel, pool_share, args.out / "figures" / "fig7_selection_capabilities.png")
    print(f"-> {args.out}")


if __name__ == "__main__":
    main()
