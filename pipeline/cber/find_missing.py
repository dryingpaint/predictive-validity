"""Step 5: for in-scope yearly-page actions with no letter on the product pages, look on Wayback
captures of the product page taken after the action date. Appends one record per searched action
to found_letters.jsonl; actions already recorded in any found_letters*.jsonl are skipped."""
import datetime
import json
import os
import re

from pipeline.cber import crawl_products
from pipeline.cber import decisions
from pipeline.cber import fetch
from pipeline.cber import letters


def wayback_pages(action, prods):
    """Pages to look up on Wayback: the action's yearly-page links, then the product pages listing its BLA."""
    urls = []
    for l in action["links"]:
        u = fetch.unwayback(l["href"])
        if "fda.gov" in u and u not in urls:
            urls.append(u)
    for p in prods:
        if action["appl_no"] in (p.get("stns") or []):
            for u in [p.get("final_url") or p.get("url")] + p.get("aliases", []):
                if u and u not in urls:
                    urls.append(u)
    return urls


def capture_docs(cap):
    """(docs, file_links) of one Wayback capture of a product page. docs holds the page's document
    links, then those of each html sub-page ('Approval History, Letters, Reviews', where old pages
    kept their letters) at its first capture on or after cap's day; file_links holds the sub-page
    links that point at a file (media/, .pdf, .zip). Both are empty when the capture does not load."""
    t, *_ = fetch.get_html(fetch.wayback(cap))
    if not t:
        return [], []
    _, docs, subs, _ = crawl_products.parse_product_page(t, cap["original"])
    files = []
    for sp in subs:
        href = fetch.unwayback(sp["href"])
        if "/media/" in href or href.lower().endswith((".pdf", ".zip")):
            files.append({"text": sp["text"], "href": href, "date": None})
            continue
        c2 = fetch.cdx(href)
        c2 = [x for x in c2 if x["timestamp"] >= cap["timestamp"][:8]] or c2
        if c2:
            t2, *_ = fetch.get_html(fetch.wayback(c2[0]))
            if t2:
                docs.extend(crawl_products.parse_product_page(t2, c2[0]["original"])[1])
    return docs, files


def found_record(r, parsed, source_page, link_text):
    """The record of a letter found for an action: the get_letter result, its parse and where it was linked."""
    return {"via": "wayback_page", "url": r["url"], "sha256": r["sha256"], "n_bytes": r["n_bytes"],
            "text": r["text"], "parsed": parsed, "source_page": source_page, "link_text": link_text,
            "wayback_pdf": r.get("wayback_url")}


def try_wayback(action, prods):
    appl, suppl, date = action["appl_no"], action["stn_suppl"], action["approval_date"]
    ad = datetime.date.fromisoformat(date)
    tried = set()
    for u in wayback_pages(action, prods):
        caps = [c for c in fetch.cdx(u) if c["timestamp"][:8] >= date.replace("-", "")]
        if not caps:
            continue
        later = [x for x in caps if x["timestamp"][:8] >= (ad + datetime.timedelta(days=90)).strftime("%Y%m%d")]
        pick = [caps[0]] + later[:1] + [caps[-1]]
        for c in pick:
            if c["timestamp"] in tried:
                continue
            tried.add(c["timestamp"])
            docs, files = capture_docs(c)
            cands = []
            for doc in docs + files:
                if not re.search(r"letter", doc["text"], re.I) or re.search(r"REMS|Dear Health", doc["text"]):
                    continue
                href = fetch.unwayback(doc["href"])
                ld = None
                if doc.get("date"):
                    m = letters.DATE_RE.search(doc["date"])
                    ld = letters.iso(m) if m else None
                if ld and abs((datetime.date.fromisoformat(ld) - ad).days) > 10:
                    continue
                cands.append((0 if ld else 1, href, doc["text"]))
            for _, href, text in sorted(cands)[:6]:
                r = letters.get_letter(href)
                parsed = letters.parse_letter(r["text"]) if r.get("text") else None
                if r.get("sha256") and letters.letter_matches(parsed, appl, suppl, date):
                    return found_record(r, parsed, fetch.wayback(c), text)
    return None


def main():
    rows = fetch.read_jsonl("year_page_rows.jsonl")
    prods = fetch.read_jsonl("products.jsonl") + fetch.read_jsonl("products_historic.jsonl")
    dec = decisions.decisions(rows)
    done = letters.found_letters()
    res = letters.match_actions(rows, fetch.read_jsonl("letters_parsed.jsonl"))
    for i, (a, c, _) in enumerate(res):
        _, in_scope = dec[i]
        if not in_scope or c or i in done:
            continue
        print(i, a["stn"], a["approval_date"], a["name"][:40], flush=True)
        hit = try_wayback(a, prods)
        rec = {"action_row": i, "stn": a["stn"], "approval_date": a["approval_date"], "found": bool(hit)}
        if hit:
            rec.update(hit)
        with open(os.path.join(fetch.BASE, "found_letters.jsonl"), "a") as f:
            f.write(json.dumps(rec) + "\n")
        print("   ->", hit["via"] if hit else "NOT FOUND", hit.get("url") if hit else "", flush=True)


if __name__ == "__main__":
    main()
