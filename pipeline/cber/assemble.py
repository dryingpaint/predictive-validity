"""Step 6: write actions_enumerated.jsonl (every yearly-page action + every in-window product-page
letter, with scope decision) and letters_index.jsonl (in-scope records in the CDER letter format)."""
import datetime
import functools
import os
import re

from pipeline.cber import decisions
from pipeline.cber import fetch
from pipeline.cber import letters

LO, HI = "2015-01-01", "2025-12-31"
_ADDR = re.compile(
    r"\s{2,}|\s(?=\d)|\(b\)|-{2,}| Lic\.| Attention| Attn|\sP\.\s?O\.|\s#|"
    r"\s(?:One|Five|Rue|Oberlaaer|Calzada|Campus|Clarendon|Dagger|Discovery Drive|Parker Plaza|Darwinweg|Langebjerg)\b|"
    r"\s[A-Z][a-z]+(?:strasse|straße|weg)\b|"
    r"\s(?:January|February|March|April|May|June|July|August|September|October|November|December)\s\d")


@functools.cache
def _page_by_appl():
    pages = {}
    for fn in ("products.jsonl", "products_historic.jsonl"):
        for p in fetch.read_jsonl(fn):
            for s in p.get("stns") or []:
                pages.setdefault(s, p)
    return pages


def _clean_mfr(s):
    s = re.sub(r"[ \t]+(?=\S)", " ", (s or "").replace("\n", " ")).strip()
    s = _ADDR.split(s)[0].strip(" ,;")
    return s or None


def product_info(appl, listing=None, letter=None):
    cls, brand, proper = decisions.PRODUCTS[appl]
    sponsor = None
    if listing is not None:
        sponsor = _clean_mfr(listing.get("manufacturer"))
    if not sponsor and letter is not None and letter.get("sponsor"):
        sp = _clean_mfr(letter["sponsor"]) or ""
        if re.match(r"^[A-Z][A-Za-z]", sp) and not re.match(r"^(Attention|Attn|ATTENTION|Our STN|Dear)", sp):
            sponsor = sp
    if appl in decisions.SPONSOR_OVERRIDE and (not sponsor or sponsor.startswith("D Biomedical")):
        sponsor = decisions.SPONSOR_OVERRIDE[appl]
    if not sponsor:
        p = _page_by_appl().get(appl)
        if p:
            sponsor = _clean_mfr(p.get("manufacturer") or p.get("list_manufacturer"))
    return {"product_class": cls, "brand": brand, "proper_name": proper, "sponsor": sponsor}


def dd(a, b):
    return abs((datetime.date.fromisoformat(a) - datetime.date.fromisoformat(b)).days)


def pick_letter(cands, appl, suppl, date):
    """Prefer the letter whose STN list contains (appl, suppl), then the one dated closest to the action."""
    def key(r):
        exact = any(a == appl and s == suppl for a, s in (r.get("stns") or []))
        ld = r.get("letter_date") or date
        repl = bool(re.search(r"replacement|correct", r.get("link_text", ""), re.I))
        return (not exact, dd(ld, date) if ld and date else 999, repl)
    c = [r for r in cands if r.get("downloaded")]
    return sorted(c, key=key)[0] if c else None


def apply_corrections(index):
    """Drop, re-letter and add records per the corrections in pipeline.cber.decisions."""
    out = []
    for r in index:
        key = (r["appl_no"], r["submission_no"])
        if key in decisions.DROP:
            continue
        if key in decisions.LETTER:
            fix = decisions.LETTER[key]
            path = os.path.join(fetch.PDF_DIR, fix["sha256"] + ".pdf")
            r.update({"url": fix["url"], "wayback_pdf": fix["wayback_pdf"], "sha256": fix["sha256"],
                      "n_bytes": os.path.getsize(path), "text": None, "error": None, "pdf_source": "wayback",
                      "letter_note": fix["why"]})
        out.append(r)
    for a in decisions.ADD:
        path = os.path.join(fetch.PDF_DIR, a["sha256"] + ".pdf")
        out.append({"appl_no": a["appl_no"], "appl_type": "BLA", "submission_type": "SUPPL",
                    "submission_no": a["submission_no"], "submission_class_code_id": None,
                    "approval_date": a["approval_date"], "review_priority": None, "sponsor": a["sponsor"],
                    "url": a["url"], "doc_date": a["approval_date"], "doc_title": None, "error": None,
                    "sha256": a["sha256"], "n_bytes": os.path.getsize(path), "text": None, "center": "CBER",
                    "product_brand": a["product_brand"], "proper_name": a["proper_name"],
                    "product_class": a["product_class"], "is_vaccine": a["product_class"] == "vaccine",
                    "change_category": a["change_category"], "listed_on_yearly_page": False,
                    "match_method": "verification", "pdf_source": "wayback", "source_page": a["source_page"],
                    "letter_note": a["letter_note"]})
    return out


def main():
    texts = letters.texts()
    rows = fetch.read_jsonl("year_page_rows.jsonl")
    lrows = fetch.read_jsonl("letters_parsed.jsonl")
    dec = decisions.decisions(rows)
    found = letters.found_letters()
    res = letters.match_actions(rows, lrows)
    enum, index = [], []
    used_keys = set()

    def make_record(appl, suppl, date, category, letter=None, found_rec=None, listing=None, how=None):
        sub_type = "ORIG" if suppl == "0" else "SUPPL"
        rec = {"appl_no": appl, "appl_type": "BLA", "submission_type": sub_type,
               "submission_no": "1" if sub_type == "ORIG" else suppl,
               "submission_class_code_id": None, "approval_date": date, "review_priority": None, "url": None, "doc_date": None, "doc_title": None, "error": None,
               "sha256": None, "n_bytes": None, "text": None, "center": "CBER"}
        info = product_info(appl, listing=listing, letter=letter)
        rec.update({"product_brand": info["brand"], "proper_name": info["proper_name"], "sponsor": info["sponsor"],
                    "product_class": info["product_class"], "is_vaccine": info["product_class"] == "vaccine",
                    "change_category": category, "listed_on_yearly_page": listing is not None,
                    "yearly_listing_page": listing["listing_page"] if listing else None,
                    "yearly_listing_text": listing["row_text"] if listing else None,
                    "match_method": how, "pdf_source": None, "zip_member": None, "letter_stns": None,
                    "source_page": None})
        if letter is not None:
            t = texts.get(letter["doc_url"], {})
            rec.update({"url": letter["doc_url"], "doc_date": letter.get("letter_date") or date,
                        "doc_title": letter.get("link_text"), "sha256": t.get("sha256"), "n_bytes": t.get("n_bytes"),
                        "text": t.get("text"), "error": t.get("error"),
                        "pdf_source": "wayback" if t.get("wayback_url") else "fda.gov",
                        "wayback_pdf": t.get("wayback_url"), "letter_stns": letter.get("stns"),
                        "source_page": letter.get("source_page")})
        elif found_rec is not None:
            p = found_rec.get("parsed") or {}
            lm = letters.DATE_RE.search(found_rec.get("link_text") or "")
            rec.update({"url": found_rec["url"], "doc_date": p.get("letter_date") or (letters.iso(lm) if lm else date),
                        "doc_title": found_rec.get("link_text"),
                        "sha256": found_rec["sha256"], "n_bytes": found_rec["n_bytes"], "text": found_rec.get("text"),
                        "pdf_source": "wayback" if found_rec.get("wayback_pdf") else "fda.gov",
                        "wayback_pdf": found_rec.get("wayback_pdf"),
                        "letter_stns": p.get("stns"), "source_page": found_rec.get("source_page")})
            if not rec["text"] or len(rec["text"].strip()) < 200:
                rec["error"] = "little_or_no_text"
        else:
            rec.update({"url": listing["listing_page"], "doc_date": None, "text": listing["row_text"],
                        "error": "no_letter_pdf", "source_page": listing["listing_page"]})
        txt = rec.get("text") or ""
        rec["letter_note"] = None
        if rec["error"] != "no_letter_pdf" and re.search(r"replacement (?:supplement )?approval letter|We also refer to our (?:supplement |BLA )?approval letter dated|letter sup\w*sedes", txt, re.I):
            rec["letter_note"] = "replacement/corrected letter; doc_date is the replacement date"
        return rec

    # A. yearly-page actions
    for i, (a, cands, how) in enumerate(res):
        cat, scope = dec[i]
        appl, suppl = a["appl_no"], a["stn_suppl"]
        if a["list_kind"] == "BLA" and suppl is None:
            suppl = "0"
        e = {"source": "yearly_page", "row": i, "list_year": a["list_year"], "list_kind": a["list_kind"],
             "stn": a["stn"], "appl_no": appl, "suppl": suppl, "approval_date": a["approval_date"],
             "name": a["name"], "manufacturer": a["manufacturer"], "indication_or_change": a["indication"],
             "listing_page": a["listing_page"], "category": cat, "in_scope": scope,
             "letter_urls": sorted({c["doc_url"] for c in cands}), "match_method": how}
        if scope:
            key = (appl, suppl, a["approval_date"])
            if key in used_keys:
                e["note"] = "duplicate of an earlier row"
                enum.append(e)
                continue
            used_keys.add(key)
            letter = pick_letter(cands, appl, suppl, a["approval_date"]) if cands else None
            f = found.get(i) if not letter else None
            rec = make_record(appl, suppl, a["approval_date"], cat, letter=letter,
                              found_rec=f if f and f.get("found") else None, listing=a,
                              how=how or ("found_" + f["via"] if f and f.get("found") else None))
            e["letter_status"] = "letter" if rec["error"] != "no_letter_pdf" else "no_letter_pdf"
            e["letter_url"] = rec["url"] if rec["error"] != "no_letter_pdf" else None
            index.append(rec)
        enum.append(e)

    # B. product-page letters not on the yearly pages
    matched_urls = {c["doc_url"] for _, cands, _ in res for c in cands}
    seen = set()
    for r in lrows:
        if r["doc_url"] in matched_urls or r["doc_url"] in seen:
            continue
        if re.search(r"Approval History|Letters, Reviews|Related Documents", r["link_text"], re.I):
            continue
        date = letters.letter_date(r)
        if not date or not (LO <= date <= HI):
            continue
        seen.add(r["doc_url"])
        hits = [(a_, s_) for a_, s_ in (r.get("stns") or []) if s_ is not None and f"{a_}/{s_}" in decisions.EXTRA]
        cat, scope = (decisions.EXTRA["/".join(hits[-1])], True) if hits else ("out_of_scope_labeling_cmc_safety_or_other", False)
        if re.search(r"REMS|Risk Evaluation|Dear Health ?care|expiry|Suspension|Revocation", r["link_text"], re.I):
            cat = "out_of_scope_rems_or_notice"
        e = {"source": "product_page_letter", "doc_url": r["doc_url"], "link_text": r["link_text"],
             "letter_stns": r.get("stns"), "letter_date": date, "product_page": r["product_page"],
             "purpose": (r.get("purpose") or "")[:600], "category": cat, "in_scope": scope}
        enum.append(e)
        for a_, s_ in hits:
            if (a_, s_, date) in used_keys:
                continue
            used_keys.add((a_, s_, date))
            index.append(make_record(a_, s_, date, cat, letter=r, how="product_page_letter"))

    index = apply_corrections(index)
    fetch.write_jsonl("actions_enumerated.jsonl", enum)
    index.sort(key=lambda r: (r["approval_date"], r["appl_no"], int(r["submission_no"])))
    cder_keys = ["appl_no", "appl_type", "submission_type", "submission_no", "submission_class_code_id",
                 "approval_date", "review_priority", "sponsor", "url", "doc_date", "doc_title", "error",
                 "sha256", "n_bytes", "text"]
    fetch.write_jsonl("letters_index.jsonl",
                      ({**{k: r.get(k) for k in cder_keys}, **{k: v for k, v in r.items() if k not in cder_keys}}
                       for r in index))
    print("enumerated", len(enum), "index", len(index))


if __name__ == "__main__":
    main()
