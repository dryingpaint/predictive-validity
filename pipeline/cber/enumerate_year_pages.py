"""Step 1: enumerate every action listed on CBER yearly BLA / BLA-supplement pages, 2015-2025.

Pages for 2023 on are read live. Earlier years are read from the last Wayback capture of the
page's current URL and, for 2015-2019, of its old ucm URL. Their CDX capture lists live in
.cache/cber/cdx_yearpages.json, keyed '{year}|{kind}|{url}'; the step queries them when the
file is absent and reads the file otherwise.
"""
import datetime
import json
import os
import re
import urllib.parse

from bs4 import BeautifulSoup

from pipeline.cber import fetch

LIVE = "https://www.fda.gov/vaccines-blood-biologics/development-approval-process-cber/"
OLD = "www.fda.gov/BiologicsBloodVaccines/DevelopmentApprovalProcess/BiologicalApprovalsbyYear/"
OLD_UCM = {2015: ("ucm434961", "ucm434963"), 2016: ("ucm482397", "ucm482398"),
           2017: ("ucm547553", "ucm547555"), 2018: ("ucm596371", "ucm596373"),
           2019: ("ucm631669", "ucm631673")}
CDX_PATH = os.path.join(fetch.BASE, "cdx_yearpages.json")
KINDS = ("BLA", "SUPPL")


def norm_date(s):
    s = s.strip()
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{2,4})", s)
    if m:
        mo, d, y = m.groups()
        y = int(y)
        if y < 100:
            y += 2000
        return f"{y:04d}-{int(mo):02d}-{int(d):02d}"
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%B %d %Y", "%b. %d, %Y"):
        try:
            return datetime.datetime.strptime(re.sub(r"\s+", " ", s), fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return None


def parse_tables(html, page_url):
    """Rows of every STN table on a yearly approval page (BLA approvals / supplement noteworthy approvals)."""
    soup = BeautifulSoup(html, "lxml")
    root = soup.find("article") or soup.find("main") or soup.body
    out = []
    for tb in root.find_all("table"):
        rows = tb.find_all("tr")
        if not rows:
            continue
        header = [c.get_text(" ", strip=True).lower() for c in rows[0].find_all(["th", "td"])]
        if not any("stn" in h for h in header):
            continue
        idx = {}
        for i, h in enumerate(header):
            if "trade" in h or "proper" in h or "product" in h:
                idx.setdefault("name", i)
            elif "indication" in h or "use" in h:
                idx.setdefault("indication", i)
            elif "stn" in h:
                idx.setdefault("stn", i)
            elif "manufact" in h or "licens" in h or "applicant" in h:
                idx.setdefault("mfr", i)
            elif "date" in h:
                idx.setdefault("date", i)
        for r in rows[1:]:
            cells = r.find_all(["td", "th"])
            if len(cells) < 3:
                continue
            txt = [re.sub(r"\s+", " ", c.get_text(" ", strip=True)) for c in cells]
            def g(k):
                i = idx.get(k)
                return txt[i] if i is not None and i < len(txt) else ""
            links = []
            for a in r.find_all("a"):
                h = a.get("href")
                if h:
                    links.append({"href": urllib.parse.urljoin(page_url, h), "text": a.get_text(" ", strip=True)})
            out.append({"name": g("name"), "indication": g("indication"), "stn": g("stn"),
                        "manufacturer": g("mfr"), "date_raw": g("date"),
                        "approval_date": norm_date(g("date")), "links": links,
                        "row_text": " | ".join(txt)})
    return out


def split_stn(stn):
    """'125643/123' -> ('125643', '123'); '125812/0' -> ('125812','0')."""
    m = re.search(r"(\d{5,6})\s*/\s*(\d+)", stn or "")
    if m:
        return m.group(1), str(int(m.group(2)))
    m = re.search(r"(\d{5,6})", stn or "")
    return (m.group(1), None) if m else (None, None)


def candidates(year, kind):
    """Scheme-less URLs of one yearly page: its current URL, then for 2015-2019 its old ucm URL."""
    slug = (f"{year}-biological-license-application-approvals" if kind == "BLA"
            else f"{year}-biological-license-application-supplement-noteworthy-approvals")
    out = [LIVE.removeprefix("https://") + slug]
    if year in OLD_UCM:
        out.append(OLD + OLD_UCM[year][0 if kind == "BLA" else 1] + ".htm")
    return out


def sources(year, kind, cdx):
    """Pages to parse for one yearly page: the live page from 2023 on, else the last capture of each candidate."""
    if year >= 2023:
        return ["https://" + candidates(year, kind)[0]]
    out = []
    for c in candidates(year, kind):
        caps = cdx.get(f"{year}|{kind}|{c}")
        if caps:
            out.append(fetch.wayback(caps[-1]))
    return out


def main():
    if not os.path.exists(CDX_PATH):
        caps = {f"{year}|{kind}|{c}": fetch.cdx(c)
                for year in range(2015, 2023) for kind in KINDS for c in candidates(year, kind)}
        with open(CDX_PATH, "w") as f:
            json.dump(caps, f, indent=1)
    with open(CDX_PATH) as f:
        cdx = json.load(f)
    rows_out = []
    status = []
    for year in range(2015, 2026):
        for kind in KINDS:
            seen = {}
            for url in sources(year, kind, cdx):
                t, path, final, st = fetch.get_html(url)
                if not t:
                    status.append({"year": year, "kind": kind, "url": url, "status": st, "rows": 0})
                    continue
                rows = parse_tables(t, url.split("id_/", 1)[-1])
                status.append({"year": year, "kind": kind, "url": url, "status": st, "rows": len(rows),
                               "html": os.path.basename(path)})
                for r in rows:
                    if not r["stn"] and not r["name"]:
                        continue
                    key = (r["stn"].replace(" ", ""), r["approval_date"], r["name"][:30])
                    if key in seen:
                        seen[key]["listing_pages"].append(url)
                        continue
                    appl, sub = split_stn(r["stn"])
                    rec = {"list_year": year, "list_kind": kind, "appl_no": appl, "stn_suppl": sub,
                           **r, "listing_page": url, "listing_pages": [url],
                           "listing_html": os.path.basename(path)}
                    seen[key] = rec
            rows_out.extend(seen.values())
            print(year, kind, len(seen), flush=True)
    fetch.write_jsonl("year_page_rows.jsonl", rows_out)
    with open(os.path.join(fetch.BASE, "year_page_status.json"), "w") as f:
        json.dump(status, f, indent=1)


if __name__ == "__main__":
    main()
