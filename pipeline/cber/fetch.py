"""Polite cached fetcher for fda.gov / web.archive.org pages and PDFs."""
import hashlib
import os
import re
import time
import urllib.parse
from pathlib import Path

import requests

BASE = str(Path(__file__).resolve().parents[2] / ".cache" / "cber")
HTML_DIR = os.path.join(BASE, "html")
PDF_DIR = os.path.join(BASE, "letters")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
S = requests.Session()
S.headers.update({"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9",
                  "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/pdf,*/*;q=0.8"})
_last = [0.0]


def _name(url):
    p = urllib.parse.urlparse(url)
    slug = re.sub(r"[^A-Za-z0-9]+", "_", (p.netloc + p.path + ("_" + p.query if p.query else "")))[-150:]
    h = hashlib.sha1(url.encode()).hexdigest()[:10]
    return f"{slug}__{h}.html"


def get(url, binary=False, tries=6, min_gap=None, timeout=60):
    if min_gap is None:
        min_gap = 3.5 if "archive.org" in url else 0.6
    for i in range(tries):
        gap = time.time() - _last[0]
        if gap < min_gap:
            time.sleep(min_gap - gap)
        _last[0] = time.time()
        try:
            hdrs = {"User-Agent": "Mozilla/5.0 (compatible; cber-approvals-audit/1.0)"} if "archive.org" in url else None
            r = S.get(url, timeout=timeout, allow_redirects=True, headers=hdrs)
            if r.status_code in (429, 500, 502, 503, 504, 520, 522, 524):
                raise requests.HTTPError(f"status {r.status_code}")
            return r
        except Exception as e:  # noqa: BLE001
            wait = 2 ** i * (10 if "archive.org" in url else 2)
            print(f"  retry {i+1} {url} ({e}); sleep {wait}s", flush=True)
            time.sleep(wait)
    return None


_IDX_PATH = os.path.join(HTML_DIR, "_index.jsonl")


def _idx():
    d = {}
    if os.path.exists(_IDX_PATH):
        for line in open(_IDX_PATH):
            try:
                import json as _j
                r = _j.loads(line)
                d[r["url"]] = r
            except Exception:  # noqa: BLE001
                pass
    return d


_IDX = None


def get_html(url, refresh=False):
    """Return (html_text, local_path, final_url, status). Cached; url->final_url kept in html/_index.jsonl."""
    global _IDX
    import json as _j
    if _IDX is None:
        _IDX = _idx()
    path = os.path.join(HTML_DIR, _name(url))
    if os.path.exists(path) and not refresh:
        with open(path, encoding="utf-8", errors="replace") as f:
            final = _IDX.get(url, {}).get("final_url", url)
            return f.read(), path, final, 200
    if not refresh and url in _IDX and _IDX[url].get("status") not in (200, None, "challenge"):
        return None, None, _IDX[url].get("final_url", url), _IDX[url]["status"]
    r = get(url)
    if r is None:
        return None, None, url, None
    rec = {"url": url, "final_url": r.url, "status": r.status_code, "file": None,
           "fetched": time.strftime("%Y-%m-%dT%H:%M:%S")}
    if r.status_code == 200:
        txt = r.text
        if "<title>Session Verification</title>" in txt[:2000]:
            return None, None, r.url, "challenge"
        with open(path, "w", encoding="utf-8") as f:
            f.write(txt)
        rec["file"] = os.path.basename(path)
    _IDX[url] = rec
    with open(_IDX_PATH, "a") as f:
        f.write(_j.dumps(rec) + "\n")
    if r.status_code != 200:
        return None, None, r.url, r.status_code
    return txt, path, r.url, r.status_code


def get_pdf(url):
    """Return dict(sha256, n_bytes, path, status, final_url, content_type)."""
    r = get(url, binary=True, timeout=120)
    if r is None:
        return {"status": None, "error": "fetch_failed"}
    ct = r.headers.get("Content-Type", "")
    data = r.content
    out = {"status": r.status_code, "final_url": r.url, "content_type": ct}
    if r.status_code != 200:
        out["error"] = str(r.status_code)
        return out
    if not data.startswith(b"%PDF"):
        out["error"] = "not_pdf"
        out["head"] = data[:300].decode("utf-8", "replace")
        return out
    sha = hashlib.sha256(data).hexdigest()
    path = os.path.join(PDF_DIR, sha + ".pdf")
    if not os.path.exists(path):
        with open(path, "wb") as f:
            f.write(data)
    out.update({"sha256": sha, "n_bytes": len(data), "path": path})
    return out


def cdx(url, limit=None, extra=""):
    """List Wayback captures (timestamp, original) with status 200 for url (exact or prefix)."""
    q = f"https://web.archive.org/cdx/search/cdx?url={urllib.parse.quote(url, safe='/:*')}&output=json&filter=statuscode:200&collapse=digest{extra}"
    if limit:
        q += f"&limit={limit}"
    r = get(q, timeout=120)
    if r is None or r.status_code != 200:
        return []
    try:
        rows = r.json()
    except Exception:  # noqa: BLE001
        return []
    return [dict(zip(rows[0], x)) for x in rows[1:]]


def wayback_latest(url, before="20991231"):
    caps = [c for c in cdx(url) if c["timestamp"] <= before]
    if not caps:
        return None
    c = caps[-1]
    return f"https://web.archive.org/web/{c['timestamp']}id_/{c['original']}"
