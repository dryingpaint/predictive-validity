"""Collect the checkers' rule questions and missed comparisons from drafts/v3/*.check.json into RULE_QUESTIONS_v3.md.

    .venv/bin/python analyses/model-system-atlas/drafts/v3/collect_questions.py
"""
import glob
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def main() -> None:
    out = ["# Rule questions and missed comparisons from the v3 re-draft", "",
           ("Collected from each tile's checker verdict (`<slug>.check.json`). A rule question is a case the v3 rules did "
            "not decide; a missed comparison is evidence the checker found that the draft left out. Neither changed a "
           "stored status: those went through adjudication."), ""]
    nq = nm = 0
    for p in sorted(glob.glob(os.path.join(HERE, "*.check.json"))):
        c = json.load(open(p))
        slug = os.path.basename(p)[:-11]
        qs, ms = c.get("rule_questions") or [], c.get("missing") or []
        if not qs and not ms:
            continue
        out += [f"## {slug}", ""]
        if qs:
            out += ["Rule questions:", ""] + [f"- {q}" for q in qs] + [""]
        if ms:
            out += ["Missed comparisons:", ""] + [f"- {m}" for m in ms] + [""]
        nq, nm = nq + len(qs), nm + len(ms)
    out.insert(4, f"{nq} rule questions and {nm} missed comparisons across the checked tiles.\n")
    open(os.path.join(HERE, "RULE_QUESTIONS_v3.md"), "w").write("\n".join(out))
    print(nq, "questions,", nm, "missed")


if __name__ == "__main__":
    main()
