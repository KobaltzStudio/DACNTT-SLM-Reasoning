from selection_common import parser_for, run

def main():
    p=parser_for("B5")
    a=p.parse_args()
    if True and not a.scores: p.error("--scores is required")
    run("B5","dynamic",a)

if __name__=="__main__": main()
