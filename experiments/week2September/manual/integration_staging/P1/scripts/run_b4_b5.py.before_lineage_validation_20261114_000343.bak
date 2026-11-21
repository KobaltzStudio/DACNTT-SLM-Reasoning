"""Run one resumable B4/B5 round: score -> learnability -> select -> validate -> train -> dev eval.

Run from experiments/week2September/manual/. Official training is intended for Cloud GPU.
"""
import argparse, json, subprocess, sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
MANUAL=HERE.parent


def run(cmd, label):
    print(f'\n[RUN] {label}:', ' '.join(map(str,cmd)), flush=True)
    subprocess.run([str(x) for x in cmd], cwd=MANUAL, check=True)


def complete_file(path, companion=None):
    if path.exists() and companion and companion.exists(): return True
    if path.exists() or (companion and companion.exists()):
        raise RuntimeError(f'incomplete artifact pair: {path} / {companion}; inspect manually, no overwrite')
    return False


def validate_score_artifacts(nll, nll_summary, scores, score_summary, checkpoint, pool, expected_reference_count):
    from student_common import load_pool, sha256_file
    import math
    pool_ids={r['trajectory_id'] for r in load_pool(pool)}
    ns=json.loads(nll_summary.read_text(encoding='utf-8'))
    if ns.get('checkpoint')!=checkpoint or ns.get('pool_sha256')!=sha256_file(pool):
        raise RuntimeError(f'NLL summary provenance mismatch: {nll_summary}')
    if int(ns.get('n_trajectories',-1))!=len(pool_ids):
        raise RuntimeError(f'NLL summary pool-size mismatch: {nll_summary}')
    nll_rows=[json.loads(x) for x in nll.read_text(encoding='utf-8').splitlines() if x.strip()]
    nll_ids=[r.get('trajectory_id') for r in nll_rows]
    if len(nll_ids)!=len(pool_ids) or len(set(nll_ids))!=len(pool_ids) or set(nll_ids)!=pool_ids:
        raise RuntimeError(f'NLL records do not cover verified pool exactly: {nll}')
    for r in nll_rows:
        if r.get('checkpoint')!=checkpoint or int(r.get('n_tokens',0))<=0 or not math.isfinite(float(r.get('ell',float('nan')))):
            raise RuntimeError(f'invalid NLL record in {nll}: {r.get("trajectory_id")}')
    ss=json.loads(score_summary.read_text(encoding='utf-8'))
    if ss.get('checkpoint')!=checkpoint or ss.get('nll_sha256')!=sha256_file(nll):
        raise RuntimeError(f'learnability summary provenance mismatch: {score_summary}')
    if int(ss.get('n_scored',-1))!=len(pool_ids) or int(ss.get('n_reference',-1))!=expected_reference_count:
        raise RuntimeError(f'learnability reference/scored count mismatch: {score_summary}')
    score_rows=[json.loads(x) for x in scores.read_text(encoding='utf-8').splitlines() if x.strip()]
    score_ids=[r.get('trajectory_id') for r in score_rows]
    if len(score_ids)!=len(pool_ids) or len(set(score_ids))!=len(pool_ids) or set(score_ids)!=pool_ids:
        raise RuntimeError(f'learnability scores do not cover verified pool exactly: {scores}')
    for r in score_rows:
        v=float(r.get('l_proxy',float('nan')))
        if r.get('checkpoint')!=checkpoint or not math.isfinite(v) or not 0<=v<=1:
            raise RuntimeError(f'invalid learnability record in {scores}: {r.get("trajectory_id")}')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--method',required=True,choices=['B4','B5'])
    p.add_argument('--seed',required=True,type=int,choices=[13,42,2026])
    p.add_argument('--round',required=True,type=int,choices=[0,1,2])
    p.add_argument('--pool',type=Path,default=MANUAL/'trajectory/pool/pool_v1_verified.jsonl')
    p.add_argument('--config',type=Path,default=MANUAL/'config/experiment_config.json')
    p.add_argument('--reports-dir',type=Path,default=MANUAL/'reports/task7')
    p.add_argument('--models-dir',type=Path,default=MANUAL/'models/task7')
    p.add_argument('--micro-batch',type=int,default=4)
    p.add_argument('--eval-backend',choices=['hf','vllm'],default='hf')
    p.add_argument('--skip-eval',action='store_true')
    a=p.parse_args()
    method,seed,rnd=a.method,a.seed,a.round
    if not a.pool.exists(): raise FileNotFoundError(a.pool)
    if not a.config.exists(): raise FileNotFoundError(a.config)
    cfg=json.loads(a.config.read_text(encoding='utf-8'))
    if cfg.get('config_version')!='v2' or cfg['budget']['beta_round_tokens']!=45426 or cfg['schedule']['rounds_M']!=3:
        raise RuntimeError('experiment config does not match the frozen v2 B4/B5 protocol')
    if method=='B4':
        score_dir=a.reports_dir/'shared'
        checkpoint='student_ckpt_000'
        adapter=None
    else:
        score_dir=a.reports_dir/method/f'seed_{seed:02d}'/'scores'
        checkpoint=f'student_ckpt_{rnd:03d}'
        adapter=(a.models_dir/method/f'seed_{seed:02d}'/checkpoint) if rnd>0 else None
        if rnd>0 and not adapter.exists(): raise FileNotFoundError(f'B5 requires source adapter {adapter}')
    score_dir.mkdir(parents=True,exist_ok=True)
    nll=score_dir/f'nll_{checkpoint}.jsonl'
    nll_summary=nll.with_suffix('.summary.json')
    scores=score_dir/f'learnability_{checkpoint}.jsonl'
    score_summary=scores.with_suffix('.summary.json')

    # For B5, reference set excludes all trajectories trained in earlier rounds for this seed.
    eligible_file=None
    if method=='B5' and rnd>0:
        prior_ids=set()
        for prev_round in range(rnd):
            prev_set=a.reports_dir/method/f'seed_{seed:02d}'/f'round_{prev_round:03d}'/'train_set.json'
            if not prev_set.exists(): raise FileNotFoundError(f'missing prior B5 train set required for reference exclusion: {prev_set}')
            prior_ids.update(json.loads(prev_set.read_text(encoding='utf-8'))['trajectory_ids'])
        from student_common import load_pool
        all_ids={r['trajectory_id'] for r in load_pool(a.pool)}
        eligible=sorted(all_ids-prior_ids)
        if len(eligible)<2: raise RuntimeError('B5 learnability reference set has fewer than two trajectories; fail-fast')
        eligible_file=score_dir/f'reference_ids_before_round_{rnd:03d}.txt'
        content='\n'.join(eligible)+'\n'
        if eligible_file.exists():
            if eligible_file.read_text(encoding='utf-8')!=content: raise RuntimeError(f'reference ID artifact differs: {eligible_file}')
        else: eligible_file.write_text(content,encoding='utf-8')

    # B4 always uses S0 scores; B5 scores the checkpoint matching this round.
    if not complete_file(nll,nll_summary):
        cmd=[sys.executable,HERE/'compute_nll.py','--tag',checkpoint,'--out',nll,'--pool',a.pool]
        if adapter: cmd += ['--adapter',adapter]
        run(cmd,f'{method} {checkpoint} NLL')
    if not complete_file(scores,score_summary):
        cmd=[sys.executable,HERE/'compute_learnability.py','--nll',nll,'--out',scores,'--checkpoint',checkpoint]
        if eligible_file: cmd += ['--eligible-ids',eligible_file]
        run(cmd,f'{method} {checkpoint} learnability')
    expected_ref_count=len(eligible) if method=="B5" and rnd>0 else len(__import__("student_common").load_pool(a.pool))
    validate_score_artifacts(nll,nll_summary,scores,score_summary,checkpoint,a.pool,expected_ref_count)

    round_dir=a.reports_dir/method/f'seed_{seed:02d}'/f'round_{rnd:03d}'
    train_set=round_dir/'train_set.json'
    log= a.reports_dir/method/f'seed_{seed:02d}'/'selection_log.jsonl'
    round_dir.mkdir(parents=True,exist_ok=True)
    selector=HERE/('select_b4_static.py' if method=='B4' else 'select_b5_dynamic.py')
    cmd=[sys.executable,selector,'--round',str(rnd),'--seed',str(seed),'--scores',scores,
         '--source-checkpoint',checkpoint,'--pool',a.pool,'--config',a.config,'--out',train_set,'--log',log]
    run(cmd,f'{method} round {rnd} selection')
    run([sys.executable,HERE/'validate_train_set.py',train_set,'--pool',a.pool,'--config',a.config,'--budget','45426'],f'{method} round {rnd} train-set validation')
    run([sys.executable,HERE/'validate_b4_b5_artifacts.py','--train-set',train_set,'--log',log,'--pool',a.pool,'--config',a.config],f'{method} round {rnd} protocol validation')

    next_checkpoint=f'student_ckpt_{rnd+1:03d}'
    adapter_out=a.models_dir/method/f'seed_{seed:02d}'/next_checkpoint
    if adapter_out.exists():
        train_log=adapter_out/'train_log.json'
        if not train_log.exists(): raise RuntimeError(f'incomplete adapter directory exists: {adapter_out}; no overwrite')
        logged=json.loads(train_log.read_text(encoding='utf-8'))
        if logged.get('train_set_sha256')!=__import__('hashlib').sha256(train_set.read_bytes()).hexdigest():
            raise RuntimeError(f'existing checkpoint was trained from a different train set: {adapter_out}')
        print(f'[RESUME] Reusing completed adapter {adapter_out}')
    else:
        cmd=[sys.executable,HERE/'train_round.py','--seed',str(seed),'--train-set',train_set,'--adapter-dir',adapter_out,'--micro-batch',str(a.micro_batch)]
        if rnd>0:
            parent=a.models_dir/method/f'seed_{seed:02d}'/f'student_ckpt_{rnd:03d}'
            if not parent.exists() or not (parent/'train_log.json').exists(): raise FileNotFoundError(f'missing parent checkpoint: {parent}')
            cmd += ['--init-adapter',parent]
        run(cmd,f'{method} round {rnd} training -> {next_checkpoint}')

    if not a.skip_eval:
        eval_out=a.reports_dir/method/f'seed_{seed:02d}'/f'eval_{next_checkpoint}_dev.jsonl'
        eval_summary=eval_out.with_suffix('.summary.json')
        if not complete_file(eval_out,eval_summary):
            run([sys.executable,HERE/'eval_student.py','--tag',f'{method}_seed{seed}_{next_checkpoint}',
                 '--adapter',adapter_out,'--out',eval_out,'--split','dev','--backend',a.eval_backend],
                f'{method} {next_checkpoint} D_dev evaluation')
        else: print(f'[RESUME] Reusing completed evaluation {eval_out}')
    print(f'\n[COMPLETE] {method} seed={seed} round={rnd}; produced {next_checkpoint}')

if __name__=='__main__': main()
