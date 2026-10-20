"""Step 5b: second, wider Wayback pass for yearly-page actions still without a letter:
links from every listing page (old ucm and new slug), more captures per page, wider date tolerance."""
import datetime
import glob
import json
import os
import re

from pipeline.cber import crawl_products
from pipeline.cber import fetch
from pipeline.cber import find_missing
from pipeline.cber import letters
from pipeline.cber import parse_year

BASE = fetch.BASE
WB = find_missing.WB
OUT = os.path.join(BASE, "found_letters_pass2.jsonl")


def d(s):
    return datetime.date.fromisoformat(s)


def listing_links(row):
    out = []
    for lp in row["listing_pages"]:
        t, *_ = fetch.get_html(lp)
        if not t:
            continue
        base = lp.split("id_/", 1)[-1]
        for r in parse_year.parse_tables(t, base):
            if r["stn"].replace(" ", "") == row["stn"].replace(" ", ""):
                for l in r["links"]:
                    u = WB.sub("", l["href"])
                    if u not in out:
                        out.append(u)
    return out


def search(row, prods):
    appl, suppl, date = row["appl_no"], row["stn_suppl"], row["approval_date"]
    if row["list_kind"] == "BLA":
        suppl = "0"
    ad = d(date)
    urls = listing_links(row)
    for u in find_missing.wayback_pages(row, prods):
        if u not in urls:
            urls.append(u)
    print("  urls", urls, flush=True)
    tried_pdf = set()
    for u in urls:
        caps = fetch.cdx(re.sub(r"^https?://", "", u))
        caps = [c for c in caps if ad <= d(f"{c['timestamp'][:4]}-{c['timestamp'][4:6]}-{c['timestamp'][6:8]}") <= ad + datetime.timedelta(days=1100)]
        if not caps:
            continue
        step = max(1, len(caps) // 6)
        pick = caps[:2] + caps[2::step][:6]
        for c in pick:
            wu = f"https://web.archive.org/web/{c['timestamp']}id_/{c['original']}"
            t, *_ = fetch.get_html(wu)
            if not t:
                continue
            _, docs, subs, _ = crawl_products.parse_product_page(t, c["original"])
            for sp in subs:
                href = WB.sub("", sp["href"])
                if "/media/" in href or href.lower().endswith((".pdf", ".zip")):
                    continue
                c2 = fetch.cdx(re.sub(r"^https?://", "", href))
                c2 = [x for x in c2 if x["timestamp"] >= c["timestamp"][:8]] or c2
                if c2:
                    t2, *_ = fetch.get_html(f"https://web.archive.org/web/{c2[0]['timestamp']}id_/{c2[0]['original']}")
                    if t2:
                        docs.extend(crawl_products.parse_product_page(t2, c2[0]["original"])[1])
            for doc in docs:
                if not re.search(r"letter", doc["text"], re.I) or re.search(r"REMS|Dear Health|Filing|Proprietary|Complete Response", doc["text"]):
                    continue
                href = WB.sub("", doc["href"])
                ld = None
                m = letters.DATE_RE.search(doc.get("date") or doc["text"])
                if m:
                    ld = letters.iso(m)
                if ld and abs((d(ld) - ad).days) > 20:
                    continue
                if href in tried_pdf:
                    continue
                tried_pdf.add(href)
                r = letters.get_letter(href)
                parsed = letters.parse_letter(r["text"]) if r.get("text") else None
                ok = find_missing.letter_matches(parsed, appl, suppl, date)
                print("   cand", ld, doc["text"][:60], href[-40:], parsed and parsed.get("stns"), ok, flush=True)
                if r.get("sha256") and ok:
                    return {"via": "wayback_page", "url": r["url"], "sha256": r["sha256"], "n_bytes": r["n_bytes"],
                            "text": r["text"], "parsed": parsed, "source_page": wu, "link_text": doc["text"],
                            "wayback_pdf": r.get("wayback_url")}
    return None


def main():
    rows = [json.loads(l) for l in open(os.path.join(BASE, "year_page_rows.jsonl"))]
    prods = [json.loads(l) for l in open(os.path.join(BASE, "products.jsonl"))]
    prods += [json.loads(l) for l in open(os.path.join(BASE, "products_historic.jsonl"))]
    notfound = set()
    for fn in glob.glob(os.path.join(BASE, "found_letters_p*.jsonl")) + [os.path.join(BASE, "found_letters.jsonl")]:
        for line in open(fn):
            r = json.loads(line)
            if not r["found"]:
                notfound.add(r["action_row"])
    done = set()
    if os.path.exists(OUT):
        done = {json.loads(l)["action_row"] for l in open(OUT)}
    for i in sorted(notfound - done):
        row = rows[i]
        print(i, row["stn"], row["approval_date"], row["name"][:40], flush=True)
        hit = search(row, prods)
        rec = {"action_row": i, "stn": row["stn"], "approval_date": row["approval_date"], "found": bool(hit)}
        if hit:
            rec.update(hit)
        with open(OUT, "a") as f:
            f.write(json.dumps(rec) + "\n")
        print("   ->", hit["url"] if hit else "NOT FOUND", flush=True)


if __name__ == "__main__":
    main()
