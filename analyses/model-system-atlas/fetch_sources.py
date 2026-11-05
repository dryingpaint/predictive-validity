"""Source bundle for the atlas drafters: each class member's FDA review package as text.

    .venv/bin/python analyses/model-system-atlas/fetch_sources.py MEMBERS.csv

MEMBERS.csv has columns `context` and `moiety_id` (the members of each context's class). For every
member with an original NDA or BLA in Drugs@FDA (preclin.fda_application_moiety, read-only), the
openFDA drugsfda record gives the review table of contents; the review PDFs listed there (non-clinical,
medical, clinical pharmacology, multidiscipline/integrated, summary, cross-discipline, statistics,
office director memo) and the original label are downloaded and converted with pdftotext; a scanned
PDF (pre-2012 packages mostly are) is OCRed page by page with pdftoppm and tesseract.

Writes sources/<appl_no>/<file>.pdf and .txt (not committed) and sources/manifest.csv, one row per
context x document, which the drafter brief points at. Agents cannot read review PDFs above 10 MB
themselves; this is why `model_filed` was null on 193 of 523 entries in the v2 run. CBER products
(gene and cell therapies) are not in openFDA drugsfda and get a row with `error: not_in_openfda`.
"""
import csv
import json
import os
import re
import subprocess
import sys
import http.client
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))

from report import frame  # noqa: E402

OUT = os.path.join(HERE, "sources")
OPENFDA = "https://api.fda.gov/drug/drugsfda.json?search=application_number:{}"
REVIEWS = re.compile(r"(PharmR|MedR|ClinPharmR|MultidisciplineR|IntegratedR|SumR|CrossR|StatR|ODMemo)", re.I)
UA = {"User-Agent": "Mozilla/5.0 (predictive-validity atlas source bundle)"}


KINDS = {k.lower(): k for k in ("PharmR", "MedR", "ClinPharmR", "MultidisciplineR", "IntegratedR", "SumR", "CrossR",
                                 "StatR", "ODMemo")}


def get(url: str, attempts: int = 3) -> bytes:
    """GET with retries: accessdata drops large transfers part-way."""
    for i in range(attempts):
        try:
            with urllib.request.urlopen(urllib.request.Request(url.replace("http://", "https://"), headers=UA),
                                        timeout=300) as r:
                return r.read()
        except (http.client.IncompleteRead, TimeoutError, urllib.error.URLError) as e:
            if isinstance(e, urllib.error.HTTPError) and e.code == 404 or i == attempts - 1:
                raise


def documents(appl_no: str, appl_type: str) -> list[tuple[str, str]]:
    """(kind, url) for the original approval's review PDFs and label."""
    try:
        rec = json.loads(get(OPENFDA.format(f"{appl_type}{appl_no}")))["results"][0]
    except Exception:
        return []
    docs, tocs = [], []
    for s in rec.get("submissions", []):
        if s.get("submission_type") != "ORIG":
            continue
        for d in s.get("application_docs") or []:
            if d.get("type") == "Label":
                docs.append(("label", d["url"]))
            elif d.get("type") == "Review":
                tocs.append(d["url"])
    for toc in tocs:
        try:
            page = get(toc).decode("latin-1")
        except Exception:
            continue
        flags = dict(re.findall(r"(\w+):\s*([01])\s*,", page))
        for name in sorted(set(re.findall(r"[\w\-. ]+?\.pdf", page, re.I))):
            name = name.strip().lstrip("/")
            m = REVIEWS.search(name)
            if appl_no.lstrip("0") not in name:  # the TOC's script also holds bare template names
                continue
            if not m or (flags and flags.get(m.group(1)[0].lower() + m.group(1)[1:], "1") == "0"):
                continue
            docs.append((KINDS[m.group(1).lower()], urllib.parse.urljoin(toc, urllib.parse.quote(name))))
    return docs


def ocr(pdf: str, txt: str) -> None:
    """Page-by-page OCR; each page's text is preceded by a form feed, as pdftotext writes it."""
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["pdftoppm", "-r", "200", "-gray", "-png", pdf, os.path.join(tmp, "p")], check=True,
                       capture_output=True, timeout=7200)
        pages = []
        for png in sorted(os.listdir(tmp), key=lambda n: int(re.sub(r"\D", "", n) or 0)):
            r = subprocess.run(["tesseract", os.path.join(tmp, png), "-", "--psm", "1"], capture_output=True,
                               text=True, timeout=600)
            pages.append(r.stdout)
    open(txt, "w").write("\f".join(pages))


def scanned(pdf_bytes: int, txt_chars: int) -> bool:
    return txt_chars < 2000 * max(1, pdf_bytes // 2_000_000)


def fetch(appl_no: str, url: str) -> dict:
    d = os.path.join(OUT, appl_no)
    os.makedirs(d, exist_ok=True)
    pdf = os.path.join(d, os.path.basename(urllib.parse.unquote(url)))
    txt = pdf[:-4] + ".txt"
    row = {"url": url, "pdf": os.path.relpath(pdf, HERE), "txt": os.path.relpath(txt, HERE), "bytes": None,
           "chars": None, "ocr": False, "error": None}
    try:
        if not os.path.exists(pdf):
            data = get(url)
            if not data.startswith(b"%PDF"):
                raise ValueError("not a PDF (bot page?)")
            open(pdf, "wb").write(data)
        row["bytes"] = os.path.getsize(pdf)
        if not os.path.exists(txt):
            subprocess.run(["pdftotext", "-layout", pdf, txt], check=True, capture_output=True, timeout=600)
        if scanned(row["bytes"], os.path.getsize(txt)):
            ocr(pdf, txt)
            row["ocr"] = True
        row["chars"] = os.path.getsize(txt)
        if scanned(row["bytes"], row["chars"]):
            row["error"] = "little text after OCR"
    except Exception as e:  # recorded per document; one failure does not stop the bundle
        row["error"] = f"{type(e).__name__}: {e}"[:200]
    return row


def main(members_csv: str) -> None:
    members = list(csv.DictReader(open(members_csv)))
    ids = sorted({int(float(m["moiety_id"])) for m in members if m.get("moiety_id")})
    appl = frame.query("""SELECT am.moiety_id, a.appl_no, a.appl_type, a.center
                          FROM preclin.fda_application_moiety am
                          JOIN preclin.fda_application a USING (appl_no)
                          WHERE am.moiety_id = ANY(%s) AND am.biosimilar_of IS NULL""", (ids,))
    by_moiety = appl.groupby("moiety_id")
    plan, rows = {}, []
    for a in appl.drop_duplicates("appl_no").itertuples():
        plan[a.appl_no] = documents(a.appl_no, a.appl_type) if a.center == "CDER" else []
    jobs = {(n, u) for n, docs in plan.items() for _, u in docs}
    with ThreadPoolExecutor(4) as ex:
        done = dict(zip(jobs, ex.map(lambda j: fetch(*j), jobs)))
    for m in members:
        mid = int(float(m["moiety_id"])) if m.get("moiety_id") else None
        if mid is None or mid not in by_moiety.groups:
            rows.append({"context": m["context"], "moiety_id": mid, "appl_no": None, "kind": None,
                         "error": "no NDA/BLA"})
            continue
        for a in by_moiety.get_group(mid).itertuples():
            if not plan.get(a.appl_no):
                rows.append({"context": m["context"], "moiety_id": mid, "appl_no": a.appl_no, "kind": None,
                             "error": "not_in_openfda" if a.center == "CBER" else "no review documents"})
            for kind, url in plan.get(a.appl_no, []):
                rows.append({"context": m["context"], "moiety_id": mid, "appl_no": a.appl_no, "kind": kind,
                             **done[(a.appl_no, url)]})
    fields = ["context", "moiety_id", "appl_no", "kind", "url", "pdf", "txt", "bytes", "chars", "ocr", "error"]
    with open(os.path.join(OUT, "manifest.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows({k: r.get(k) for k in fields} for r in rows)
    ok = sum(1 for r in rows if r.get("txt") and not r.get("error"))
    print(f"{len(rows)} rows, {ok} documents as text, {len(rows) - ok} with an error; sources/manifest.csv")


if __name__ == "__main__":
    main(sys.argv[1])
