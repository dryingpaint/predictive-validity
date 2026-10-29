"""What the next publish changes in the report's Claude Doc.

    python -m report.doc plan                          # report/output/doc_plan.json: figures to upload, sections to write
    python -m report.doc blob PATH=BLOB [PATH=BLOB]    # record the doc blob a figure file was uploaded as
    python -m report.doc published TAB=REV [TAB=REV]   # record the rendered tabs as published at those revisions

The Claude Doc (DOC in report/doc.json) is the canonical report: people edit its prose, and a
publish writes the rendered tabs into it (the report-doc skill, .claude/skills/report-doc). Each
tab is cut into sections at its headings. report/doc.json keeps, per tab, a hash of each section
as last published and the tab's revision then, and for each figure the hash of the file uploaded
and its doc blob. `plan` lists the figures whose file changed (to upload first) and the sections
whose rendered text or figure differs (replace), is new (insert after the section before it) or is
gone (delete), with figure paths written as their blobs. Prose people edit in the doc is ported
back to the templates before a build, so a section the plan rewrites carries their edits.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re

from report import frame

STATE = os.path.join(frame.REPO, "report", "doc.json")
PLAN = os.path.join(frame.REPO, "report", "output", "doc_plan.json")
HEADING = re.compile(r"^(#{1,6}) (.+)$")
FIGURE = re.compile(r"!\[([^\]]*)\]\((report/output/figures/[^)]+\.png)\)")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


def sections(markdown: str) -> list[dict]:
    """The tab's sections in order: each heading with the text up to the next heading. A section's
    key is its heading path ("Industry failure modes > Phase transitions"); HTML comments are dropped."""
    markdown = re.sub(r"<!--.*?-->\n*", "", markdown, flags=re.S)
    out, path, fenced = [], [], False
    for line in markdown.split("\n"):
        fenced ^= line.startswith("```")
        m = None if fenced else HEADING.match(line)
        if m:
            level = len(m.group(1))
            path = [p for p in path if p[0] < level] + [(level, m.group(2).strip())]
            out.append({"key": " > ".join(t for _, t in path), "level": level, "heading": m.group(2).strip(),
                        "lines": [line]})
        elif out:
            out[-1]["lines"].append(line)
    for s in out:
        s["markdown"] = "\n".join(s.pop("lines")).strip() + "\n"
        s["hash"] = sha(s["markdown"].encode())
    return out


def figure_hash(path: str) -> str:
    return sha(open(os.path.join(frame.REPO, path), "rb").read())


def plan(_args) -> None:
    state = json.load(open(STATE))
    known = state["figures"]
    fresh = {path: f["blob"] for path, f in known.items() if f["hash"] == figure_hash(path)}
    steps, figures = [], []
    for name, tab in state["tabs"].items():
        now = sections(open(os.path.join(frame.REPO, name)).read())
        before = tab["sections"]
        prev = None
        for s in now:
            paths = [p for _, p in FIGURE.findall(s["markdown"])]
            figures += [{"tab": name, "alt": a, "path": p} for a, p in FIGURE.findall(s["markdown"]) if p not in fresh]
            changed_figure = any(p not in fresh or known[p].get("published") != known[p]["blob"] for p in paths)
            s["markdown"] = FIGURE.sub(lambda m: f"![{m.group(1)}]({fresh.get(m.group(2), m.group(2))})", s["markdown"])
            if s["key"] not in before:
                steps.append({"tab": name, "action": "insert", "after": prev, **s})
            elif before[s["key"]] != s["hash"] or changed_figure:
                steps.append({"tab": name, "action": "replace", **s})
            prev = s["key"]
        keys = {s["key"] for s in now}
        steps += [{"tab": name, "action": "delete", "key": k} for k in before if k not in keys]
    if figures:
        steps = []  # upload the figures and record their blobs first; the sections then cite them
    out = {"doc": state["doc"], "tabs": {k: {"node": v["node"], "rev": v["rev"]} for k, v in state["tabs"].items()},
           "sections": steps, "figures": figures}
    with open(PLAN, "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(f"{PLAN}: {sum(s['action'] == 'replace' for s in steps)} sections to replace, "
          f"{sum(s['action'] == 'insert' for s in steps)} to insert, {sum(s['action'] == 'delete' for s in steps)} "
          f"to delete, {len(figures)} figures")


def published(args) -> None:
    state = json.load(open(STATE))
    revs = dict(a.split("=", 1) for a in args.revs)
    for name, tab in state["tabs"].items():
        text = open(os.path.join(frame.REPO, name)).read()
        tab["sections"] = {s["key"]: s["hash"] for s in sections(text)}
        if name in revs:
            tab["rev"] = int(revs[name])
        for _, path in FIGURE.findall(text):
            state["figures"][path]["published"] = state["figures"][path]["blob"]
    with open(STATE, "w") as f:
        json.dump(state, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print(f"{STATE}: recorded {', '.join(f'{k} rev {v}' for k, v in revs.items())}")


def blob(args) -> None:
    state = json.load(open(STATE))
    for a in args.blobs:
        path, b = a.split("=", 1)
        state["figures"][path] = {**state["figures"].get(path, {}), "hash": figure_hash(path), "blob": b}
    with open(STATE, "w") as f:
        json.dump(state, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print(f"{STATE}: recorded {len(args.blobs)} figure blobs")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("plan").set_defaults(fn=plan)
    b = sub.add_parser("blob")
    b.add_argument("blobs", nargs="+", metavar="PATH=BLOB")
    b.set_defaults(fn=blob)
    p = sub.add_parser("published")
    p.add_argument("revs", nargs="+", metavar="TAB=REV")
    p.set_defaults(fn=published)
    args = parser.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
