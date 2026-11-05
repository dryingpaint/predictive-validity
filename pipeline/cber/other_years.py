"""CBER biologics approvals in the years the main steps do not cover -> .cache/cber/letters_index_other.jsonl.

    python -m pipeline.cber.other_years   # yearly pages 2008-2014 (Wayback) and 2026 (live) -> LLM -> index

The main CBER steps (pipeline.cber) cover 2015-2025 and decide each row by hand, keyed by its row
index. The years outside are read here into their own file, so those keys do not move. For 2008-2014
the BLA and supplement pages are read at every Wayback capture of their old ucm URL and the rows
pooled, since a single capture can hold a partial list; the current year's pages are read live. An LLM reads each row (product, indication or
change, STN) and gives the category the hand decisions use and, for an in-scope row, the product's
brand, proper name and class. Each in-scope row becomes an index record in the CDER letter format
whose document is the yearly listing: original approvals before 2015 are dated, and the listed
indication is what `pipeline.fda extract` reads. `pipeline.fda load-cber` loads this file with the main
one.
"""
from __future__ import annotations

import re

from pipeline import llm
from pipeline.cber import fetch
from pipeline.cber.decisions import IN_SCOPE_SUPPL
from pipeline.cber.enumerate_year_pages import LIVE, OLD, parse_tables, split_stn

OLD_PAGES = {  # year -> (BLA approvals, BLA supplement approvals), ucm ids of the old yearly pages
    2008: ("ucm173571", "ucm172240"), 2009: ("ucm167930", "ucm167932"), 2010: ("ucm201369", "ucm207053"),
    2011: ("ucm242933", "ucm242934"), 2012: ("ucm289008", "ucm289009"), 2013: ("ucm338259", "ucm338262"),
    2014: ("ucm385847", "ucm385849"),
}
LIVE_YEARS = (2026,)  # after the main steps' last year
ORIGINAL = ["original_bla", "diagnostic_device", "blood_establishment", "further_manufacturing"]
SUPPLEMENT = sorted(IN_SCOPE_SUPPL) + ["cmc_manufacturing", "diagnostic_device", "blood_establishment",
                                       "strain_or_formula_update"]
CLASSES = ["vaccine", "cell_therapy", "gene_therapy", "blood_plasma_product", "allergenic", "other_biologic"]

SYSTEM = f"""You classify one row of an FDA CBER yearly approval list: a biologics license application (BLA) approval or a BLA supplement approval.

category, for an original BLA: original_bla (a therapeutic or preventive biologic: vaccine, plasma protein, cell or gene therapy, allergenic extract, antitoxin and the like); diagnostic_device (a test kit, blood grouping reagent or other in vitro diagnostic licensed as a biologic); blood_establishment (Source Plasma, whole blood or blood components licensed to a collection establishment); further_manufacturing (an intermediate licensed only for further manufacture).
category, for a supplement: new_indication (a new disease or use); indication_revision (an existing indication narrowed, broadened in wording or otherwise changed); population_expansion (a new age group or population for an existing use); dosing_regimen (a new dose, schedule or route for an existing use); accelerated_to_traditional; new_formulation_clinical (a new formulation or presentation approved on clinical data); clinical_data_labeling (new clinical data added to the label without a new use); cmc_manufacturing (manufacturing, facility, process or presentation changes); diagnostic_device; blood_establishment; strain_or_formula_update (the annual influenza strain change or an equivalent formula update).
For an in-scope row (an original_bla, or a supplement in {', '.join(sorted(IN_SCOPE_SUPPL))}): brand (the trade name as listed), proper_name (the nonproprietary proper name, without the brand) and product_class ({', '.join(CLASSES)}). Otherwise give them empty, with product_class other_biologic. Judge only from the row."""
SCHEMA = {
    "type": "object",
    "properties": {"category": {"type": "string", "enum": sorted(set(ORIGINAL + SUPPLEMENT))},
                   "brand": {"type": "string"}, "proper_name": {"type": "string"},
                   "product_class": {"type": "string", "enum": CLASSES}},
    "required": ["category", "brand", "proper_name", "product_class"],
    "additionalProperties": False,
}


def validate(p: dict, out: dict) -> None:
    allowed = ORIGINAL if p["kind"] == "BLA" else SUPPLEMENT
    if out["category"] not in allowed:
        raise ValueError(f"{out['category']} is not a category for a {p['kind']} row")
    if in_scope(p["kind"], out["category"]) and not (out["brand"].strip() or out["proper_name"].strip()):
        raise ValueError("an in-scope row without a brand or proper name")


TASK = llm.Task(name="cber_listing_scope", prompt_version="v1", schema_version="v1", system=SYSTEM, schema=SCHEMA,
                render=lambda p: (f"List: {'BLA approvals' if p['kind'] == 'BLA' else 'BLA supplement approvals'} "
                                  f"{p['year']}\nProduct: {p['name']}\nIndication or change: {p['indication'] or '-'}\n"
                                  f"STN: {p['stn']}\nManufacturer: {p['manufacturer'] or '-'}"),
                validate=validate, subject_type="cber_listing", model="claude-sonnet-5", effort="low",
                max_tokens=1000)


def in_scope(kind: str, category: str) -> bool:
    return category == "original_bla" if kind == "BLA" else category in IN_SCOPE_SUPPL


def pages() -> list[tuple[int, str, str, list[str]]]:
    """(year, kind, listing page, URLs to read): every Wayback capture of an old page, the live page itself."""
    out = [(year, kind, "https://" + OLD + ucm + ".htm", [fetch.wayback(c) for c in fetch.cdx(OLD + ucm + ".htm")])
           for year, ucms in OLD_PAGES.items() for kind, ucm in zip(("BLA", "SUPPL"), ucms)]
    for year in LIVE_YEARS:
        for kind, slug in (("BLA", "biological-license-application-approvals"),
                           ("SUPPL", "biological-license-application-supplement-noteworthy-approvals")):
            out.append((year, kind, f"{LIVE}{year}-{slug}", [f"{LIVE}{year}-{slug}"]))
    return out


def rows() -> list[dict]:
    """Every row of the yearly pages outside the main steps, pooled over all reads of each page."""
    out = []
    for year, kind, page, urls in pages():
        seen = {}
        for url in urls:
            html, _path, _final, _status = fetch.get_html(url)
            for r in parse_tables(html or "", page):
                key = (re.sub(r"\s+", "", r["stn"]), r["approval_date"], r["name"][:30])
                if r["stn"] and key not in seen:
                    appl, sub = split_stn(r["stn"])
                    seen[key] = {"year": year, "kind": kind, "appl_no": appl, "stn_suppl": sub,
                                 "listing_page": page, **r}
        out += seen.values()
        print(year, kind, len(seen), flush=True)
    return out


def record(r: dict, out: dict) -> dict:
    """An index record in the CDER letter format, documented by the yearly listing row."""
    orig = r["kind"] == "BLA"
    return {"appl_no": r["appl_no"], "appl_type": "BLA", "submission_type": "ORIG" if orig else "SUPPL",
            "submission_no": "1" if orig else r["stn_suppl"], "submission_class_code_id": None,
            "approval_date": r["approval_date"], "review_priority": None, "sponsor": r["manufacturer"] or None,
            "url": r["listing_page"], "doc_date": r["approval_date"], "doc_title": None, "error": "no_letter_pdf",
            "sha256": None, "n_bytes": None, "text": r["row_text"], "center": "CBER",
            "product_brand": out["brand"] or None, "proper_name": out["proper_name"] or None,
            "product_class": out["product_class"], "is_vaccine": out["product_class"] == "vaccine",
            "change_category": out["category"], "listed_on_yearly_page": True, "yearly_listing_page": r["listing_page"],
            "yearly_listing_text": r["row_text"]}


def main() -> None:
    listed = [r for r in rows() if r["appl_no"] and r["approval_date"] and (r["kind"] == "BLA" or r["stn_suppl"])]
    items = {f"{r['appl_no']}/{r['stn_suppl'] or 0}/{r['approval_date']}": {
        "year": r["year"], "kind": r["kind"], "name": r["name"], "indication": r["indication"], "stn": r["stn"],
        "manufacturer": r["manufacturer"]} for r in listed}
    decided = {k: out for k, _, out in llm.decisions(llm.run(TASK, items))}
    index = list({k: record(r, decided[k]) for r in listed  # one record per action, however many rows list it
                  if (k := f"{r['appl_no']}/{r['stn_suppl'] or 0}/{r['approval_date']}") in decided
                  and in_scope(r["kind"], decided[k]["category"])}.values())
    index.sort(key=lambda x: (x["approval_date"], x["appl_no"], int(x["submission_no"])))
    fetch.write_jsonl("letters_index_other.jsonl", index)
    print(f"rows={len(listed)} decided={len(decided)} in scope={len(index)} "
          f"(originals {sum(x['submission_type'] == 'ORIG' for x in index)})")


if __name__ == "__main__":
    main()
