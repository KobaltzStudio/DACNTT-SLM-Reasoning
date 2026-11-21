#!/usr/bin/env python3
"""
Analyze the Task 5 smoke test and apply the pre-agreed decision thresholds.

Decision rule (agreed 2026-10-19 before running; see Instruction_0.1.md section 8):
  change is "clear" if |Acc(S_1) - Acc(S_0)| >= 0.02 on D_dev OR exact McNemar p < 0.10.
  clear increase + decreasing loss  -> keep I3/I4/I5
  no clear change                   -> more epochs or larger n_round (config v2)
  clear decrease                    -> inspect pipeline / format; discuss Teacher-Student pair
  loss not decreasing               -> lower the learning rate

Exploratory (not used for the decision): NLL rank stability between S_0 and S_1, split into
trajectories that were trained on and trajectories that were not; L_proxy top-n overlap.

Inputs in --dir (default reports/task5/smoke_test/):
  eval_S0_dev.jsonl, eval_S1_dev_seed<s>.jsonl, train_log_seed<s>.json, train_set_seed<s>.json,
  nll_pool_S0.jsonl, nll_pool_S1_seed<s>.jsonl (optional)
Outputs: smoke_analysis.json, smoke_analysis.md

Usage (from experiments/week2September/manual/):
  python scripts/analyze_smoke_test.py --seeds 13 42
"""
import argparse
import json
import math
import statistics
import sys
from pathlib import Path

from scipy.stats import binomtest, spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parent))
from student_common import SMOKE_DIR, load_config, read_jsonl, write_json  # noqa: E402

DELTA_CLEAR = 0.02
P_CLEAR = 0.10
FORMAT_CONFOUND = 0.05


def accuracy_block(s0, s1):
    ids = sorted(set(s0) & set(s1))
    if len(ids) != len(s0) or len(ids) != len(s1):
        raise ValueError("S_0 and S_1 evaluations cover different problems")
    c0 = [s0[i]["status"] == "valid" for i in ids]
    c1 = [s1[i]["status"] == "valid" for i in ids]
    b = sum((not a) and c for a, c in zip(c0, c1))   # wrong -> right
    c = sum(a and (not d) for a, d in zip(c0, c1))   # right -> wrong
    p = binomtest(b, b + c, 0.5).pvalue if b + c else 1.0
    acc0, acc1 = sum(c0) / len(ids), sum(c1) / len(ids)
    fmt = lambda d: sum(d[i]["status"] != "invalid_format" for i in ids) / len(ids)  # noqa: E731
    mlen = lambda d: statistics.mean(d[i]["n_output_tokens"] for i in ids)  # noqa: E731
    return {
        "n": len(ids), "acc_S0": acc0, "acc_S1": acc1, "delta": acc1 - acc0,
        "wrong_to_right": b, "right_to_wrong": c, "mcnemar_exact_p": p,
        "format_S0": fmt(s0), "format_S1": fmt(s1),
        "mean_len_S0": mlen(s0), "mean_len_S1": mlen(s1),
        "lenient_acc_S0_exploratory": sum(s0[i].get("lenient_correct", False) for i in ids) / len(ids),
        "lenient_acc_S1_exploratory": sum(s1[i].get("lenient_correct", False) for i in ids) / len(ids),
        "clear_change": abs(acc1 - acc0) >= DELTA_CLEAR or p < P_CLEAR,
    }


def loss_block(log):
    losses = [s["loss"] for s in log["steps_log"]]
    k = max(1, min(5, len(losses) // 3))
    first, last = statistics.mean(losses[:k]), statistics.mean(losses[-k:])
    return {"steps": len(losses), "loss_first": first, "loss_last": last,
            "loss_decreasing": last < first, "max_loss": max(losses),
            "supervised_tokens": log["cumulative_training_tokens"],
            "beta_round_tokens_config": log["beta_round_tokens_config"],
            "train_seconds": log["elapsed_seconds"], "peak_gpu_memory_gb": log["peak_gpu_memory_gb"]}


def decide(acc, loss):
    if not loss["loss_decreasing"]:
        return "lower_lr", "Loss không giảm: giảm learning rate (vd. 1e-4) và chạy lại"
    if acc["clear_change"] and acc["delta"] > 0:
        return "keep", "Accuracy tăng rõ, loss giảm: giữ I3/I4/I5"
    if acc["clear_change"] and acc["delta"] < 0:
        return "decrease", "Accuracy giảm rõ: kiểm tra định dạng/pipeline, cân nhắc đổi cặp mô hình"
    return "no_change", "Không thay đổi rõ: tăng epoch hoặc n_round (config v2)"


def l_proxy(ells):
    vals = sorted(ells.values())
    med = statistics.median(vals)
    q = statistics.quantiles(vals, n=4)
    sigma = (q[2] - q[0]) / 1.349
    return {k: math.exp(-((v - med) ** 2) / (2 * sigma ** 2)) for k, v in ells.items()}, med, sigma


def nll_block(nll0, nll1, trained, n_top):
    ids = sorted(set(nll0) & set(nll1))
    out = {}
    for name, sub in (("all", ids), ("trained", [i for i in ids if i in trained]),
                      ("untrained", [i for i in ids if i not in trained])):
        if len(sub) < 3:
            continue
        a, b = [nll0[i]["ell"] for i in sub], [nll1[i]["ell"] for i in sub]
        out[name] = {"n": len(sub), "spearman_ell": spearmanr(a, b).statistic,
                     "mean_ell_S0": statistics.mean(a), "mean_ell_S1": statistics.mean(b),
                     "mean_delta_ell": statistics.mean(y - x for x, y in zip(a, b))}
    lp0, med0, sd0 = l_proxy({i: nll0[i]["ell"] for i in ids})
    lp1, med1, sd1 = l_proxy({i: nll1[i]["ell"] for i in ids})
    top = lambda lp: set(sorted(lp, key=lambda k: (-lp[k], k))[:n_top])  # noqa: E731
    t0, t1 = top(lp0), top(lp1)
    out["l_proxy"] = {"ell_star_S0": med0, "sigma_S0": sd0, "ell_star_S1": med1, "sigma_S1": sd1,
                      "spearman_l_proxy": spearmanr([lp0[i] for i in ids], [lp1[i] for i in ids]).statistic,
                      "top_n": n_top, "jaccard_top_n": len(t0 & t1) / len(t0 | t1)}
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", type=Path, default=SMOKE_DIR)
    ap.add_argument("--seeds", type=int, nargs="+", default=[13, 42])
    args = ap.parse_args()
    d = args.dir
    cfg = load_config()

    s0 = {r["problem_id"]: r for r in read_jsonl(d / "eval_S0_dev.jsonl")}
    nll0_path = d / "nll_pool_S0.jsonl"
    nll0 = {r["trajectory_id"]: r for r in read_jsonl(nll0_path)} if nll0_path.exists() else None
    result = {"thresholds": {"delta_clear": DELTA_CLEAR, "mcnemar_p_clear": P_CLEAR}, "seeds": {}}
    for seed in args.seeds:
        s1_path = d / f"eval_S1_dev_seed{seed}.jsonl"
        if not s1_path.exists():
            print(f"seed {seed}: {s1_path.name} missing, skipped")
            continue
        s1 = {r["problem_id"]: r for r in read_jsonl(s1_path)}
        acc = accuracy_block(s0, s1)
        loss = loss_block(json.loads((d / f"train_log_seed{seed}.json").read_text(encoding="utf-8")))
        code, text = decide(acc, loss)
        # a change in format compliance confounds the strict metric with learning the output format
        acc["format_confound"] = abs(acc["format_S1"] - acc["format_S0"]) >= FORMAT_CONFOUND
        if acc["format_confound"]:
            text += " (CẢNH BÁO: tỉ lệ đúng định dạng đổi ≥ 5 điểm %, so với accuracy lỏng trước khi kết luận)"
        entry = {"accuracy": acc, "training": loss, "decision": code, "decision_text": text}
        nll1_path = d / f"nll_pool_S1_seed{seed}.jsonl"
        if nll0 and nll1_path.exists():
            trained = set(json.loads((d / f"train_set_seed{seed}.json").read_text(encoding="utf-8"))["trajectory_ids"])
            nll1 = {r["trajectory_id"]: r for r in read_jsonl(nll1_path)}
            entry["nll_exploratory"] = nll_block(nll0, nll1, trained, cfg["budget"]["n_round"])
        result["seeds"][str(seed)] = entry

    deltas = [e["accuracy"]["delta"] for e in result["seeds"].values()]
    if len(deltas) > 1:
        result["seed_spread_delta"] = max(deltas) - min(deltas)
    codes = {e["decision"] for e in result["seeds"].values()}
    result["overall_decision"] = codes.pop() if len(codes) == 1 else "seeds_disagree"
    write_json(d / "smoke_analysis.json", result)

    lines = ["# Smoke test: kết quả phân tích tự động", "",
             f"Ngưỡng: |ΔAcc| ≥ {DELTA_CLEAR:.0%} hoặc McNemar p < {P_CLEAR}.", "",
             "| Seed | Acc S_0 | Acc S_1 | Δ | sai→đúng | đúng→sai | p | Format S_0→S_1 | Loss đầu→cuối | Quyết định |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for seed, e in result["seeds"].items():
        a, t = e["accuracy"], e["training"]
        lines.append(f"| {seed} | {a['acc_S0']:.3f} | {a['acc_S1']:.3f} | {a['delta']:+.3f} | {a['wrong_to_right']} | "
                     f"{a['right_to_wrong']} | {a['mcnemar_exact_p']:.3g} | {a['format_S0']:.3f}→{a['format_S1']:.3f} | "
                     f"{t['loss_first']:.3f}→{t['loss_last']:.3f} | {e['decision_text']} |")
    lines += ["", "Accuracy lỏng (exploratory, số cuối trong output, bỏ qua định dạng):"]
    for seed, e in result["seeds"].items():
        a = e["accuracy"]
        lines.append(f"- seed {seed}: {a['lenient_acc_S0_exploratory']:.3f} → {a['lenient_acc_S1_exploratory']:.3f}")
    lines += ["", f"**Quyết định chung:** `{result['overall_decision']}`"]
    if "seed_spread_delta" in result:
        lines.append(f"Chênh lệch Δ giữa các seed: {result['seed_spread_delta']:.3f}")
    for seed, e in result["seeds"].items():
        if "nll_exploratory" in e:
            n = e["nll_exploratory"]
            lines += ["", f"## NLL (exploratory), seed {seed}", "",
                      "| Nhóm | n | Spearman ℓ(S_0), ℓ(S_1) | Δℓ trung bình |", "|---|---|---|---|"]
            for g in ("all", "trained", "untrained"):
                if g in n:
                    lines.append(f"| {g} | {n[g]['n']} | {n[g]['spearman_ell']:.3f} | {n[g]['mean_delta_ell']:+.4f} |")
            lp = n["l_proxy"]
            lines.append(f"\nL_proxy: Spearman S_0/S_1 = {lp['spearman_l_proxy']:.3f}, "
                         f"Jaccard top-{lp['top_n']} = {lp['jaccard_top_n']:.3f}")
    (d / "smoke_analysis.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
