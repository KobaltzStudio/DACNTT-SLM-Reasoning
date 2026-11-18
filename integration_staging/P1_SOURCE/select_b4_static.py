from selection_common import parser_for, run

def main():
    p=parser_for("B4")
    a=p.parse_args()
    if True and not a.scores: p.error("--scores is required")
    run("B4","static",a)

if __name__=="__main__": main()
