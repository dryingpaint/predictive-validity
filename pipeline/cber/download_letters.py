"""Step 3: download approval-letter PDFs linked from product pages (current + historic)."""
import re

from pipeline.cber import fetch
from pipeline.cber import letters

SKIP = re.compile(r"Dear Health ?care Provider|expiry extension|REMS|Risk Evaluation and Mitigation|Approval History|Letters, Reviews|Related Documents", re.I)


def wanted_docs(name):
    """Hrefs of the letter links on the product pages in one products file."""
    return [d["href"] for p in fetch.read_jsonl(name) for d in p.get("docs", [])
            if re.search(r"letter", d["text"], re.I) and not SKIP.search(d["text"])]


def main():
    urls = list(dict.fromkeys(letters.canon_media(u) for name in ("products.jsonl", "products_historic.jsonl")
                              for u in wanted_docs(name)))
    print("letters to fetch", len(urls), flush=True)
    for i, u in enumerate(urls):
        r = letters.get_letter(u)
        if i % 50 == 0 or r.get("error"):
            print(i, u, r.get("status"), r.get("error"), r.get("n_bytes"), flush=True)


if __name__ == "__main__":
    main()
