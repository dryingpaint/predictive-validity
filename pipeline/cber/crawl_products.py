"""Step 2: build the CBER product universe and crawl each product page for document links."""
import os
import re
import urllib.parse

from bs4 import BeautifulSoup

from pipeline.cber import fetch

FDA = "https://www.fda.gov"
LISTS = {
    "master": "https://www.fda.gov/vaccines-blood-biologics/cber-regulated-products-supporting-documents",
    "cgt": "https://www.fda.gov/vaccines-blood-biologics/cellular-gene-therapy-products/approved-cellular-and-gene-therapy-products",
    "vaccines": "https://www.fda.gov/vaccines-blood-biologics/vaccines/vaccines-licensed-use-united-states",
    "blood": "https://www.fda.gov/vaccines-blood-biologics/blood-blood-products/approved-blood-products",
    "fractionated": "https://www.fda.gov/vaccines-blood-biologics/approved-blood-products/fractionated-plasma-products",
    "allergenics": "https://www.fda.gov/vaccines-blood-biologics/allergenics",
    "fmt": "https://www.fda.gov/vaccines-blood-biologics/fecal-microbiota-products",
    "tissue": "https://www.fda.gov/vaccines-blood-biologics/tissue-tissue-products",
}
SKIP_PREFIX = ("/vaccines-blood-biologics/development-approval-process-cber",)
NAV = {"/vaccines-blood-biologics", "/vaccines-blood-biologics/infectious-disease-tests",
       "/vaccines-blood-biologics/cber-reports",
       "/vaccines-blood-biologics/center-biologics-evaluation-and-research-cber-product-approval-information",
       "/vaccines-blood-biologics/fecal-microbiota-products", "/vaccines-blood-biologics/allergenics",
       "/vaccines-blood-biologics/blood-blood-products", "/vaccines-blood-biologics/blood-donor-screening",
       "/vaccines-blood-biologics/cellular-gene-therapy-products",
       "/vaccines-blood-biologics/guidance-compliance-regulatory-information-biologics",
       "/vaccines-blood-biologics/international-activities", "/vaccines-blood-biologics/news-events-biologics",
       "/vaccines-blood-biologics/resources-you-biologics", "/vaccines-blood-biologics/safety-availability-biologics",
       "/vaccines-blood-biologics/science-research-biologics", "/vaccines-blood-biologics/tissue-tissue-products",
       "/vaccines-blood-biologics/vaccines", "/vaccines-blood-biologics/xenotransplantation"}


def canon(href, base):
    u = urllib.parse.urljoin(base, href)
    p = urllib.parse.urlparse(u)
    if p.netloc not in ("www.fda.gov", "fda.gov"):
        return None
    path = p.path.rstrip("/")
    if not path.startswith("/vaccines-blood-biologics/") or path in NAV or path.startswith(SKIP_PREFIX):
        return None
    return FDA + path


def product_universe():
    prods = {}
    # master table
    t, *_ = fetch.get_html(LISTS["master"])
    soup = BeautifulSoup(t, "lxml")
    art = soup.find("article")
    for tr in art.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 2:
            continue
        a = tr.find("a")
        if not a or not a.get("href"):
            continue
        u = canon(a["href"], LISTS["master"])
        if not u:
            continue
        cells = [re.sub(r"\s+", " ", c.get_text(" ", strip=True)) for c in tds]
        prods.setdefault(u, {"url": u, "sources": []})
        prods[u].update({"proper_name": cells[0], "trade_name": cells[1] if len(cells) > 1 else "",
                         "manufacturer": cells[2] if len(cells) > 2 else ""})
        prods[u]["sources"].append("master")
    for key in ("cgt", "vaccines", "blood", "fractionated", "fmt", "tissue", "allergenics"):
        t, *_ = fetch.get_html(LISTS[key])
        if not t:
            print("list fail", key)
            continue
        soup = BeautifulSoup(t, "lxml")
        art = soup.find("article") or soup
        for a in art.find_all("a"):
            if not a.get("href") or a["href"].startswith("#") or "/media/" in a["href"]:
                continue
            u = canon(a["href"], LISTS[key])
            if not u:
                continue
            prods.setdefault(u, {"url": u, "sources": []})
            prods[u].setdefault("link_text", a.get_text(" ", strip=True))
            if key not in prods[u]["sources"]:
                prods[u]["sources"].append(key)
    # yearly-page links
    for r in fetch.read_jsonl("year_page_rows.jsonl"):
        for l in r["links"]:
            u = canon(fetch.unwayback(l["href"]), FDA)
            if not u:
                continue
            prods.setdefault(u, {"url": u, "sources": []})
            prods[u].setdefault("link_text", l["text"])
            if "yearpage" not in prods[u]["sources"]:
                prods[u]["sources"].append("yearpage")
    return prods


DATE_RE = re.compile(r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})")


def parse_product_page(html, url):
    soup = BeautifulSoup(html, "lxml")
    art = soup.find("article") or soup
    text = re.sub(r"\s+", " ", art.get_text(" ", strip=True))
    info = {}
    m = re.search(r"STN:?\s*(?:BLA?|BL)?\s*#?\s*([0-9]{5,6}(?:\s*[,&/]\s*(?:BL\s*)?[0-9]{5,6})*)", text)
    if m:
        info["stn_text"] = m.group(1)
        info["stns"] = re.findall(r"\d{5,6}", m.group(1))
    for k, pat in (("proper_name", r"Proper Name:\s*(.*?)\s+(?:Trade ?name|Tradename|Manufacturer|Indication)"),
                   ("trade_name", r"Trade ?name:\s*(.*?)\s+(?:Manufacturer|Indication|Proper)"),
                   ("manufacturer", r"Manufacturer:\s*(.*?)\s+(?:Indications?|Product Information|Proper|Trade)")):
        m = re.search(pat, text, re.I)
        if m:
            info[k] = m.group(1)[:300]
    m = re.search(r"Indications?:?\s*(.*?)\s*(?:Product Information|Supporting Documents|Package Insert)", text)
    if m:
        info["indication_text"] = m.group(1)[:3000]
    docs = []
    subpages = []
    for a in art.find_all("a"):
        href = a.get("href")
        if not href or href.startswith("#"):
            continue
        txt = re.sub(r"\s+", " ", a.get_text(" ", strip=True))
        full = urllib.parse.urljoin(url, href)
        if "/media/" in full or full.lower().endswith(".pdf"):
            dm = DATE_RE.search(txt)
            docs.append({"text": txt, "href": full, "date": dm.group(0) if dm else None})
        elif re.search(r"approval history|letters, reviews|supporting documents", txt, re.I):
            subpages.append({"text": txt, "href": full})
    return info, docs, subpages, text[:6000]


def main():
    prods = product_universe()
    print("candidate urls", len(prods), flush=True)
    merged = {}
    for i, (u, p) in enumerate(sorted(prods.items())):
        t, path, final, st = fetch.get_html(u)
        final = (final or u).split("?")[0].split("#")[0].rstrip("/")
        if final in merged:
            merged[final]["aliases"].append(u)
            for s_ in p["sources"]:
                if s_ not in merged[final]["sources"]:
                    merged[final]["sources"].append(s_)
            for k in ("proper_name", "trade_name", "manufacturer"):
                if p.get(k) and not merged[final].get("list_" + k):
                    merged[final]["list_" + k] = p[k]
            continue
        rec = {"url": final, "aliases": [u], "sources": list(p["sources"]), "link_text": p.get("link_text"),
               "list_proper_name": p.get("proper_name"), "list_trade_name": p.get("trade_name"),
               "list_manufacturer": p.get("manufacturer"),
               "status": st, "html": os.path.basename(path) if path else None}
        if t:
            info, docs, subs, text = parse_product_page(t, final)
            rec.update(info)
            rec["docs"] = docs
            rec["subpages"] = subs
            rec["page_text"] = text
            for sp in subs:
                if "/media/" in sp["href"] or not sp["href"].startswith("https://www.fda.gov"):
                    continue
                t2, path2, final2, st2 = fetch.get_html(sp["href"])
                sp["status"] = st2
                sp["html"] = os.path.basename(path2) if path2 else None
                if t2:
                    _, docs2, _, _ = parse_product_page(t2, sp["href"])
                    for d in docs2:
                        d["from_subpage"] = sp["href"]
                    rec["docs"].extend(docs2)
        merged[final] = rec
        if i % 25 == 0:
            print(i, u, st, len(rec.get("docs", [])), flush=True)
    fetch.write_jsonl("products.jsonl", merged.values())
    print("products", len(merged))


if __name__ == "__main__":
    main()
