"""Step 5b: second, wider Wayback pass for yearly-page actions still without a letter:
links from every listing page (old ucm and new slug), more captures per page, wider date tolerance.
Searches the actions whose found_letters*.jsonl record is not found and appends one record per
action to found_letters_pass2.jsonl; actions already in that file are skipped."""
import datetime
import json
import os
import re

from pipeline.cber import enumerate_year_pages
from pipeline.cber import fetch
from pipeline.cber import find_missing
from pipeline.cber import letters

OUT = "found_letters_pass2.jsonl"


def listing_links(row):
    out = []
    for lp in row["listing_pages"]:
        t, *_ = fetch.get_html(lp)
        if not t:
            continue
        base = lp.split("id_/", 1)[-1]
        for r in enumerate_year_pages.parse_tables(t, base):
            if r["stn"].replace(" ", "") == row["stn"].replace(" ", ""):
                for l in r["links"]:
                    u = fetch.unwayback(l["href"])
                    if u not in out:
                        out.append(u)
    return out


def search(row, prods):
    appl, suppl, date = row["appl_no"], row["stn_suppl"], row["approval_date"]
    if row["list_kind"] == "BLA":
        suppl = "0"
    ad = datetime.date.fromisoformat(date)
    first, last = date.replace("-", ""), (ad + datetime.timedelta(days=1100)).strftime("%Y%m%d")
    urls = listing_links(row)
    for u in find_missing.wayback_pages(row, prods):
        if u not in urls:
            urls.append(u)
    tried_pdf = set()
    for u in urls:
        caps = [c for c in fetch.cdx(u) if first <= c["timestamp"][:8] <= last]
        if not caps:
            continue
        step = max(1, len(caps) // 6)
        pick = caps[:2] + caps[2::step][:6]
        for c in pick:
            docs, _ = find_missing.capture_docs(c)
            for doc in docs:
                if not re.search(r"letter", doc["text"], re.I) or re.search(r"REMS|Dear Health|Filing|Proprietary|Complete Response", doc["text"]):
                    continue
                href = fetch.unwayback(doc["href"])
                m = letters.DATE_RE.search(doc.get("date") or doc["text"])
                ld = letters.iso(m) if m else None
                if ld and abs((datetime.date.fromisoformat(ld) - ad).days) > 20:
                    continue
                if href in tried_pdf:
                    continue
                tried_pdf.add(href)
                r = letters.get_letter(href)
                parsed = letters.parse_letter(r["text"]) if r.get("text") else None
                if r.get("sha256") and letters.letter_matches(parsed, appl, suppl, date):
                    return find_missing.found_record(r, parsed, fetch.wayback(c), doc["text"])
    return None


def main():
    rows = fetch.read_jsonl("year_page_rows.jsonl")
    prods = fetch.read_jsonl("products.jsonl") + fetch.read_jsonl("products_historic.jsonl")
    out = os.path.join(fetch.BASE, OUT)
    done = {r["action_row"] for r in fetch.read_jsonl(OUT)} if os.path.exists(out) else set()
    todo = sorted(i for i, r in letters.found_letters().items() if not r["found"] and i not in done)
    for i in todo:
        row = rows[i]
        print(i, row["stn"], row["approval_date"], row["name"][:40], flush=True)
        hit = search(row, prods)
        rec = {"action_row": i, "stn": row["stn"], "approval_date": row["approval_date"], "found": bool(hit)}
        if hit:
            rec.update(hit)
        with open(out, "a") as f:
            f.write(json.dumps(rec) + "\n")
        print("   ->", hit["url"] if hit else "NOT FOUND", flush=True)


if __name__ == "__main__":
    main()
