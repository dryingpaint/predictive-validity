"""Parse CBER yearly approval tables (BLA approvals / BLA supplement noteworthy approvals)."""
import re
import urllib.parse

from bs4 import BeautifulSoup


def norm_date(s):
    s = s.strip()
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{2,4})", s)
    if m:
        mo, d, y = m.groups()
        y = int(y)
        if y < 100:
            y += 2000
        return f"{y:04d}-{int(mo):02d}-{int(d):02d}"
    import datetime
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%B %d %Y", "%b. %d, %Y"):
        try:
            return datetime.datetime.strptime(re.sub(r"\s+", " ", s), fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return None


def parse_tables(html, page_url):
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
