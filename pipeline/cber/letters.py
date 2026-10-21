"""CBER letter PDFs: download, extract text with pypdf, parse STN / date / sponsor / purpose, and
match letters to yearly-page actions."""
import datetime
import functools
import glob
import json
import os
import re

import pypdf

from pipeline.cber import fetch

MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
DATE_RE = re.compile(rf"({MONTHS})\s+(\d{{1,2}})\s*,?\s*(\d{{4}})")
MNUM = {m: i + 1 for i, m in enumerate(MONTHS.split("|"))}


def iso(m):
    return f"{int(m.group(3)):04d}-{MNUM[m.group(1)]:02d}-{int(m.group(2)):02d}"


def canon_media(u):
    u = re.sub(r"^https?://(web\.archive\.org/web|wayback\.archive-it\.org/\d+)/\d+[a-z_]*/", "", u)
    m = re.search(r"fda\.gov/media/(\d+)(?:/download)?(?:[?/#]|$)", u)
    return f"https://www.fda.gov/media/{m.group(1)}/download" if m else u


@functools.cache
def texts():
    """{letter url: download record} over letters_text*.jsonl in name order: the first record per url,
    replaced by any later one that has a PDF hash. get_letter appends to letters_text.jsonl and to this dict."""
    d = {}
    for name in sorted(glob.glob("letters_text*.jsonl", root_dir=fetch.BASE)):
        for r in fetch.read_jsonl(name):
            if r["url"] not in d or r.get("sha256"):
                d[r["url"]] = r
    return d


def wayback_pdf(url):
    """Find an archived copy of a PDF URL on the Wayback Machine; returns fetch.get_pdf-style dict."""
    variants = [url, url + "?attachment", url.replace("https://", "http://")]
    for v in variants:
        caps = fetch.cdx(v)
        caps = [c for c in caps if c.get("mimetype", "").endswith("pdf") or c.get("mimetype") == "application/octet-stream"] or caps
        for c in reversed(caps[-3:]):
            wu = fetch.wayback(c)
            r = fetch.get_pdf(wu)
            if r.get("sha256"):
                r["wayback_url"] = wu
                return r
    return None


def get_letter(url):
    """Download (cached) and extract a letter; returns dict with sha256, n_bytes, text, error.
    Falls back to the Wayback Machine copy when fda.gov no longer serves the file."""
    url = canon_media(url)
    c = texts()
    if url in c and (c[url].get("sha256") or c[url].get("wayback_tried")):
        return c[url]
    r = fetch.get_pdf(url) if url not in c else {"status": c[url].get("status"), "error": c[url].get("error")}
    rec = {"url": url, "status": r.get("status"), "sha256": r.get("sha256"), "n_bytes": r.get("n_bytes"),
           "error": r.get("error"), "text": None, "n_pages": None, "wayback_url": None}
    if not r.get("sha256"):
        rec["wayback_tried"] = True
        w = wayback_pdf(url)
        if w:
            r = w
            rec.update({"sha256": w["sha256"], "n_bytes": w["n_bytes"], "error": None,
                        "wayback_url": w["wayback_url"]})
    if r.get("path"):
        try:
            rd = pypdf.PdfReader(r["path"])
            rec.update({"text": "\n".join((p.extract_text() or "") for p in rd.pages), "n_pages": len(rd.pages)})
        except Exception as e:  # noqa: BLE001
            rec.update({"text": "", "n_pages": 0, "error": f"pdf_text_error: {e}"})
        else:
            if len(rec["text"].strip()) < 200:
                rec["error"] = "little_or_no_text"
    c[url] = rec
    with open(os.path.join(fetch.BASE, "letters_text.jsonl"), "a") as f:
        f.write(json.dumps(rec) + "\n")
    return rec


STN_RE = re.compile(r"(?:STN|BLA|BL)\s*[:#]?\s*(?:BLA?\s*|BL\s*)?(1\d{5}|10\d{4})\s*/\s*(\d{1,5})")


_MONTH_ALTS = {m: [m] for m in MONTHS.split("|")}
_MONTH_ALTS["February"].append("Februray")
_FUZZY_MONTH = "|".join(
    "(?:" + "|".join(r"\s*".join(re.escape(ch) for ch in alt) for alt in alts) + ")"
    for alts in _MONTH_ALTS.values())
_FUZZY_DATE = re.compile(r"(" + _FUZZY_MONTH + r")\s*(\d{1,2})\s*,?\s*(\d{4})", re.I)
_NUM_DATE = re.compile(r"\b(\d{1,2})[-/](\d{1,2})[-/](20\d{2})\b")


def header_date(header):
    """Letter date from the letterhead block; tolerant of pypdf line breaks inside words and typos."""
    m = _FUZZY_DATE.search(header)
    if m:
        word = re.sub(r"\s+", "", m.group(1)).lower()
        for i, (mon, alts) in enumerate(_MONTH_ALTS.items()):
            if word in [a.lower() for a in alts]:
                return f"{int(m.group(3)):04d}-{i + 1:02d}-{int(m.group(2)):02d}"
    m = _NUM_DATE.search(header)
    if m and 1 <= int(m.group(1)) <= 12:
        return f"{int(m.group(3)):04d}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    return None


def _stns_in(s):
    out = []
    for m in STN_RE.finditer(s):
        k = (m.group(1), str(int(m.group(2))))
        if k not in out:
            out.append(k)
    return out


def parse_letter(text):
    t = text or ""
    dear = re.search(r"\bDear\b", t)
    header = t[: dear.start()] if dear and dear.start() < 4000 else t[:1500]
    body = t[dear.start():] if dear else t
    out = {}
    stns = _stns_in(header)
    if not stns:
        pg = []
        for m in re.finditer(r"Page\s+\d+\s*[-–—]\s*(?:Our\s+)?(?:STN|BLA?|BL)[^\n]{0,40}?(1\d{5}|10\d{4})\s*/\s*(\d{1,5})", t):
            k = (m.group(1), str(int(m.group(2))))
            if k not in pg:
                pg.append(k)
        stns = pg
    if not stns:
        # bundled letters list the STNs in a table right after the salutation
        first = body[:2500]
        cand = []
        for m in STN_RE.finditer(first):
            pre = first[max(0, m.start() - 60):m.start()].lower()
            if "letter" in pre or "dated" in pre or "approved on" in pre:
                continue
            k = (m.group(1), str(int(m.group(2))))
            if k not in cand:
                cand.append(k)
        stns = cand
    if not stns:
        m = re.search(r"(?:STN|BLA|BL)\s*:?\s*#?\s*(?:BL\s*)?(1\d{5}|10\d{4})", t[:3000])
        if m:
            stns = [(m.group(1), None)]
    out["stns"] = stns
    out["letter_date"] = header_date(header)
    dm = DATE_RE.search(header)
    am = re.search(r"\n([^\n]+)\n\s*(?:ATTENTION|Attention|Attn)", header)
    if am and not re.match(r"^\s*(Our STN|STN|BL|BLA|SUPPLEMENT|APPROVAL|\w+ \d{1,2}, \d{4})", am.group(1).strip()):
        out["sponsor"] = am.group(1).strip()[:120]
    elif dm:
        after = t[dm.end(): dm.end() + 600].split("\n")
        lines = [x.strip() for x in after if x.strip() and not re.match(r"^(Our STN|STN|BL|BLA|SUPPLEMENT|APPROVAL)", x.strip())]
        out["sponsor"] = lines[0][:120] if lines else None
    para = body[:2200]
    para = re.split(r"\n\s*(?:LABELING|BIOLOGICAL PRODUCT DEVIATIONS|POSTMARKETING|PEDIATRIC REQUIREMENTS|ADVISORY COMMITTEE|MANUFACTURING LOCATIONS|We hereby approve the draft)", para)[0]
    out["purpose"] = re.sub(r"\s+", " ", para)[:1500]
    return out


def letter_date(r):
    """A letters_parsed row's date: the letterhead date, else the date in its link text."""
    date = r.get("letter_date")
    if not date and r.get("link_date"):
        m = DATE_RE.search(r["link_date"])
        date = iso(m) if m else None
    return date


def letter_matches(parsed, appl, suppl, date):
    """A parsed letter is for the action if it lists the action's STN/supplement, or its BLA and is
    dated within a week of the action."""
    if not parsed:
        return False
    for a, s in parsed.get("stns") or []:
        if a == appl and suppl is not None and s == suppl:
            return True
    ld = parsed.get("letter_date")
    return bool(ld and any(a == appl for a, _ in parsed.get("stns") or [])
                and abs((datetime.date.fromisoformat(ld) - datetime.date.fromisoformat(date)).days) <= 7)


def match_actions(actions, lrows):
    """(action, letters, how) per yearly-page action: letters_parsed rows listing its STN/supplement
    (how='stn'), else rows for its BLA dated within a week of it (how='appl_date'); how is None without letters."""
    by_stn, by_appl = {}, {}
    for r in lrows:
        dt = letter_date(r)
        for a, s in r.get("stns") or []:
            if s is not None:
                by_stn.setdefault((a, s), []).append(r)
            by_appl.setdefault(a, []).append((dt, r))
    out = []
    for a in actions:
        cands = []
        how = None
        if a.get("appl_no") and a.get("stn_suppl") is not None:
            cands = by_stn.get((a["appl_no"], a["stn_suppl"]), [])
            how = "stn"
        if not cands and a.get("appl_no") and a.get("approval_date"):
            ad = datetime.date.fromisoformat(a["approval_date"])
            cands = [r for dt, r in by_appl.get(a["appl_no"], [])
                     if dt and abs((datetime.date.fromisoformat(dt) - ad).days) <= 7]
            how = "appl_date"
        out.append((a, cands, how if cands else None))
    return out


def found_letters():
    """{action_row: record} over found_letters*.jsonl (both Wayback passes): the first record per
    action, replaced by any later one that found a letter."""
    out = {}
    for name in glob.glob("found_letters*.jsonl", root_dir=fetch.BASE):
        for r in fetch.read_jsonl(name):
            if r["action_row"] not in out or r.get("found"):
                out[r["action_row"]] = r
    return out
