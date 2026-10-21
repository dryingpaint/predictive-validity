"""Step 2b: product pages that are no longer live: crawl_products pages that did not load, and the
rows of pipeline/cber/historic_missing.json. Resolve via live fetch, else the last Wayback capture.

historic_missing.json is a pinned input that no step rebuilds. It was read off the CBER master list
of products and supporting documents in its Wayback snapshots of 2014-2025 and holds the rows whose
product pages the live list no longer links: each row's cells, every href it had with the last
snapshot that listed that href, and the row's first and last snapshot.
"""
import json
import os
import re
from pathlib import Path

from pipeline.cber import crawl_products
from pipeline.cber import fetch

HISTORIC_MISSING = Path(__file__).with_name("historic_missing.json")


def norm(u):
    u = re.sub(r"^https?://(www\.)?fda\.gov(:80)?", "https://www.fda.gov", u.strip())
    return u.split("#")[0].split("?")[0].rstrip("/")


def wayback_page(url):
    caps = fetch.cdx(url)
    caps = [c for c in caps if "page-not-found" not in c["original"]]
    if not caps:
        return None
    c = caps[-1]
    wu = fetch.wayback(c)
    t, path, final, st = fetch.get_html(wu)
    if not t:
        return {"wayback_url": wu, "status": st}
    info, docs, subs, text = crawl_products.parse_product_page(t, c["original"])
    for d in docs:
        d["href"] = fetch.unwayback(d["href"])
    rec = {"wayback_url": wu, "status": 200, "html": os.path.basename(path), "docs": docs, "page_text": text, **info}
    for sp in subs:
        href = fetch.unwayback(sp["href"])
        if "/media/" in href or "/downloads/" in href.lower() or href.lower().endswith(".pdf"):
            continue
        caps2 = fetch.cdx(href)
        if not caps2:
            continue
        c2 = caps2[-1]
        wu2 = fetch.wayback(c2)
        t3, p3, _, _ = fetch.get_html(wu2)
        if t3:
            _, docs3, _, _ = crawl_products.parse_product_page(t3, c2["original"])
            for d in docs3:
                d["href"] = fetch.unwayback(d["href"])
                d["from_subpage"] = wu2
            rec["docs"].extend(docs3)
    return rec


def main():
    targets = []
    for p in fetch.read_jsonl("products.jsonl"):
        if p.get("status") != 200:
            for a in p["aliases"]:
                targets.append({"why": "current_404", "url": a, "names": [p.get("link_text")]})
    with open(HISTORIC_MISSING) as f:
        historic = json.load(f)
    for h in historic:
        hrefs = sorted(h["hrefs"].items(), key=lambda x: x[1])
        targets.append({"why": "historic_missing", "url": norm(hrefs[-1][0]), "names": h["cells"],
                        "first": h["first"], "last": h["last"], "all_hrefs": [x[0] for x in hrefs]})
    out = []
    for t in targets:
        rec = dict(t)
        txt, path, final, st = fetch.get_html(t["url"])
        if txt and "page-not-found" not in (final or ""):
            info, docs, subs, text = crawl_products.parse_product_page(txt, final)
            rec.update({"resolved": "live", "final_url": final, "html": os.path.basename(path), "docs": docs,
                        "page_text": text, **info})
        else:
            w = None
            for u in [t["url"]] + [x for x in t.get("all_hrefs", []) if norm(x) != t["url"]][::-1]:
                w = wayback_page(u)
                if w and w.get("status") == 200:
                    break
            if w and w.get("status") == 200:
                rec.update({"resolved": "wayback", **w})
            else:
                rec["resolved"] = "unresolved"
        out.append(rec)
        print(rec["resolved"], t["url"][-80:], len(rec.get("docs", [])), flush=True)
    fetch.write_jsonl("products_historic.jsonl", out)


if __name__ == "__main__":
    main()
