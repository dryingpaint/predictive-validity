"""Step 4: join downloaded letters with the product pages that link them; one row per (letter, STN)."""
import re

from pipeline.cber import fetch
from pipeline.cber import letters


def main():
    texts = letters.texts()
    rows = []
    seen = set()
    for p in fetch.read_jsonl("products.jsonl") + fetch.read_jsonl("products_historic.jsonl"):
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
    fetch.write_jsonl("letters_parsed.jsonl", rows)
    print(len(rows))


if __name__ == "__main__":
    main()
