from selection_common import parser_for, run

def main():
    p=parser_for("B2")
    a=p.parse_args()
    if False and not a.scores: p.error("--scores is required")
    run("B2","random",a)

if __name__=="__main__": main()
