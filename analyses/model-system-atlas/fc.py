"""Fetch a page or search the web through Firecrawl, for the atlas agents when WebFetch is refused or the
search budget is spent. The key is FIRECRAWL_API_KEY in .env (never committed).

    .venv/bin/python analyses/model-system-atlas/fc.py scrape <url> [--max-chars N]
    .venv/bin/python analyses/model-system-atlas/fc.py search "<query>" [--limit N]

scrape prints the page as markdown (PDFs included); search prints title, url and a snippet per hit.
"""
import argparse
import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))
from dotenv import load_dotenv

load_dotenv(os.path.join(HERE, "..", "..", ".env"))
KEY = os.environ.get("FIRECRAWL_API_KEY")


def call(path: str, body: dict) -> dict:
    req = urllib.request.Request(f"https://api.firecrawl.dev/v2/{path}", data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def main() -> None:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scrape")
    s.add_argument("url")
    s.add_argument("--max-chars", type=int, default=60000)
    q = sub.add_parser("search")
    q.add_argument("query")
    q.add_argument("--limit", type=int, default=8)
    a = p.parse_args()
    if not KEY:
        sys.exit("FIRECRAWL_API_KEY is not set in .env")
    if a.cmd == "scrape":
        d = call("scrape", {"url": a.url, "formats": ["markdown"]})
        if not d.get("success"):
            sys.exit(f"scrape failed: {d.get('error')}")
        md = d["data"].get("markdown", "")
        meta = d["data"].get("metadata", {})
        print(f"# {meta.get('title', '')}\n# {meta.get('sourceURL', a.url)}\n")
        print(md[: a.max_chars] + ("\n[truncated]" if len(md) > a.max_chars else ""))
    else:
        d = call("search", {"query": a.query, "limit": a.limit})
        if not d.get("success"):
            sys.exit(f"search failed: {d.get('error')}")
        hits = d["data"].get("web", d["data"]) if isinstance(d["data"], dict) else d["data"]
        for h in hits:
            print(f"- {h.get('title', '')}\n  {h.get('url', '')}\n  {(h.get('description') or '')[:300]}")


if __name__ == "__main__":
    main()
