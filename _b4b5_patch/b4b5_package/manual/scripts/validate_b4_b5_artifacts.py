"""Protocol validator for B4/B5 train sets and append-only selection logs."""
import argparse, json, math
from pathlib import Path
from student_common import load_config, load_pool, load_tokenizer, encode_example, sha256_file


def read_jsonl(path):
    rows=[]
    with Path(path).open(encoding='utf-8') as f:
        for i,line in enumerate(f,1):
            if line.strip():
                try: rows.append(json.loads(line))
                except json.JSONDecodeError as e: raise ValueError(f'{path}:{i}: {e}') from e
    return rows


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--train-set',required=True,type=Path)
    p.add_argument('--log',required=True,type=Path)
    p.add_argument('--pool',type=Path)
    p.add_argument('--config',type=Path)
    p.add_argument('--expected-method',choices=['B4','B5'])
    a=p.parse_args()
    ts=json.loads(a.train_set.read_text(encoding='utf-8'))
    method=ts['method']; rnd=int(ts['round']); seed=int(ts['training_seed'])
    if method not in ('B4','B5') or (a.expected_method and method!=a.expected_method):
        raise ValueError('method mismatch; expected B4/B5')
    cfg=json.loads(a.config.read_text(encoding='utf-8')) if a.config else load_config()
    pool_path=a.pool or (Path(__file__).resolve().parents[1]/ts['pool'])
    if sha256_file(pool_path)!=ts['pool_sha256']: raise ValueError('pool SHA256 mismatch')
    pool=load_pool(pool_path); byid={r['trajectory_id']:r for r in pool}
    ids=ts['trajectory_ids']
    if not ids or len(ids)!=len(set(ids)): raise ValueError('empty or duplicate selected IDs')
    if any(x not in byid for x in ids): raise ValueError('selected trajectory absent from verified pool')
    tok=load_tokenizer(cfg['student']['model'],cfg['student']['revision'])
    lengths={r['trajectory_id']:int(encode_example(tok,r['question'],r['raw_generation'],add_eos=False)['n_traj']) for r in pool}
    total=sum(lengths[x] for x in ids)
    budget=int(ts['trajectory_token_budget'])
    if total!=int(ts['trajectory_tokens']): raise ValueError(f'Budget A mismatch: stored {ts["trajectory_tokens"]}, recomputed {total}')
    if total>budget: raise ValueError(f'budget exceeded: {total}>{budget}')
    problems=[byid[x]['problem_id'] for x in ids]
    if len(problems)!=len(set(problems)): raise ValueError('n_cap=1 violated within round')
    if ts.get('budget_unit','').find('excludes <|im_end|>')<0: raise ValueError('train set does not declare Budget A token semantics')

    all_log=read_jsonl(a.log)
    rows=[r for r in all_log if r.get('record_type')=='selection' and r.get('method')==method and int(r.get('training_seed',-1))==seed and int(r.get('round',-1))==rnd]
    log_ids=[r.get('trajectory_id') for r in rows]
    if len(rows)!=len(pool) or len(log_ids)!=len(set(log_ids)) or set(log_ids)!={r['trajectory_id'] for r in pool}: raise ValueError(f'round log coverage mismatch/duplicates: {len(rows)}/{len(pool)}')
    logged=[r['trajectory_id'] for r in rows if r.get('selected')]
    if logged!=ids: raise ValueError('train-set IDs do not match selected IDs in log (including order)')
    for r in rows:
        if r.get('tokens')!=lengths[r['trajectory_id']]: raise ValueError(f'token count mismatch in log: {r["trajectory_id"]}')
        if r.get('selected') and r.get('criterion') not in ({'B4':'top_l_proxy_static','B5':'top_l_proxy_dynamic'}[method],):
            raise ValueError('selected log row has unexpected criterion')
        if method in ('B4','B5'):
            v=float(r['l_proxy'])
            if not math.isfinite(v) or not 0<=v<=1: raise ValueError('invalid L_proxy in log')
    if method=='B4' and ts['source_checkpoint']!='student_ckpt_000': raise ValueError('B4 must use S0')
    if method=='B5' and ts['source_checkpoint']!=f'student_ckpt_{rnd:03d}': raise ValueError('B5 checkpoint mismatch')
    if method=='B4':
        prior={r['trajectory_id'] for r in all_log if r.get('record_type')=='selection' and r.get('method')=='B4' and int(r.get('training_seed',-1))==seed and int(r.get('round',-1))<rnd and r.get('selected')}
        if prior & set(ids): raise ValueError('B4 repeats a trajectory across rounds')
    print(f'[PASS] {method} round={rnd} seed={seed}: {len(ids)} trajectories, {total}/{budget} Budget-A tokens; log coverage and protocol checks passed')

if __name__=='__main__': main()
