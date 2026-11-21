import argparse, json, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from student_common import MANUAL_DIR, POOL_VERIFIED, load_config, load_pool, load_tokenizer, encode_example, sha256_file, DEV_IDS, TEST_IDS

def main():
    p=argparse.ArgumentParser()
    p.add_argument("train_set",type=Path)
    p.add_argument("--pool",type=Path)
    p.add_argument("--config",type=Path)
    p.add_argument("--budget",type=int)
    p.add_argument("--skip-tokenizer",action="store_true")
    a=p.parse_args()
    ts=json.loads(a.train_set.read_text(encoding="utf-8"))
    pp=a.pool or (MANUAL_DIR/ts.get("pool",str(POOL_VERIFIED)))
    if not pp.is_absolute(): pp=MANUAL_DIR/pp
    if ts.get("pool_sha256") and sha256_file(pp)!=ts["pool_sha256"]: raise ValueError("pool SHA256 mismatch")
    pool=load_pool(pp); byid={r["trajectory_id"]:r for r in pool}; ids=ts.get("trajectory_ids",[])
    if not ids: raise ValueError("empty trajectory_ids")
    if len(ids)!=len(set(ids)): raise ValueError("duplicate trajectory IDs")
    missing=[x for x in ids if x not in byid]
    if missing: raise ValueError(f"IDs missing from pool: {missing[:5]}")
    rows=[byid[x] for x in ids]
    held=set(DEV_IDS.read_text(encoding="utf-8").split())|set(TEST_IDS.read_text(encoding="utf-8").split())
    leak=sorted({r["problem_id"] for r in rows}&held)
    if leak: raise ValueError(f"D_dev/D_test leakage: {leak[:5]}")
    cap=int(load_config()["selection"]["n_cap"]); counts={}
    for r in rows: counts[r["problem_id"]]=counts.get(r["problem_id"],0)+1
    if any(v>cap for v in counts.values()): raise ValueError(f"n_cap={cap} violated")
    if a.skip_tokenizer:
        raise ValueError("--skip-tokenizer is disabled for this validator; use exact tokenizer validation")
    cfg=json.loads(a.config.read_text(encoding="utf-8")) if a.config else load_config()
    tok=load_tokenizer(cfg["student"]["model"],cfg["student"]["revision"])
    total = sum(
        int(
            encode_example(
                tok,
                r["question"],
                r["raw_generation"],
                add_eos=False
            )["n_traj"]
        )
        for r in rows
    )
    budget=int(a.budget if a.budget is not None else cfg["budget"]["beta_round_tokens"])
    if total>budget: raise ValueError(f"budget exceeded: {total}>{budget}")
    if "trajectory_tokens" in ts and int(ts["trajectory_tokens"])!=total:
        raise ValueError(f"stored trajectory_tokens={ts['trajectory_tokens']} but recomputed={total}")
    print(
        f"[PASS] {len(rows)} trajectories; "
        f"{total}/{budget} Budget-A trajectory response tokens (excludes <|im_end|>); "
        "pool, leakage, n_cap checks passed"
    )

if __name__=="__main__": main()
