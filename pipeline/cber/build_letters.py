"""Step 4: join downloaded letters with the product pages that link them; one row per (letter, STN)."""
import json
import os
import re

from pipeline.cber import fetch
from pipeline.cber import letters

BASE = fetch.BASE


def load_texts():
    d = {}
    import glob
    for p in sorted(glob.glob(os.path.join(BASE, "letters_text*.jsonl"))):
        if True:
            for line in open(p):
                r = json.loads(line)
                if r["url"] not in d or r.get("sha256"):
                    d[r["url"]] = r
    return d


def main():
    texts = load_texts()
    prods = [json.loads(l) for l in open(os.path.join(BASE, "products.jsonl"))]
    hist = [json.loads(l) for l in open(os.path.join(BASE, "products_historic.jsonl"))]
    rows = []
    seen = set()
    for p in prods + hist:
        page = p.get("final_url") or p.get("url") or p.get("hist_url")
        src_page = p.get("wayback_url") or page
        for d in p.get("docs", []):
            if not re.search(r"letter", d["text"], re.I):
                continue
            u = letters.canon_media(d["href"])
            key = (u, page)
            if key in seen:
                continue
            seen.add(key)
            t = texts.get(u)
            row = {"doc_url": u, "link_text": d["text"], "link_date": d.get("date"),
                   "source_page": d.get("from_subpage") or src_page, "product_page": page,
                   "page_trade_name": p.get("trade_name") or p.get("list_trade_name") or p.get("link_text"),
                   "page_proper_name": p.get("proper_name") or p.get("list_proper_name"),
                   "page_manufacturer": p.get("manufacturer") or p.get("list_manufacturer"),
                   "page_stns": p.get("stns"), "downloaded": bool(t and t.get("sha256"))}
            if t:
                row.update({"sha256": t.get("sha256"), "n_bytes": t.get("n_bytes"), "fetch_error": t.get("error"),
                            "wayback_pdf": t.get("wayback_url")})
                if t.get("text"):
                    row.update(letters.parse_letter(t["text"]))
            rows.append(row)
    with open(os.path.join(BASE, "letters_parsed.jsonl"), "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(len(rows))


if __name__ == "__main__":
    main()
