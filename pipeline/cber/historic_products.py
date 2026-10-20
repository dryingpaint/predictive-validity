"""Step 2b: product pages that were on historical snapshots of the CBER master list (2014-2025)
or linked from yearly pages but are no longer live. Resolve via live fetch, else the last Wayback capture."""
import json
import os
import re

from pipeline.cber import crawl_products
from pipeline.cber import fetch

BASE = fetch.BASE
WB = re.compile(r"^https?://web\.archive\.org/web/\d+[a-z_]*/")


def norm(u):
    u = re.sub(r"^https?://(www\.)?fda\.gov(:80)?", "https://www.fda.gov", u.strip())
    return u.split("#")[0].split("?")[0].rstrip("/")


def wayback_page(url):
    caps = fetch.cdx(re.sub(r"^https?://", "", url))
    caps = [c for c in caps if "page-not-found" not in c["original"]]
    if not caps:
        return None
    c = caps[-1]
    wu = f"https://web.archive.org/web/{c['timestamp']}id_/{c['original']}"
    t, path, final, st = fetch.get_html(wu)
    if not t:
        return {"wayback_url": wu, "status": st}
    info, docs, subs, text = crawl_products.parse_product_page(t, c["original"])
    for d in docs:
        d["href"] = WB.sub("", d["href"])
    rec = {"wayback_url": wu, "status": 200, "html": os.path.basename(path), "docs": docs, "page_text": text, **info}
    for sp in subs:
        href = WB.sub("", sp["href"])
        if "/media/" in href or "/downloads/" in href.lower() or href.lower().endswith(".pdf"):
            continue
        caps2 = fetch.cdx(re.sub(r"^https?://", "", href))
        if not caps2:
            continue
        c2 = caps2[-1]
        wu2 = f"https://web.archive.org/web/{c2['timestamp']}id_/{c2['original']}"
        t3, p3, _, _ = fetch.get_html(wu2)
        if t3:
            _, docs3, _, _ = crawl_products.parse_product_page(t3, c2["original"])
            for d in docs3:
                d["href"] = WB.sub("", d["href"])
                d["from_subpage"] = wu2
            rec["docs"].extend(docs3)
    return rec


def main():
    cur = [json.loads(l) for l in open(os.path.join(BASE, "products.jsonl"))]
    targets = []
    for p in cur:
        if p.get("status") != 200:
            for a in p["aliases"]:
                targets.append({"why": "current_404", "url": a, "names": [p.get("link_text")]})
    for h in json.load(open(os.path.join(BASE, "historic_missing.json"))):
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
    with open(os.path.join(BASE, "products_historic.jsonl"), "w") as f:
        for r in out:
            f.write(json.dumps(r) + "\n")


if __name__ == "__main__":
    main()
