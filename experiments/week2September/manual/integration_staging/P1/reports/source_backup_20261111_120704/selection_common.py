import argparse, json, random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from student_common import MANUAL_DIR, POOL_VERIFIED, CONFIG_PATH, load_config, load_pool, load_tokenizer, encode_example, sha256_file

def read_jsonl(path):
    if not path or not Path(path).exists(): return []
    out=[]
    with Path(path).open(encoding="utf-8") as f:
        for i,line in enumerate(f,1):
            if line.strip():
                try: out.append(json.loads(line))
                except json.JSONDecodeError as e: raise ValueError(f"{path}:{i}: {e}") from e
    return out

def parser_for(method):
    p=argparse.ArgumentParser(description=f"Select one round for {method}")
    p.add_argument("--round",type=int,required=True)
    p.add_argument("--seed",type=int,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--log",type=Path,required=True)
    p.add_argument("--pool",type=Path,default=POOL_VERIFIED)
    p.add_argument("--config",type=Path,default=CONFIG_PATH)
    p.add_argument("--scores",type=Path)
    p.add_argument("--source-checkpoint")
    p.add_argument("--budget",type=int,help="reduced budget for smoke tests only")
    return p

def run(method, strategy, a):
    cfg=json.loads(a.config.read_text(encoding="utf-8"))
    if not 0 <= a.round < int(cfg["schedule"]["rounds_M"]): raise ValueError("round outside configured schedule")
    budget=int(a.budget if a.budget is not None else cfg["budget"]["beta_round_tokens"])
    pool=load_pool(a.pool)
    byid={r["trajectory_id"]:r for r in pool}
    if len(byid)!=len(pool): raise ValueError("duplicate trajectory_id in pool")
    tok=load_tokenizer(cfg["student"]["model"],cfg["student"]["revision"])
    lengths = {
        r["trajectory_id"]: int(
            encode_example(
                tok,
                r["question"],
                r["raw_generation"],
                add_eos=True
            )["n_supervised"]
        )
        for r in pool
    }
    scores={}
    if a.scores:
        for r in read_jsonl(a.scores):
            if r["trajectory_id"] in scores: raise ValueError("duplicate ID in scores")
            scores[r["trajectory_id"]]=r
    if method in ("B4","B5"):
        missing=set(byid)-set(scores)
        if missing: raise ValueError(f"score file missing {len(missing)} pool records")
    source=a.source_checkpoint or (f"student_ckpt_{a.round:03d}" if method=="B5" else "student_ckpt_000")
    if method in ("B4","B5"):
        wrong=[tid for tid in byid if scores[tid].get("checkpoint") != source]
        if wrong: raise ValueError(f"{len(wrong)} score records are not from {source}; first={wrong[:3]}")
        invalid=[tid for tid in byid if not 0.0 <= float(scores[tid]["l_proxy"]) <= 1.0]
        if invalid: raise ValueError(f"invalid L_proxy values; first={invalid[:3]}")
    if method=="B4" and source!="student_ckpt_000": raise ValueError("B4 must use S0 scores")
    if method=="B5" and source!=f"student_ckpt_{a.round:03d}": raise ValueError("B5 source checkpoint must match round")
    hist=read_jsonl(a.log)
    hist=[r for r in hist if r.get("record_type")=="selection" and r.get("method")==method and int(r.get("training_seed",-1))==a.seed]
    prev={r["trajectory_id"] for r in hist if r.get("selected")} if method in ("B3","B4") else set()
    used={r["problem_id"] for r in hist if int(r.get("round",-1))==a.round and r.get("selected")}
    if strategy=="random":
        candidates=list(pool); random.Random(a.seed*100+a.round).shuffle(candidates)
    elif strategy=="shortest":
        best={}
        for r in pool:
            k=(lengths[r["trajectory_id"]],r["trajectory_id"])
            if r["problem_id"] not in best or k<best[r["problem_id"]][0]: best[r["problem_id"]]=(k,r)
        candidates=[v[1] for v in best.values()]
        random.Random(a.seed).shuffle(candidates)
    elif strategy=="static":
        candidates=sorted(pool,key=lambda r:(-float(scores[r["trajectory_id"]]["l_proxy"]),r["trajectory_id"]))
    else:
        candidates=sorted(pool,key=lambda r:(-float(scores[r["trajectory_id"]]["l_proxy"]),r["trajectory_id"]))
    selected=[]; spent=0; logrows=[]
    for rank,r in enumerate(candidates,1):
        tid,pid=r["trajectory_id"],r["problem_id"]; nt=lengths[tid]; sc=scores.get(tid,{})
        choose=False
        if pid in used: reason="n_cap_reached"
        elif method in ("B3","B4") and tid in prev: reason="already_selected_in_previous_round"
        elif spent+nt>budget: reason="budget_exhausted"
        else:
            choose=True; reason={"B2":"random","B3":"shortest_correct","B4":"top_l_proxy_static","B5":"top_l_proxy_dynamic"}[method]
            selected.append(r); used.add(pid); spent+=nt
        logrows.append({
            "record_type":"selection","method":method,"round":a.round,"source_checkpoint":source,
            "training_seed":a.seed,"problem_id":pid,"trajectory_id":tid,"tokens":nt,
            "nll":sc.get("nll"),"ell_star":sc.get("ell_star"),"sigma":sc.get("sigma"),
            "l_proxy":sc.get("l_proxy"),"score":sc.get("l_proxy") if method in ("B4","B5") else None,
            "rank":rank if method in ("B3","B4","B5") else None,"selected":choose,
            "criterion":reason,"outcome":None,"config_hash":sha256_file(a.config)
        })
    if not selected: raise RuntimeError("empty selection; check budget and history")
    try: pool_rel=str(a.pool.resolve().relative_to(MANUAL_DIR.resolve())).replace("\\","/")
    except ValueError: raise ValueError("pool must be located inside manual/ for train_round.py")
    train={
        "method":method,"round":a.round,"training_seed":a.seed,"source_checkpoint":source,
        "pool":pool_rel,"pool_sha256":sha256_file(a.pool),
        "trajectory_ids":[r["trajectory_id"] for r in selected],"n_trajectories":len(selected),
        "trajectory_tokens":spent,"trajectory_token_budget":budget,
        "budget_unit": "Student-tokenized supervised response tokens; includes end-of-turn token",
        "config_sha256":sha256_file(a.config)
    }
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(train,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    a.log.parent.mkdir(parents=True,exist_ok=True)
    with a.log.open("a",encoding="utf-8") as f:
        for r in logrows: f.write(json.dumps(r,ensure_ascii=False)+"\n")
    print(f"[PASS] {method} round={a.round} seed={a.seed}: {len(selected)} trajectories, {spent}/{budget} trajectory tokens")
    print(f"[OUT] {a.out}")
