"""Offline tests for the group-approved B4/B5 selector semantics."""
import math
from compute_learnability import derive
from selection_common import rank_by_learnability, fill_budget


def test_rank_and_tie_break():
    pool=[{'trajectory_id':'p2_t1','problem_id':'p2'},{'trajectory_id':'p1_t1','problem_id':'p1'},
          {'trajectory_id':'p3_t1','problem_id':'p3'}]
    scores={'p2_t1':{'l_proxy':.9},'p1_t1':{'l_proxy':.9},'p3_t1':{'l_proxy':.5}}
    assert [x['trajectory_id'] for x in rank_by_learnability(pool,scores)]==['p1_t1','p2_t1','p3_t1']


def test_budget_option_a_skip_and_continue():
    candidates=[{'trajectory_id':'a','problem_id':'pa'}, {'trajectory_id':'b','problem_id':'pb'},
                {'trajectory_id':'c','problem_id':'pc'}]
    selected,events,spent=fill_budget(candidates,{'a':8,'b':3,'c':2},5)
    assert [x['trajectory_id'] for x in selected]==['b','c']
    assert spent==5 and events[0]['reason']=='budget_exhausted_skip_continue'


def test_n_cap_and_b4_exclusion():
    candidates=[{'trajectory_id':'a','problem_id':'p'}, {'trajectory_id':'b','problem_id':'p'},
                {'trajectory_id':'c','problem_id':'q'}]
    selected,events,spent=fill_budget(candidates,{'a':1,'b':1,'c':1},10,excluded_ids={'a'})
    assert [x['trajectory_id'] for x in selected]==['b','c']
    assert events[0]['reason']=='already_selected_in_previous_round'
    assert events[2]['selected']


def test_b5_reselection_allowed_by_empty_exclusion():
    row={'trajectory_id':'old','problem_id':'p'}
    selected,_,_=fill_budget([row],{'old':1},10,excluded_ids=set())
    assert [x['trajectory_id'] for x in selected]==['old']


def test_learnability_reference_and_fail_fast():
    rows=[{'trajectory_id':f't{i}','problem_id':f'p{i}','n_tokens':5,'ell':v}
          for i,v in enumerate([1.,1.2,1.4,1.6,1.8])]
    all_scores,meta=derive(rows,'student_ckpt_001',{'t1','t2','t3','t4'})
    assert len(all_scores)==5 and meta['n_reference']==4
    assert all(math.isfinite(x['l_proxy']) and 0<=x['l_proxy']<=1 for x in all_scores)
    try: derive(rows,'student_ckpt_001',{'t0'})
    except ValueError: pass
    else: raise AssertionError('reference set <2 must fail')
    bad=[dict(r) for r in rows]; bad[0]['ell']=float('nan')
    try: derive(bad,'student_ckpt_001')
    except ValueError: pass
    else: raise AssertionError('NaN NLL must fail')
    flat=[dict(r,ell=1.0) for r in rows]
    try: derive(flat,'student_ckpt_001')
    except ValueError: pass
    else: raise AssertionError('sigma=0 must fail')


def main():
    test_rank_and_tie_break(); test_budget_option_a_skip_and_continue()
    test_n_cap_and_b4_exclusion(); test_b5_reselection_allowed_by_empty_exclusion()
    test_learnability_reference_and_fail_fast()
    print('[PASS] B4/B5 protocol unit tests (ranking, Budget A, option A, n_cap, re-selection, fail-fast)')

if __name__=='__main__': main()
