"""Step 5: for yearly-page actions with no letter on the current product pages, look
(a) inside the product's 'Approval History, Letters, Reviews' zip archives and
(b) on Wayback captures of the product page taken after the action date."""
import datetime
import json
import os
import re

from pipeline.cber import crawl_products
from pipeline.cber import fetch
from pipeline.cber import letters
from pipeline.cber import match
from pipeline.cber import yearly_decisions
from pipeline.cber import zipletters

BASE = fetch.BASE
OUT = os.environ.get("CBER_FOUND_OUT", os.path.join(BASE, "found_letters.jsonl"))
WB = re.compile(r"^https?://web\.archive\.org/web/\d+[a-z_]*/")


def d(s):
    return datetime.date.fromisoformat(s)


def product_pages_for(appl, prods):
    out = []
    for p in prods:
        if appl in (p.get("stns") or []) or appl in (p.get("page_stns") or []):
            out.append(p)
    return out


def done_keys():
    import glob
    keys = set()
    for fn in glob.glob(os.path.join(BASE, "found_letters*.jsonl")):
        for line in open(fn):
            r = json.loads(line)
            keys.add(r["action_row"])
    return keys


def emit(rec):
    with open(OUT, "a") as f:
        f.write(json.dumps(rec) + "\n")


def letter_matches(parsed, appl, suppl, date):
    if not parsed:
        return False
    for a, s in parsed.get("stns") or []:
        if a == appl and suppl is not None and s == suppl:
            return True
    ld = parsed.get("letter_date")
    if ld and any(a == appl for a, _ in parsed.get("stns") or []) and abs((d(ld) - d(date)).days) <= 7:
        return True
    return False


def try_zips(action, prods):
    appl, suppl, date = action["appl_no"], action["stn_suppl"], action["approval_date"]
    for p in product_pages_for(appl, prods):
        for doc in p.get("docs", []):
            if not re.search(r"Approval History|Letters, Reviews|Related Documents", doc["text"], re.I):
                continue
            try:
                found, names = zipletters.extract_letters(doc["href"])
            except Exception as e:  # noqa: BLE001
                print("  zip error", doc["href"], e, flush=True)
                continue
            for f in found:
                parsed = letters.parse_letter(f["text"]) if f.get("text") else None
                if letter_matches(parsed, appl, suppl, date):
                    return {"via": "zip", "url": f["zip_url"], "zip_member": f["member"], "sha256": f["sha256"],
                            "n_bytes": f["n_bytes"], "text": f["text"], "parsed": parsed,
                            "source_page": p.get("final_url") or p.get("url")}
    return None


def wayback_pages(action, prods):
    urls = []
    for l in action["links"]:
        u = WB.sub("", l["href"])
        if "fda.gov" in u and u not in urls:
            urls.append(u)
    for p in product_pages_for(action["appl_no"], prods):
        for u in [p.get("final_url") or p.get("url")] + p.get("aliases", []):
            if u and u not in urls:
                urls.append(u)
    return urls


def try_wayback(action, prods):
    appl, suppl, date = action["appl_no"], action["stn_suppl"], action["approval_date"]
    ad = d(date)
    tried = set()
    for u in wayback_pages(action, prods):
        caps = fetch.cdx(re.sub(r"^https?://", "", u))
        caps = [c for c in caps if d(f"{c['timestamp'][:4]}-{c['timestamp'][4:6]}-{c['timestamp'][6:8]}") >= ad]
        if not caps:
            continue
        later = [x for x in caps if x["timestamp"][:8] >= (ad + datetime.timedelta(days=90)).strftime("%Y%m%d")]
        pick = [caps[0]] + later[:1] + [caps[-1]]
        for c in pick:
            if c["timestamp"] in tried:
                continue
            tried.add(c["timestamp"])
            wu = f"https://web.archive.org/web/{c['timestamp']}id_/{c['original']}"
            t, path, final, st = fetch.get_html(wu)
            if not t:
                continue
            _, docs, subs, _ = crawl_products.parse_product_page(t, c["original"])
            for sp in subs:  # old pages kept letters on an 'Approval History, Letters, Reviews' html sub-page
                href = WB.sub("", sp["href"])
                if "/media/" in href or href.lower().endswith((".pdf", ".zip")):
                    docs.append({"text": sp["text"], "href": href, "date": None})
                    continue
                c2 = fetch.cdx(re.sub(r"^https?://", "", href))
                c2 = [x for x in c2 if x["timestamp"] >= c["timestamp"][:8]] or c2
                if c2:
                    wu2 = f"https://web.archive.org/web/{c2[0]['timestamp']}id_/{c2[0]['original']}"
                    t2, *_ = fetch.get_html(wu2)
                    if t2:
                        _, docs2, _, _ = crawl_products.parse_product_page(t2, c2[0]["original"])
                        docs.extend(docs2)
            cands = []
            for doc in docs:
                if not re.search(r"letter", doc["text"], re.I) or re.search(r"REMS|Dear Health", doc["text"]):
                    continue
                href = WB.sub("", doc["href"])
                ld = None
                if doc.get("date"):
                    m = letters.DATE_RE.search(doc["date"])
                    ld = letters.iso(m) if m else None
                if ld and abs((d(ld) - ad).days) > 10:
                    continue
                cands.append((0 if ld else 1, href, doc["text"]))
            for _, href, text in sorted(cands)[:6]:
                r = letters.get_letter(href)
                parsed = letters.parse_letter(r["text"]) if r.get("text") else None
                if r.get("sha256") and letter_matches(parsed, appl, suppl, date):
                    return {"via": "wayback_page", "url": r["url"], "sha256": r["sha256"], "n_bytes": r["n_bytes"],
                            "text": r["text"], "parsed": parsed, "source_page": wu, "link_text": text,
                            "wayback_pdf": r.get("wayback_url")}
    return None


def main():
    rows = [json.loads(l) for l in open(os.path.join(BASE, "year_page_rows.jsonl"))]
    prods = [json.loads(l) for l in open(os.path.join(BASE, "products.jsonl"))]
    prods += [json.loads(l) for l in open(os.path.join(BASE, "products_historic.jsonl"))]
    lrows = [json.loads(l) for l in open(os.path.join(BASE, "letters_parsed.jsonl"))]
    dec = yearly_decisions.decisions()
    res = match.match_actions(rows, lrows)
    done = done_keys()
    import sys
    part, nparts = (int(sys.argv[1]), int(sys.argv[2])) if len(sys.argv) > 2 else (0, 1)
    todo = [i for i, (a, c, how) in enumerate(res) if dec[i]["in_scope"] and not c and i not in done]
    mine = set(todo[part::nparts])
    for i, (a, c, how) in enumerate(res):
        if i not in mine:
            continue
        print(i, a["stn"], a["approval_date"], a["name"][:40], flush=True)
        hit = try_wayback(a, prods)
        if not hit:
            hit = try_zips(a, prods)
        rec = {"action_row": i, "stn": a["stn"], "approval_date": a["approval_date"], "found": bool(hit)}
        if hit:
            rec.update(hit)
        emit(rec)
        print("   ->", hit["via"] if hit else "NOT FOUND", hit.get("url") if hit else "", flush=True)


if __name__ == "__main__":
    main()
