"""Polite cached fetcher for fda.gov / web.archive.org pages and PDFs, and the .cache/cber file helpers."""
import functools
import hashlib
import json
import os
import re
import time
import urllib.parse
from pathlib import Path

import requests

BASE = str(Path(__file__).resolve().parents[2] / ".cache" / "cber")
HTML_DIR = os.path.join(BASE, "html")
PDF_DIR = os.path.join(BASE, "letters")
os.makedirs(HTML_DIR, exist_ok=True)
os.makedirs(PDF_DIR, exist_ok=True)
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
S = requests.Session()
S.headers.update({"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9",
                  "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/pdf,*/*;q=0.8"})
_last = [0.0]
_IDX_PATH = os.path.join(HTML_DIR, "_index.jsonl")
_WAYBACK_PREFIX = re.compile(r"^https?://web\.archive\.org/web/\d+[a-z_]*/")


def read_jsonl(name):
    """Rows of a JSON-lines file under .cache/cber."""
    with open(os.path.join(BASE, name)) as f:
        return [json.loads(line) for line in f]


def write_jsonl(name, rows):
    with open(os.path.join(BASE, name), "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def wayback(cap):
    """Raw (id_) Wayback URL of a CDX capture."""
    return f"https://web.archive.org/web/{cap['timestamp']}id_/{cap['original']}"


def unwayback(url):
    """The original URL inside a Wayback URL; any other URL unchanged."""
    return _WAYBACK_PREFIX.sub("", url)


def _name(url):
    p = urllib.parse.urlparse(url)
    slug = re.sub(r"[^A-Za-z0-9]+", "_", (p.netloc + p.path + ("_" + p.query if p.query else "")))[-150:]
    h = hashlib.sha1(url.encode()).hexdigest()[:10]
    return f"{slug}__{h}.html"


def get(url, timeout=60):
    min_gap = 3.5 if "archive.org" in url else 0.6
    for i in range(6):
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


@functools.cache
def _index():
    """{url: fetch record} from html/_index.jsonl; get_html adds to it as it fetches."""
    d = {}
    if os.path.exists(_IDX_PATH):
        with open(_IDX_PATH) as f:
            for line in f:
                try:
                    r = json.loads(line)
                    d[r["url"]] = r
                except Exception:  # noqa: BLE001
                    pass
    return d


def get_html(url):
    """Return (html_text, local_path, final_url, status). Cached; url->final_url kept in html/_index.jsonl."""
    idx = _index()
    path = os.path.join(HTML_DIR, _name(url))
    if os.path.exists(path):
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read(), path, idx.get(url, {}).get("final_url", url), 200
    if url in idx and idx[url].get("status") not in (200, None, "challenge"):
        return None, None, idx[url].get("final_url", url), idx[url]["status"]
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
    idx[url] = rec
    with open(_IDX_PATH, "a") as f:
        f.write(json.dumps(rec) + "\n")
    if r.status_code != 200:
        return None, None, r.url, r.status_code
    return txt, path, r.url, r.status_code


def get_pdf(url):
    """Return dict(status, sha256, n_bytes, path), or dict(status, error) when no PDF came back."""
    r = get(url, timeout=120)
    if r is None:
        return {"status": None, "error": "fetch_failed"}
    out = {"status": r.status_code}
    if r.status_code != 200:
        out["error"] = str(r.status_code)
        return out
    data = r.content
    if not data.startswith(b"%PDF"):
        out["error"] = "not_pdf"
        return out
    sha = hashlib.sha256(data).hexdigest()
    path = os.path.join(PDF_DIR, sha + ".pdf")
    if not os.path.exists(path):
        with open(path, "wb") as f:
            f.write(data)
    out.update({"sha256": sha, "n_bytes": len(data), "path": path})
    return out


def cdx(url):
    """List Wayback captures with status 200 for url (exact or prefix; any scheme is dropped)."""
    url = re.sub(r"^https?://", "", url)
    q = f"https://web.archive.org/cdx/search/cdx?url={urllib.parse.quote(url, safe='/:*')}&output=json&filter=statuscode:200&collapse=digest"
    r = get(q, timeout=120)
    if r is None or r.status_code != 200:
        return []
    try:
        rows = r.json()
    except Exception:  # noqa: BLE001
        return []
    return [dict(zip(rows[0], x)) for x in rows[1:]]
