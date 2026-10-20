"""Step 6: write actions_enumerated.jsonl (every yearly-page action + every in-window product-page
letter, with scope decision) and letters_index.jsonl (in-scope records in the CDER letter format)."""
import datetime
import glob
import json
import os
import re

from pipeline.cber import extra_decisions
from pipeline.cber import fetch
from pipeline.cber import letters
from pipeline.cber import match
from pipeline.cber import product_classes
from pipeline.cber import yearly_decisions

BASE = fetch.BASE
LO, HI = "2015-01-01", "2025-12-31"
IN_SCOPE = yearly_decisions.IN_SCOPE_SUPPL | {"original_bla"}


def load_texts():
    d = {}
    for p in sorted(glob.glob(os.path.join(BASE, "letters_text*.jsonl"))):
        for line in open(p):
            r = json.loads(line)
            if r["url"] not in d or r.get("sha256"):
                d[r["url"]] = r
    return d


def found_letters():
    out = {}
    for p in glob.glob(os.path.join(BASE, "found_letters*.jsonl")):
        for line in open(p):
            r = json.loads(line)
            if r["action_row"] not in out or r.get("found"):
                out[r["action_row"]] = r
    return out


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


def clean_name(s):
    return re.sub(r"\s+", " ", (s or "")).strip() or None


def main():
    texts = load_texts()
    rows = [json.loads(l) for l in open(os.path.join(BASE, "year_page_rows.jsonl"))]
    lrows = [json.loads(l) for l in open(os.path.join(BASE, "letters_parsed.jsonl"))]
    dec = yearly_decisions.decisions()
    found = found_letters()
    res = match.match_actions(rows, lrows)
    enum, index = [], []
    used_keys = set()

    def make_record(appl, suppl, date, category, letter=None, found_rec=None, listing=None, how=None):
        sub_type = "ORIG" if suppl == "0" else "SUPPL"
        rec = {"appl_no": appl, "appl_type": "BLA", "submission_type": sub_type,
               "submission_no": "1" if sub_type == "ORIG" else suppl,
               "submission_class_code_id": None, "approval_date": date, "review_priority": None, "url": None, "doc_date": None, "doc_title": None, "error": None,
               "sha256": None, "n_bytes": None, "text": None, "center": "CBER"}
        info = product_classes.product_info(appl, listing=listing, letter=letter)
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
                        "text": t.get("text"), "error": t.get("error") if t.get("error") != "little_or_no_text" else "little_or_no_text",
                        "pdf_source": "wayback" if t.get("wayback_url") else "fda.gov",
                        "wayback_pdf": t.get("wayback_url"), "letter_stns": letter.get("stns"),
                        "source_page": letter.get("source_page")})
        elif found_rec is not None:
            p = found_rec.get("parsed") or {}
            lm = letters.DATE_RE.search(found_rec.get("link_text") or "")
            rec.update({"url": found_rec["url"], "doc_date": p.get("letter_date") or (letters.iso(lm) if lm else date),
                        "doc_title": found_rec.get("link_text") or found_rec.get("zip_member"),
                        "sha256": found_rec["sha256"], "n_bytes": found_rec["n_bytes"], "text": found_rec.get("text"),
                        "pdf_source": "zip" if found_rec["via"] == "zip" else ("wayback" if found_rec.get("wayback_pdf") else "fda.gov"),
                        "zip_member": found_rec.get("zip_member"), "wayback_pdf": found_rec.get("wayback_pdf"),
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
        d = dec[i]
        appl, suppl = a["appl_no"], a["stn_suppl"]
        if a["list_kind"] == "BLA" and suppl is None:
            suppl = "0"
        e = {"source": "yearly_page", "row": i, "list_year": a["list_year"], "list_kind": a["list_kind"],
             "stn": a["stn"], "appl_no": appl, "suppl": suppl, "approval_date": a["approval_date"],
             "name": a["name"], "manufacturer": a["manufacturer"], "indication_or_change": a["indication"],
             "listing_page": a["listing_page"], "category": d["category"], "in_scope": d["in_scope"],
             "letter_urls": sorted({c["doc_url"] for c in cands}), "match_method": how}
        if d["in_scope"]:
            key = (appl, suppl, a["approval_date"])
            if key in used_keys:
                e["note"] = "duplicate of an earlier row"
                enum.append(e)
                continue
            used_keys.add(key)
            letter = pick_letter(cands, appl, suppl, a["approval_date"]) if cands else None
            f = found.get(i) if not letter else None
            rec = make_record(appl, suppl, a["approval_date"], d["category"], letter=letter,
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
        keys, date = match.letter_keys(r)
        date = r.get("letter_date") or date
        if not date or not (LO <= date <= HI):
            continue
        seen.add(r["doc_url"])
        stns = [(a_, s_) for a_, s_ in (r.get("stns") or []) if s_ is not None]
        cat, scope = "out_of_scope_labeling_cmc_safety_or_other", False
        for a_, s_ in stns:
            k = f"{a_}/{s_}"
            if k in extra_decisions.EXTRA_SUPPL:
                cat, scope = extra_decisions.EXTRA_SUPPL[k], True
            elif k in extra_decisions.EXTRA_ORIG:
                cat, scope = extra_decisions.EXTRA_ORIG[k], True
        if re.search(r"REMS|Risk Evaluation|Dear Health ?care|expiry|Suspension|Revocation", r["link_text"], re.I):
            cat = "out_of_scope_rems_or_notice"
        e = {"source": "product_page_letter", "doc_url": r["doc_url"], "link_text": r["link_text"],
             "letter_stns": r.get("stns"), "letter_date": date, "product_page": r["product_page"],
             "purpose": (r.get("purpose") or "")[:600], "category": cat, "in_scope": scope}
        enum.append(e)
        if scope:
            for a_, s_ in stns:
                k = f"{a_}/{s_}"
                if k not in extra_decisions.EXTRA_SUPPL and k not in extra_decisions.EXTRA_ORIG:
                    continue
                if (a_, s_, date) in used_keys:
                    continue
                used_keys.add((a_, s_, date))
                index.append(make_record(a_, s_, date, cat, letter=r, how="product_page_letter"))

    with open(os.path.join(BASE, "actions_enumerated.jsonl"), "w") as f:
        for e in enum:
            f.write(json.dumps(e) + "\n")
    index.sort(key=lambda r: (r["approval_date"], r["appl_no"], int(r["submission_no"])))
    cder_keys = ["appl_no", "appl_type", "submission_type", "submission_no", "submission_class_code_id",
                 "approval_date", "review_priority", "sponsor", "url", "doc_date", "doc_title", "error",
                 "sha256", "n_bytes", "text"]
    with open(os.path.join(BASE, "letters_index.jsonl"), "w") as f:
        for r in index:
            ordered = {k: r.get(k) for k in cder_keys}
            ordered.update({k: v for k, v in r.items() if k not in ordered})
            f.write(json.dumps(ordered) + "\n")
    print("enumerated", len(enum), "index", len(index))


if __name__ == "__main__":
    main()
