#!/usr/bin/env python3
"""
Hypothesis H and the noise tolerance epsilon (analysis_plan.md section 7, T7-4, T7-6, T7-7, T7-8).
Reads the learnability.jsonl files written by score_learnability.py; no GPU. Needs numpy.

Repeated measurement [T7-6]: the B4 runs of the training seeds (same data, different seed). The script
checks that their train sets are identical. U(t -> t+1) = trajectories not trained in B4 up to S_{t+1}.

H test [T7-7], for S_0 -> S_1 and S_1 -> S_2, on U:
  rho_change^a = Spearman(L | S_t^a, L | S_{t+1}^a)             (S_0 is shared by all seeds)
  rho_noise^a  = mean over b != a of Spearman(L | S_{t+1}^a, L | S_{t+1}^b)
  Delta^a      = rho_noise^a - rho_change^a
  Bootstrap over problem_id clusters, 10,000 resamples, seed 363636, the same resamples for every seed and
  scale. H is supported for a pair when EVERY seed has a one-sided 95% lower bound (5th percentile) of
  Delta^a > 0 AND Delta^a >= 0.05 [T7-4]. Decision scale: L_proxy. The same numbers on ell (rank of the raw
  length-normalized NLL) are reported; if L_proxy passes and ell does not, the conclusion is only "the ranking
  by distance to the median changes" [T7-7].
epsilon [T7-6]: 95th percentile of |L(S_1^a) - L(S_1^b)| on U(0 -> 1), pooled over seed pairs, with a
  problem-cluster bootstrap 95% CI and 2.77 s_w for comparison (s_w^2 = mean over trajectories of the variance
  across seeds). For each pair and seed: share of U with |L(S_{t+1}) - L(S_t)| > epsilon, against 5%.
Sensitivity, exploratory: sqrt(rho_noise) benchmark at S_0 -> S_1, Steiger's Z for the dependent
  correlations (common variable L | S_{t+1}^a), U without problems that had any trajectory trained, and the
  same analysis on B2 when its S_1/S_2 NLL exist (--b2-nll runs).
Selection noise [T7-8]: mean pairwise Jaccard of the B5 round-2 train sets across seeds, against the random
  expectation k / (2N - k).

Usage (from experiments/week2September/manual/):
  python scripts/score_learnability.py runs/main
  python scripts/h_test.py runs/main --out reports/task7/main_results
Outputs: <out>/h_test.json, <out>/tables/h_test.csv, <out>/figures/fig5_h_test.png (needs matplotlib).
"""
import argparse
import csv
import itertools
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_layout import discover, jaccard  # noqa: E402
from student_common import read_jsonl  # noqa: E402

N_BOOT, BOOT_SEED, DELTA_MIN, ALPHA_ONE_SIDED = 10_000, 363636, 0.05, 0.05
SCALES = ("l_proxy", "ell")


def avg_rank(x):
    order = np.argsort(x, kind="mergesort")
    sx = x[order]
    new = np.r_[True, sx[1:] != sx[:-1]]
    starts = np.flatnonzero(new)
    ends = np.r_[starts[1:], len(x)]
    ranks = np.empty(len(x))
    ranks[order] = ((starts + ends - 1) / 2 + 1)[np.cumsum(new) - 1]
    return ranks


def spearman(x, y):
    return float(np.corrcoef(avg_rank(x), avg_rank(y))[0, 1])


def steiger_z(r_jk, r_jh, r_kh, n):
    """Steiger (1980) Z for H0: rho_jk = rho_jh (common variable j), pooled r-bar; two-sided p."""
    rm = (r_jk + r_jh) / 2
    c = (r_kh * (1 - 2 * rm ** 2) - 0.5 * rm ** 2 * (1 - 2 * rm ** 2 - r_kh ** 2)) / (1 - rm ** 2) ** 2
    z = (math.atanh(r_jk) - math.atanh(r_jh)) * math.sqrt(n - 3) / math.sqrt(2 - 2 * c)
    return z, math.erfc(abs(z) / math.sqrt(2))


def load_scores(path):
    rows = read_jsonl(path)
    return {r["trajectory_id"]: (r["problem_id"], r["ell"], r["l_proxy"]) for r in rows}


class Panel:
    """Scores of one method across seeds: S_0 (shared), S_1, S_2 per seed; trained sets per round."""

    def __init__(self, runs_dir, method):
        self.method = method
        self.runs = [r for r in discover(runs_dir) if r.method == method]
        s0 = Path(runs_dir) / "S0" / "learnability.jsonl"
        self.s0 = load_scores(s0) if s0.exists() else None
        self.scores, self.trained = {}, {}
        for run in self.runs:
            for t in (1, 2):
                p = run.path / f"S{t}" / "learnability.jsonl"
                if p.exists():
                    self.scores[(run.seed, t)] = load_scores(p)
            self.trained[run.seed] = [set(run.train_set(t)["trajectory_ids"]) for t in run.rounds()]

    def seeds_with(self, t):
        return sorted(s for s in self.trained if (s, t) in self.scores)

    def at(self, seed, t):
        return self.s0 if t == 0 else self.scores[(seed, t)]


def bootstrap_index(groups, rng):
    """Positions of a problem-cluster resample: problems drawn with replacement, all their trajectories kept."""
    n_prob = len(groups)
    counts = np.bincount(rng.integers(0, n_prob, n_prob), minlength=n_prob)
    return np.concatenate([np.repeat(g, c) for g, c in zip(groups, counts) if c])


def analyse_pair(panel, t, seeds, U, n_boot, label):
    """Point estimates and bootstrap of Delta^a on both scales for S_t -> S_{t+1}."""
    ids = sorted(U)
    prob = [panel.at(seeds[0], t + 1)[i][0] for i in ids]
    uniq = {p: k for k, p in enumerate(sorted(set(prob)))}
    groups = [[] for _ in uniq]
    for pos, p in enumerate(prob):
        groups[uniq[p]].append(pos)
    groups = [np.array(g) for g in groups]
    col = {"ell": 1, "l_proxy": 2}
    vec = {(scale, s, tt): np.array([panel.at(s, tt)[i][col[scale]] for i in ids])
           for scale in SCALES for s in seeds for tt in (t, t + 1)}

    def deltas(idx):
        out = {}
        for scale in SCALES:
            r = {(s, tt): avg_rank(vec[(scale, s, tt)][idx]) for s in seeds for tt in (t, t + 1)}
            noise = {}
            for a, b in itertools.combinations(seeds, 2):
                noise[(a, b)] = noise[(b, a)] = np.corrcoef(r[(a, t + 1)], r[(b, t + 1)])[0, 1]
            for a in seeds:
                change = np.corrcoef(r[(a, t)], r[(a, t + 1)])[0, 1]
                rho_noise = np.mean([noise[(a, b)] for b in seeds if b != a])
                out[(scale, a)] = (rho_noise - change, rho_noise, change)
        return out

    full = np.arange(len(ids))
    point = deltas(full)
    rng = np.random.default_rng(BOOT_SEED)
    boot = {k: np.empty(n_boot) for k in point}
    for i in range(n_boot):
        d = deltas(bootstrap_index(groups, rng))
        for k in point:
            boot[k][i] = d[k][0]
    rows = []
    def pct(scale, a, q):
        return float(np.percentile(boot[(scale, a)], q)) if n_boot else float("nan")

    for scale in SCALES:
        for a in seeds:
            delta, rho_noise, change = point[(scale, a)]
            lb = pct(scale, a, 100 * ALPHA_ONE_SIDED)
            row = {"analysis": label, "pair": f"S{t}->S{t + 1}", "scale": scale, "seed": a, "n_U": len(ids),
                   "n_problems": len(groups), "rho_change": change, "rho_noise": rho_noise, "delta": delta,
                   "delta_lb95_one_sided": lb, "delta_ci95_low": pct(scale, a, 2.5),
                   "delta_ci95_high": pct(scale, a, 97.5),
                   "passes": bool(lb > 0 and delta >= DELTA_MIN)}
            if t == 0:
                row["sqrt_rho_noise"] = math.sqrt(max(rho_noise, 0))
                row["change_below_sqrt_noise"] = bool(change < row["sqrt_rho_noise"])
            zs = []
            for b in seeds:
                if b == a:
                    continue
                r_kh = spearman(vec[(scale, a, t)], vec[(scale, b, t + 1)])
                r_ab = spearman(vec[(scale, a, t + 1)], vec[(scale, b, t + 1)])
                zs.append(steiger_z(r_ab, change, r_kh, len(ids)))
            row["steiger_z_min"] = min(z for z, _ in zs)
            row["steiger_p_max"] = max(p for _, p in zs)
            rows.append(row)
    return rows


def run_method(panel, n_boot, label):
    results, decisions, notes = [], {}, []
    seeds_all = sorted(panel.trained)
    if panel.s0 is None:
        return results, decisions, [f"{label}: S0/learnability.jsonl missing (run score_learnability.py)"]
    if len(seeds_all) >= 2:
        same = all(panel.trained[s] == panel.trained[seeds_all[0]] for s in seeds_all)
        notes.append(f"{label}: train sets identical across seeds: {same}")
        if not same and panel.method == "B4":
            notes.append("B4 train sets differ across seeds: the repeated-measurement design of T7-6 does not hold")
    for t in (0, 1):
        seeds = [s for s in panel.seeds_with(t + 1) if t == 0 or (s, t) in panel.scores]
        if len(seeds) < 2:
            notes.append(f"{label} S{t}->S{t + 1}: {len(seeds)} seed(s) with scores, need >= 2")
            continue
        trained = set().union(*(panel.trained[seeds[0]][: t + 1]))
        universe = set(panel.at(seeds[0], t + 1))
        U = universe - trained
        rows = analyse_pair(panel, t, seeds, U, n_boot, label)
        results += rows
        lp = [r for r in rows if r["scale"] == "l_proxy"]
        el = [r for r in rows if r["scale"] == "ell"]
        decisions[f"S{t}->S{t + 1}"] = {"seeds": seeds, "H_supported_on_L_proxy": all(r["passes"] for r in lp),
                                        "passes_on_ell": all(r["passes"] for r in el)}
        if label == panel.method:  # sensitivity: drop problems that had any trajectory trained
            prob = {i: panel.at(seeds[0], t + 1)[i][0] for i in universe}
            touched = {prob[i] for i in trained}
            U2 = {i for i in U if prob[i] not in touched}
            results += analyse_pair(panel, t, seeds, U2, 0 if n_boot == 0 else min(n_boot, 1000),
                                    f"{label} (U without trained problems, 1000 resamples)")
    return results, decisions, notes


def epsilon(panel, n_boot):
    seeds = panel.seeds_with(1)
    if len(seeds) < 2 or panel.s0 is None:
        return None
    U = sorted(set(panel.at(seeds[0], 1)) - panel.trained[seeds[0]][0])
    L = np.array([[panel.at(s, 1)[i][2] for i in U] for s in seeds])
    diffs = np.stack([np.abs(L[a] - L[b]) for a, b in itertools.combinations(range(len(seeds)), 2)])
    eps = float(np.percentile(diffs, 95))
    s_w = float(np.sqrt(np.mean(np.var(L, axis=0, ddof=1))))
    prob = [panel.at(seeds[0], 1)[i][0] for i in U]
    uniq = {p: k for k, p in enumerate(sorted(set(prob)))}
    groups = [[] for _ in uniq]
    for pos, p in enumerate(prob):
        groups[uniq[p]].append(pos)
    groups = [np.array(g) for g in groups]
    rng = np.random.default_rng(BOOT_SEED)
    boot = [float(np.percentile(diffs[:, bootstrap_index(groups, rng)], 95)) for _ in range(n_boot)]
    exceed = []
    for t in (0, 1):
        for s in panel.seeds_with(t + 1):
            if t == 1 and (s, 1) not in panel.scores:
                continue
            Ut = sorted(set(panel.at(s, t + 1)) - set().union(*panel.trained[s][: t + 1]))
            change = np.array([abs(panel.at(s, t + 1)[i][2] - panel.at(s, t)[i][2]) for i in Ut])
            exceed.append({"pair": f"S{t}->S{t + 1}", "seed": s, "n_U": len(Ut),
                           "share_change_above_epsilon": float(np.mean(change > eps)), "reference_share": 0.05})
    return {"seeds": seeds, "n_U": len(U), "epsilon": eps,
            "epsilon_ci95": [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))] if boot else None,
            "s_w": s_w, "epsilon_normal_2_77_s_w": 2.77 * s_w, "exceed": exceed}


def selection_jaccard(runs_dir, n_pool):
    b5 = [r for r in discover(runs_dir) if r.method == "B5" and len(r.rounds()) >= 3]
    if len(b5) < 2:
        return None
    sets = {r.seed: set(r.train_set(2)["trajectory_ids"]) for r in b5}
    pairs = {f"{a}-{b}": jaccard(sets[a], sets[b]) for a, b in itertools.combinations(sorted(sets), 2)}
    k = float(np.mean([len(s) for s in sets.values()]))
    return {"round": 2, "pairwise": pairs, "mean": float(np.mean(list(pairs.values()))),
            "random_expectation": k / (2 * n_pool - k), "n_pool": n_pool, "mean_selected": k}


def figure(rows, out):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed: figure skipped")
        return
    main = [r for r in rows if r["analysis"] == "B4"]
    pairs = sorted({r["pair"] for r in main})
    if not pairs:
        return
    ink, ink2, grid, surface = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
    color = {"l_proxy": "#2a78d6", "ell": "#eb6834"}
    label = {"l_proxy": "L_proxy (decision scale)", "ell": "ℓ rank"}
    fig, axes = plt.subplots(1, len(pairs), figsize=(5 * len(pairs), 4), facecolor=surface, squeeze=False)
    for ax, pair in zip(axes[0], pairs):
        ax.set_facecolor(surface)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        ax.grid(axis="y", color=grid, linewidth=0.8)
        ax.set_axisbelow(True)
        ax.axhline(0, color=ink2, linewidth=1)
        ax.axhline(DELTA_MIN, color=ink2, linewidth=1, linestyle="--")
        ax.annotate("Δ = 0.05", (0.01, DELTA_MIN), xycoords=("axes fraction", "data"), color=ink2, fontsize=8,
                    va="bottom")
        seeds = sorted({r["seed"] for r in main if r["pair"] == pair})
        for k, scale in enumerate(SCALES):
            pts = [next(r for r in main if r["pair"] == pair and r["scale"] == scale and r["seed"] == s) for s in seeds]
            xs = [i + (k - 0.5) * 0.25 for i in range(len(seeds))]
            ys = [p["delta"] for p in pts]
            lo = [p["delta"] - p["delta_lb95_one_sided"] for p in pts]
            ax.errorbar(xs, ys, yerr=[lo, [0] * len(pts)], fmt="o" if scale == "l_proxy" else "s", color=color[scale],
                        markersize=7, capsize=4, linewidth=2, label=label[scale])
        ax.set_xticks(range(len(seeds)), [f"seed {s}" for s in seeds])
        ax.tick_params(colors=ink2, labelsize=9)
        ax.set_title(f"B4, {pair}", color=ink, fontsize=11, loc="left")
        ax.set_ylabel("Δ = ρ_noise − ρ_change", color=ink2, fontsize=9)
    axes[0][0].legend(frameon=False, fontsize=9, labelcolor=ink)
    fig.suptitle("Hypothesis H: point estimate and one-sided 95% lower bound (problem bootstrap)", color=ink,
                 fontsize=11, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=200, facecolor=surface)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs_dir", type=Path)
    ap.add_argument("--out", type=Path, default=Path("reports/task7/main_results"))
    ap.add_argument("--n-boot", type=int, default=N_BOOT, help="resamples (10,000 by the analysis plan)")
    args = ap.parse_args()

    b4 = Panel(args.runs_dir, "B4")
    rows, decisions, notes = run_method(b4, args.n_boot, "B4")
    b2 = Panel(args.runs_dir, "B2")
    if b2.scores:
        r2, d2, n2 = run_method(b2, min(args.n_boot, 1000), "B2 (exploratory, 1000 resamples)")
        rows += r2
        notes += n2
        decisions["B2_exploratory"] = d2
    n_pool = len(b4.s0) if b4.s0 else 0
    report = {"design": {"n_boot": args.n_boot, "boot_seed": BOOT_SEED, "delta_min": DELTA_MIN,
                         "lower_bound": "5th percentile (one-sided 95%)", "decision_scale": "l_proxy"},
              "decisions": decisions, "epsilon": epsilon(b4, args.n_boot),
              "selection_jaccard_B5_round2": selection_jaccard(args.runs_dir, n_pool), "notes": notes, "rows": rows}
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "h_test.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if rows:
        (args.out / "tables").mkdir(exist_ok=True)
        fields = list(dict.fromkeys(k for r in rows for k in r))
        with (args.out / "tables" / "h_test.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
        figure(rows, args.out / "figures" / "fig5_h_test.png")
    for n in notes:
        print("note:", n)
    for pair, d in decisions.items():
        print(pair, d)
    if report["epsilon"]:
        e = report["epsilon"]
        print(f"epsilon {e['epsilon']:.4f} CI {e['epsilon_ci95']}  2.77 s_w {e['epsilon_normal_2_77_s_w']:.4f}")
    print(f"-> {args.out / 'h_test.json'}")


if __name__ == "__main__":
    main()
