"""Match yearly-page actions to letters (by STN/supplement, else BLA + date within a week)."""
import datetime
import json
import os

from pipeline.cber import fetch

BASE = fetch.BASE


def d(s):
    return datetime.date.fromisoformat(s) if s else None


def letter_keys(r):
    """(appl, suppl, date) tuples a parsed letter row covers."""
    date = r.get("letter_date")
    if not date and r.get("link_date"):
        from pipeline.cber import letters
        m = letters.DATE_RE.search(r["link_date"])
        date = letters.iso(m) if m else None
    return [(a, s, date) for a, s in (r.get("stns") or [])], date


def match_actions(actions, lrows):
    by_stn, by_appl = {}, {}
    for r in lrows:
        keys, date = letter_keys(r)
        for a, s, dt in keys:
            if s is not None:
                by_stn.setdefault((a, s), []).append(r)
            by_appl.setdefault(a, []).append((dt, r))
    out = []
    for a in actions:
        cands = []
        how = None
        if a.get("appl_no") and a.get("stn_suppl") is not None:
            cands = by_stn.get((a["appl_no"], a["stn_suppl"]), [])
            how = "stn"
        if not cands and a.get("appl_no") and a.get("approval_date"):
            ad = d(a["approval_date"])
            cands = [r for dt, r in by_appl.get(a["appl_no"], []) if dt and abs((d(dt) - ad).days) <= 7]
            how = "appl_date"
        out.append((a, cands, how if cands else None))
    return out


if __name__ == "__main__":
    rows = [json.loads(l) for l in open(os.path.join(BASE, "year_page_rows.jsonl"))]
    lrows = [json.loads(l) for l in open(os.path.join(BASE, "letters_parsed.jsonl"))]
    res = match_actions(rows, lrows)
    n = sum(1 for _, c, _ in res if c)
    print("matched", n, "of", len(res))
