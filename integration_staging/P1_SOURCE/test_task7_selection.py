from eval_metrics import score_output, summarize
from compute_learnability import derive

def main():
    row={"problem_id":"gsm8k_train_00001","ground_truth":"40"}
    a=score_output(row,"S0","REASONING:\nwork\nANSWER:\n40",12,512)
    b=score_output(row,"S0","The answer is 40",5,512)
    assert a["correct"] and a["format_compliant"]
    assert not b["correct"] and b["lenient_correct"] and not b["format_compliant"]
    m=summarize([a,b],{"gsm8k_train_00001":["arithmetic"]})
    assert m["accuracy"]==0.5 and m["lenient_accuracy"]==1.0
    nll=[{"trajectory_id":f"t{i}","problem_id":f"p{i}","n_tokens":10,"ell":x} for i,x in enumerate([1.,1.2,1.4,1.6,1.8])]
    out,meta=derive(nll,"student_ckpt_000")
    assert len(out)==5 and abs(meta["ell_star"]-1.4)<1e-9
    print("[PASS] eval_metrics and learnability unit tests")

if __name__=="__main__": main()
