"""Read approval letters out of CBER 'Approval History, Letters, Reviews, and Related Documents' zip
archives using HTTP range requests (only the central directory and the letter members are fetched)."""
import hashlib
import io
import json
import os
import re
import time
import zipfile

from pipeline.cber import fetch
from pipeline.cber import letters

BASE = fetch.BASE
LISTING = os.path.join(BASE, "zip_listings.jsonl")


class RangeFile(io.RawIOBase):
    def __init__(self, url):
        self.url = url
        r = fetch.S.get(url, headers={"Range": "bytes=0-0"}, timeout=60)
        self.size = int(r.headers["Content-Range"].split("/")[1])
        self.pos = 0
        self.ctype = r.headers.get("Content-Type")

    def seekable(self):
        return True

    def readable(self):
        return True

    def seek(self, off, whence=0):
        self.pos = off if whence == 0 else (self.pos + off if whence == 1 else self.size + off)
        return self.pos

    def tell(self):
        return self.pos

    def read(self, n=-1):
        if n is None or n < 0:
            n = self.size - self.pos
        if n == 0 or self.pos >= self.size:
            return b""
        end = min(self.size, self.pos + n) - 1
        for i in range(5):
            time.sleep(0.4)
            try:
                r = fetch.S.get(self.url, headers={"Range": f"bytes={self.pos}-{end}"}, timeout=120)
                if r.status_code == 206:
                    break
            except Exception:  # noqa: BLE001
                pass
            time.sleep(2 ** i)
        data = r.content
        self.pos += len(data)
        return data

    def readinto(self, b):
        data = self.read(len(b))
        b[: len(data)] = data
        return len(data)


def list_zip(url):
    url = letters.canon_media(url)
    rf = RangeFile(url)
    if "zip" not in (rf.ctype or ""):
        return rf, None
    return rf, zipfile.ZipFile(io.BufferedReader(rf, buffer_size=1 << 16))


def extract_letters(url, want=re.compile(r"approval letter|\bletter\b.*approv|approv.*letter", re.I)):
    """Return list of dicts for members whose name looks like an approval letter."""
    rf, z = list_zip(url)
    out = []
    if z is None:
        return out, None
    names = [i.filename for i in z.infolist()]
    with open(LISTING, "a") as f:
        f.write(json.dumps({"url": letters.canon_media(url), "members": names}) + "\n")
    for i in z.infolist():
        if not want.search(os.path.basename(i.filename)) or not i.filename.lower().endswith(".pdf"):
            continue
        data = z.read(i)
        sha = hashlib.sha256(data).hexdigest()
        path = os.path.join(fetch.PDF_DIR, sha + ".pdf")
        if not os.path.exists(path):
            open(path, "wb").write(data)
        txt, n, err = letters.extract_text(path)
        out.append({"zip_url": letters.canon_media(url), "member": i.filename, "sha256": sha, "n_bytes": len(data),
                    "text": txt, "n_pages": n, "error": err})
    return out, names


if __name__ == "__main__":
    import sys
    res, names = extract_letters(sys.argv[1])
    print(names)
    for r in res:
        print(r["member"], r["n_bytes"], (r["text"] or "")[:300])
