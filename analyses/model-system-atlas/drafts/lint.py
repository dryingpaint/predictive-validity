"""Schema lint for drafts/*.json against figure.py's assumptions and the v2 brief.

    .venv/bin/python analyses/model-system-atlas/drafts/lint.py

Reports empty cells (no model relied on), consecutive same-status entries (best-model changes that
figure.py collapses), unknown keys, unsorted years, missing `reason` on the latest entry.
"""
import glob
import json
import os
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
STAT = {"same", "other", "neg", "contra", "untested"}
KEYS = {"year", "status", "model", "note", "short", "src", "srcLabel", "quote", "confidence", "subjects",
        "comparison_stated", "epub_year", "print_year", "registry_date", "model_filed", "product_in_model",
        "magnitude", "source_calls_it", "population", "model_first_use_year", "judgement", "reason",
        "patient_trials"}


def main():
    extra, issues = Counter(), []
    for p in sorted(glob.glob(os.path.join(HERE, "*.json"))):
        if p.endswith((".check.json", ".hand.json")):
            continue
        d = json.load(open(p)); cid = os.path.basename(p)[:-5]
        for k in ("order", "area", "disease", "mondo_id", "population", "mechanism", "label", "cells"):
            if k not in d:
                issues.append((cid, "top-level", f"missing {k}"))
        for q in ("engagement", "dose", "efficacy", "safety"):
            strip = d["cells"].get(q)
            if strip is None:
                issues.append((cid, q, "cell missing")); continue
            if not strip:
                issues.append((cid, q, "empty cell (no model relied on)")); continue
            prev = None
            for i, e in enumerate(strip, 1):
                if e.get("status") not in STAT:
                    issues.append((cid, q, f"bad status {e.get('status')!r}"))
                if not isinstance(e.get("year"), int):
                    issues.append((cid, q, f"year not int: {e.get('year')!r}"))
                if prev and e["status"] == prev:
                    issues.append((cid, q, f"same-status entry {i} ({e['status']}): model change or strengthening"))
                prev = e["status"]
                extra.update(k for k in e if k not in KEYS)
            if "reason" not in strip[-1]:
                issues.append((cid, q, "latest entry lacks reason"))
            if sorted(e["year"] for e in strip) != [e["year"] for e in strip]:
                issues.append((cid, q, "years not sorted"))
    print("unknown keys:", dict(extra))
    for i in issues:
        print(*i, sep=" | ")
    print(len(issues), "findings")


if __name__ == "__main__":
    main()
