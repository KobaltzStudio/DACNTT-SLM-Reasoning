#!/usr/bin/env python3
"""Build seven descriptive seed-13 figures from complete observed inputs."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import io
from itertools import combinations
import json
import math
from pathlib import Path
import tempfile

from build_capability_learning_dynamics import CAPABILITIES, gold_inputs, validate_one
from p1p2_artifact_manager import publish_json_no_overwrite, publish_pair_no_overwrite
from p1p2_controller import read_json, read_jsonl, sha256
from select_checkpoint_on_dev import METHODS, score, verified_prediction

VERSION = "p1p2.descriptive-figures.v2.1"
NAMES = ("selection_jaccard", "selection_composition", "student_accuracy", "capability_mastery",
         "capability_makeup", "learnability_distribution", "p1_capability_learning_curves")
P1 = ("P1-DEFICIT", "P1P2")
OUTPUT = Path("reports/p1p2_integration/final_validation/figures")
COLORS = dict(zip(METHODS, ("#2166ac", "#b2182b", "#238b45", "#6a51a3")))


def selection_rows(root, method, round_no, inputs):
    historical = method in ("B4", "B5")
    namespace = "main" if historical else "p1p2_integration"
    target = root / "runs" / namespace / f"{method}_seed13" / f"round_{round_no-int(historical):03d}"
    train_path, log_path = target / "train_set.json", target / "selection_log.jsonl"
    train = read_json(train_path)
    rows = [row for row in read_jsonl(log_path) if row.get("record_type") == "selection"]
    identifiers = [row["trajectory_id"] for row in rows]
    selected = {row["trajectory_id"] for row in rows if row.get("selected") is True}
    train_ids = train["trajectory_ids"]
    if (len(identifiers) != len(set(identifiers)) or not selected or selected != set(train_ids)
            or len(train_ids) != len(selected) or train.get("method") != method
            or train.get("training_seed") != 13 or train.get("round") != round_no - int(historical)
            or any(row.get("method") != method or row.get("round") != round_no - int(historical)
                   or row.get("seed", row.get("training_seed")) != 13 for row in rows)):
        raise ValueError(f"Selection identity or coverage mismatch: {target}")
    inputs.update({str(path): sha256(path) for path in (train_path, log_path)})
    return selected, rows


def selection_composition(rounds):
    seen, previous, output = set(), set(), []
    for current in rounds:
        output.append({"new": len(current - seen), "retained": len(current & previous),
                       "readmitted": len((current & seen) - previous)})
        seen |= current
        previous = current
    return output


def observed(getter, missing, scope):
    try:
        return getter()
    except FileNotFoundError as exc:
        if missing is None:
            raise
        missing[scope] = str(exc)
        return None


def mastery_data(root, methods, inputs, missing=None):
    gold = gold_inputs(root)
    rows = []
    for method, checkpoint in [("SHARED", 0), *((m, r) for m in methods for r in (1, 2, 3))]:
        if not checkpoint:
            sidecar = root / "reports/capability/g5_9_real_data_s0/SHARED_seed0_S0"
        elif method in P1:
            sidecar = root / "reports/p1p2_integration/capability_sidecars" / f"{method}_seed13_S{checkpoint}"
        else:
            sidecar = root / "reports/capability/g5_9_historical_20261117" / f"{method}_seed13_S{checkpoint}"
            if not sidecar.is_dir() and method == "B4":
                sidecar = root / "reports/capability_g4_validation" / sidecar.name
        manifest = sidecar / "student_capability_evaluation_manifest.json"
        if not manifest.is_file():
            if missing is None or checkpoint == 0:
                raise FileNotFoundError(manifest)
            missing[f"{method} S{checkpoint}"] = str(manifest)
            continue
        metrics, metadata = validate_one(sidecar)
        resolved = observed(lambda: verified_prediction(root, method, checkpoint), missing if checkpoint else None,
                            f"{method} S{checkpoint}")
        if resolved is None:
            continue
        prediction, _ = resolved
        if (metadata["method"], metadata["seed"], metadata["checkpoint"]) != (method, 13 if checkpoint else 0, f"S{checkpoint}"):
            raise ValueError(f"Sidecar identity mismatch: {sidecar}")
        if (sha256(prediction) != metadata["prediction_sha256"]
                or any(metadata["input_hashes"].get(key) != value for key, value in gold.items())):
            raise ValueError(f"Sidecar input fingerprint mismatch: {sidecar}")
        inputs[str(manifest)] = metadata["sidecar_manifest_sha256"]
        inputs[str(prediction)] = metadata["prediction_sha256"]
        rows.extend({**row, "prediction_path": str(prediction), "sidecar_manifest_sha256": metadata["sidecar_manifest_sha256"]}
                    for row in metrics)
    return rows


def figure_data(root, name, missing=None):
    inputs, result = {}, []
    if name == "student_accuracy":
        dev_path = root / "splits/d_dev_ids.txt"
        ids = set(dev_path.read_text(encoding="utf-8-sig").split())
        if len(ids) != 500:
            raise ValueError(f"Expected 500 D_dev IDs: {dev_path}")
        inputs[str(dev_path)] = sha256(dev_path)
        for method, checkpoint in [("SHARED", 0), *((m, r) for m in METHODS for r in (1, 2, 3))]:
            resolved = observed(lambda: verified_prediction(root, method, checkpoint), missing if checkpoint else None,
                                f"{method} S{checkpoint}")
            if resolved is None:
                continue
            prediction, _ = resolved
            if {row["problem_id"] for row in read_jsonl(prediction)} != ids:
                raise ValueError(f"Incomplete D_dev coverage: {prediction}")
            result.append({"method": method, "checkpoint": f"S{checkpoint}", "denominator": 500,
                           "prediction_path": str(prediction), "prediction_sha256": sha256(prediction),
                           **score(prediction, ids)})
            inputs[str(prediction)] = sha256(prediction)
    elif name in ("capability_mastery", "p1_capability_learning_curves"):
        result = mastery_data(root, P1 if name.startswith("p1_") else METHODS, inputs, missing)
    else:
        if name == "capability_makeup":
            pool = root / "trajectory/pool/pool_v1_verified.jsonl"
            inputs[str(pool)] = sha256(pool)
            pool_rows = read_jsonl(pool)
            verified = {row["trajectory_id"]: row["capabilities"] for row in pool_rows}
            if (len(verified) != len(pool_rows) or any(not labels or not set(labels) <= set(CAPABILITIES)
                                                      for labels in verified.values())):
                raise ValueError(f"Invalid verified capability labels: {pool}")
        methods = ("B4", "B5", "P1P2") if name == "learnability_distribution" else METHODS
        for method in methods:
            rounds = {r: observed(lambda: selection_rows(root, method, r, inputs), missing, f"{method} R{r}") for r in (1, 2, 3)}
            sets = {r: entry[0] for r, entry in rounds.items() if entry is not None}
            if name == "selection_jaccard":
                for a, b in combinations(sets, 2):
                    intersection, union = len(sets[a] & sets[b]), len(sets[a] | sets[b])
                    result.append({"method": method, "pair": f"R{a} vs R{b}", "first_round": a, "second_round": b,
                                   "intersection_count": intersection, "union_count": union, "jaccard": intersection / union})
            elif name == "selection_composition":
                prefix = []
                for r in (1, 2, 3):
                    if r not in sets:
                        break
                    prefix.append(sets[r])
                for r, counts in enumerate(selection_composition(prefix), 1):
                    if r == 1:
                        counts.update(retained=None, readmitted=None)
                    result.append({"method": method, "round": r, "selected_count": len(sets[r]), **counts})
            else:
                for r, selected_and_log in rounds.items():
                    if selected_and_log is None:
                        continue
                    selected, log = selected_and_log
                    if name == "capability_makeup":
                        eligible = {row["trajectory_id"] for row in log
                                    if row.get("reason", row.get("criterion")) not in {"ineligible", "already_trained"}}
                        if not selected <= eligible <= verified.keys():
                            raise ValueError(f"Selection contains unverified IDs: {method} R{r}")
                        for group, ids in (("selected", selected), ("eligible", eligible)):
                            for cap in CAPABILITIES:
                                count = sum(cap in verified[t] for t in ids)
                                result.append({"method": method, "round": r, "group": group, "capability": cap,
                                               "fraction": count / len(ids), "capability_count": count,
                                               "trajectories": len(ids), "pool_path": str(pool), "pool_sha256": inputs[str(pool)]})
                    else:
                        scores = [row for row in log if row.get("p2_l_proxy", row.get("l_proxy")) is not None]
                        if not scores:
                            raise ValueError(f"Missing observed L_proxy values: {method} R{r}")
                        for entry in scores:
                            value = entry.get("p2_l_proxy", entry.get("l_proxy"))
                            if not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
                                raise ValueError(f"Invalid L_proxy: {method} R{r}")
                            result.append({"method": method, "round": r, "checkpoint": entry["source_checkpoint"],
                                           "trajectory_id": entry["trajectory_id"], "l_proxy": value})
    if not result:
        raise ValueError("No validated observations available for this figure")
    return result, inputs


def draw(path, name, rows, *, partial=False):
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import pyplot as plt
    from matplotlib.ticker import PercentFormatter

    checkpoints = ["S0", "S1", "S2", "S3"]

    def plot_checkpoints(ax, series, metric, method):
        values = {row["checkpoint"]: row[metric] for row in series}
        ax.plot(range(4), [values.get(key, math.nan) for key in checkpoints], marker="o", label=method,
                color=COLORS[method])
        ax.set_xticks(range(4), checkpoints)
        ax.set_xlim(-0.15, 3.15)
        ax.yaxis.set_major_formatter(PercentFormatter(1))

    if name in ("capability_mastery", "p1_capability_learning_curves"):
        fig, axes = plt.subplots(2, 4, figsize=(14, 7), sharey=True, layout="constrained")
        for cap, ax in zip(CAPABILITIES, axes.flat):
            panel = [row for row in rows if row["capability"] == cap]
            shared = next(row for row in panel if row["method"] == "SHARED")
            for method in sorted({row["method"] for row in panel} - {"SHARED"}):
                series = [shared] + [row for row in panel if row["method"] == method]
                plot_checkpoints(ax, series, "mastery", method)
            ax.set(title=cap, ylim=(0, 1), ylabel="Strict Gold mastery")
        axes.flat[0].legend(fontsize=8)
        axes.flat[-1].set_visible(False)
    else:
        fig, ax = plt.subplots(figsize=(13, 6), layout="constrained")
        if name == "student_accuracy":
            shared = rows[0]
            for method in sorted({row["method"] for row in rows} - {"SHARED"}):
                series = [shared] + [row for row in rows if row["method"] == method]
                plot_checkpoints(ax, series, "accuracy", method)
            ax.set(ylabel="Strict D_dev accuracy (500 IDs)", ylim=(0, 1))
        elif name == "selection_jaccard":
            pairs = ["R1 vs R2", "R1 vs R3", "R2 vs R3"]
            for index, method in enumerate(METHODS):
                series = [row for row in rows if row["method"] == method]
                if series:
                    ax.scatter([pairs.index(row["pair"]) + (index - 1.5) * 0.10 for row in series],
                               [row["jaccard"] for row in series], label=method, color=COLORS[method], clip_on=False)
            ax.set_xticks(range(3), pairs)
            ax.set_xlim(-0.3, 2.3)
            ax.set(ylabel="Jaccard overlap", ylim=(0, 1))
            ax.yaxis.set_major_formatter(PercentFormatter(1))
        elif name == "selection_composition":
            labels = [f"{row['method']} R{row['round']}" for row in rows]
            bottom = [0] * len(rows)
            for category in ("new", "retained", "readmitted"):
                counts = [row[category] or 0 for row in rows]
                ax.bar(labels, counts, bottom=bottom, label=category)
                bottom = [a + b for a, b in zip(bottom, counts)]
            ax.set_ylabel("Selected trajectories")
            ax.set_xlabel("Retained and readmitted are not applicable in R1")
        elif name == "capability_makeup":
            for method in METHODS:
                for group in ("selected", "eligible"):
                    series = [row for row in rows if row["method"] == method and row["group"] == group]
                    if series:
                        ax.plot([f"R{row['round']} {row['capability']}" for row in series],
                                [row["fraction"] for row in series], label=f"{method} {group}", color=COLORS[method],
                                linestyle="-" if group == "selected" else "--")
            ax.set_ylabel("Fraction of trajectories")
            ax.set_ylim(0, 1)
            ax.yaxis.set_major_formatter(PercentFormatter(1))
        else:
            groups = sorted({(row["method"], row["round"], row["checkpoint"]) for row in rows})
            samples = [[row["l_proxy"] for row in rows if (row["method"], row["round"], row["checkpoint"]) == key]
                       for key in groups]
            ax.boxplot(samples, tick_labels=[f"{method} R{r}\n{checkpoint}" for method, r, checkpoint in groups])
            ax.set_ylabel("L_proxy")
        ax.tick_params(axis="x", labelrotation=40)
        if name != "learnability_distribution":
            ax.legend(fontsize=8)
    scope = "single seed 13, partial checkpoint coverage" if partial else "single seed 13"
    fig.suptitle(f"{name.replace('_', ' ').title()} · {scope}")
    fig.savefig(path, dpi=220)
    plt.close(fig)


def row_sources(name, row, inputs):
    method = row["method"]
    if "prediction_path" in row:
        return {path: digest for path, digest in inputs.items()
                if path == row["prediction_path"] or Path(path).name == "d_dev_ids.txt"
                or Path(path).parent == Path(row.get("sidecar_source", "."))}
    if name == "selection_jaccard":
        rounds = (row["first_round"], row["second_round"])
    elif name == "selection_composition":
        rounds = range(1, row["round"] + 1)
    else:
        rounds = (row["round"],)
    names = {f"round_{r-int(method in ('B4', 'B5')):03d}" for r in rounds}
    return {path: digest for path, digest in inputs.items()
            if Path(path).name == "pool_v1_verified.jsonl" or
            (f"{method}_seed13" in Path(path).parts and Path(path).parent.name in names)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manual-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--preflight", action="store_true", help="Report availability without writing figures")
    parser.add_argument("--allow-partial", action="store_true", help="Plot only verified observations and list unavailable scopes")
    args = parser.parse_args()
    root = args.manual_root.resolve()
    output = args.output or root / OUTPUT
    manifest = {"schema_version": VERSION, "script_sha256": sha256(Path(__file__)),
                "generated_at_utc": datetime.now(timezone.utc).isoformat(),
                "scope": "single seed 13, one shared S0, descriptive analysis", "figures": {}}
    if not args.preflight and (output / "figure_manifest.json").exists():
        raise FileExistsError(output / "figure_manifest.json")
    for name in NAMES:
        stem = f"{name}_seed13"
        missing = {} if args.allow_partial else None
        try:
            rows, inputs = figure_data(root, name, missing)
        except (OSError, ValueError, KeyError) as exc:
            manifest["figures"][stem] = {"status": "BLOCKED", "reason": str(exc)}
            continue
        manifest["figures"][stem] = {"status": "AVAILABLE" if args.preflight else "GENERATED", "inputs": inputs,
                                     "missing": missing or {}, "partial": bool(missing), "observations": len(rows)}
        if not args.preflight:
            with tempfile.TemporaryDirectory() as temp:
                png = Path(temp) / f"{stem}.png"
                draw(png, name, rows, partial=bool(missing))
                csv_path = output / f"{stem}.csv"
                buffer = io.StringIO(newline="")
                writer = csv.DictWriter(buffer, fieldnames=[*dict.fromkeys(key for row in rows for key in row),
                                                           "seed_scope", "source_paths_and_sha256"])
                writer.writeheader()
                writer.writerows({**row, "seed_scope": 13, "source_paths_and_sha256":
                                  json.dumps(row_sources(name, row, inputs), ensure_ascii=False, sort_keys=True)} for row in rows)
                publish_pair_no_overwrite(output / png.name, png.read_bytes(), csv_path, buffer.getvalue().encode("utf-8"))
                manifest["figures"][stem]["outputs"] = {file.name: sha256(file) for file in (output / png.name, csv_path)}
    if not args.preflight:
        publish_json_no_overwrite(output / "figure_manifest.json", manifest)
    print(json.dumps(manifest, indent=2))
    complete = all(f["status"] == "GENERATED" and not f.get("partial") for f in manifest["figures"].values())
    return 0 if args.preflight or complete else 4


if __name__ == "__main__":
    raise SystemExit(main())
