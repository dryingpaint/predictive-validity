"""Step 3: download approval-letter PDFs linked from product pages (current + historic)."""
import json
import os
import re
import sys

from pipeline.cber import fetch
from pipeline.cber import letters

BASE = fetch.BASE
SKIP = re.compile(r"Dear Health ?care Provider|expiry extension|REMS|Risk Evaluation and Mitigation|Approval History|Letters, Reviews|Related Documents", re.I)


def wanted_docs(path):
    out = []
    for line in open(path):
        p = json.loads(line)
        for d in p.get("docs", []):
            if not re.search(r"letter", d["text"], re.I) or SKIP.search(d["text"]):
                continue
            out.append(d["href"])
    return out


def main():
    srcs = sys.argv[1:] or [os.path.join(BASE, "products.jsonl")]
    urls = []
    for s in srcs:
        urls.extend(wanted_docs(s))
    seen = []
    for u in urls:
        cu = letters.canon_media(u)
        if cu not in seen:
            seen.append(cu)
    print("letters to fetch", len(seen), flush=True)
    for i, u in enumerate(seen):
        r = letters.get_letter(u)
        if i % 50 == 0 or r.get("error"):
            print(i, u, r.get("status"), r.get("error"), r.get("n_bytes"), flush=True)


if __name__ == "__main__":
    main()
