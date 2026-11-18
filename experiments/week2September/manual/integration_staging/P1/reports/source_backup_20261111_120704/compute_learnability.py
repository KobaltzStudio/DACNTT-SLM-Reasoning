import argparse, json, math, statistics
from pathlib import Path
from student_common import write_json, sha256_file, load_config

def read_jsonl(path):
    rows = []
    with Path(path).open(encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            if line.strip():
                try: rows.append(json.loads(line))
                except json.JSONDecodeError as e: raise ValueError(f"{path}:{i}: {e}") from e
    return rows

def derive(rows, checkpoint, eligible_ids=None):
    by_id = {}
    for r in rows:
        tid = r["trajectory_id"]
        if tid in by_id: raise ValueError(f"duplicate trajectory_id: {tid}")
        if int(r["n_tokens"]) <= 0 or not math.isfinite(float(r["ell"])):
            raise ValueError(f"invalid NLL record: {tid}")
        by_id[tid] = r
    if eligible_ids is not None:
        unknown = sorted(eligible_ids - set(by_id))
        if unknown: raise ValueError(f"eligible IDs absent from NLL input: {unknown[:5]}")
    ref = [float(r["ell"]) for tid, r in by_id.items() if eligible_ids is None or tid in eligible_ids]
    if len(ref) < 2: raise ValueError("reference set must contain at least two trajectories")
    q = statistics.quantiles(sorted(ref), n=4, method="inclusive")
    median, q1, q3 = statistics.median(ref), q[0], q[2]
    sigma = (q3 - q1) / 1.349
    if not math.isfinite(sigma) or sigma <= 0:
        raise ValueError(f"IQR/1.349 must be positive; got {sigma}. Inspect reference set; do not silently change formula.")
    out = []
    for tid, r in sorted(by_id.items()):
        ell = float(r["ell"])
        out.append({
            "trajectory_id": tid, "problem_id": r["problem_id"], "checkpoint": checkpoint,
            "tokens": int(r["n_tokens"]), "nll": ell, "ell_star": median, "sigma": sigma,
            "l_proxy": math.exp(-((ell - median) ** 2) / (2 * sigma ** 2)),
            "brier_sum": r.get("brier_sum"),
        })
    return out, {"checkpoint": checkpoint, "n_scored": len(out), "n_reference": len(ref),
                 "ell_star": median, "q1": q1, "q3": q3, "sigma": sigma}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--nll", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--checkpoint", required=True)
    p.add_argument("--eligible-ids", type=Path)
    a = p.parse_args()
    rows = read_jsonl(a.nll)
    if not rows: raise ValueError("NLL input is empty")
    if any(r.get("checkpoint") != a.checkpoint for r in rows):
        raise ValueError("NLL records do not all match --checkpoint")
    eligible = set(a.eligible_ids.read_text(encoding="utf-8").split()) if a.eligible_ids else None
    out, summary = derive(rows, a.checkpoint, eligible)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with a.out.open("w", encoding="utf-8") as f:
        for r in out: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    summary.update({"nll_file": str(a.nll), "nll_sha256": sha256_file(a.nll),
                    "student_revision": load_config()["student"]["revision"],
                    "eligible_ids_file": str(a.eligible_ids) if a.eligible_ids else None})
    write_json(a.out.with_suffix(".summary.json"), summary)
    print(f"[PASS] scored={len(out)} reference={summary['n_reference']} ell_star={summary['ell_star']:.6f} sigma={summary['sigma']:.6f}")

if __name__ == "__main__": main()
