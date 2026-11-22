"""pipeline.target_origin and the small generalisations it needs in pipeline.literature. No database."""
from __future__ import annotations

import pandas as pd
import pytest

from pipeline import literature
from pipeline import target_origin as to


def test_pubmed_ids_uses_the_callers_term_builder(monkeypatch):
    seen = []
    monkeypatch.setattr(literature, "pubmed_count", lambda term: seen.append(term) or 3)
    monkeypatch.setattr(literature, "eutils", lambda endpoint, **kw: "<r><IdList><Id>1</Id><Id>2</Id></IdList></r>")
    term, total, ids = literature.pubmed_ids(["x"], 2007, term=lambda lo, hi: f"CUSTOM {lo}..{hi}")
    assert term == "CUSTOM 1900..2007" and total == 3 and ids == ["1", "2"]
    assert seen == ["CUSTOM 1900..2007"]


def test_pubmed_ids_default_term_is_unchanged(monkeypatch):
    monkeypatch.setattr(literature, "pubmed_count", lambda term: 0)
    monkeypatch.setattr(literature, "eutils", lambda endpoint, **kw: "<r><IdList></IdList></r>")
    term, _, _ = literature.pubmed_ids(["x"], 2007)
    assert term == literature.pubmed_term(["x"], "1900", "2007")


def test_epmc_records_uses_the_callers_query(monkeypatch):
    posted = []
    monkeypatch.setattr(literature, "epmc_post",
                        lambda q, cursor="*", log=print, **kw: posted.append(q) or {"hitCount": 0, "resultList": {"result": []}})
    q, total, out = literature.epmc_records(["x"], 2007, query="MY QUERY")
    assert posted == ["MY QUERY"] and q == "MY QUERY" and total == 0 and out == []


# --- names, queries, records, bundle (pipeline.target_origin) ---

def hgnc(**kw) -> pd.DataFrame:
    row = {"symbol": "MET", "name": "MET proto-oncogene, receptor tyrosine kinase", "prev_symbols": [], "alias_symbols": []}
    row.update(kw)
    return pd.DataFrame([row])


def test_a_short_symbol_gives_way_to_the_other_names():
    names = to.gene_names("MET", hgnc(alias_symbols=["HGFR", "c-Met", "RCCP2"]), "hepatocyte growth factor receptor")
    assert names[0] == "hepatocyte growth factor receptor" and "MET" not in names
    assert "HGFR" in names and "c-Met" in names


def test_gene_names_drops_identifiers_and_caps():
    aliases = [f"ALIAS{i:02d}X" for i in range(15)] + ["(2S)-2-amino", "Q9UQ80"]
    names = to.gene_names("TNF", hgnc(symbol="TNF", name="tumor necrosis factor", alias_symbols=aliases), None)
    assert names[0] == "tumor necrosis factor" and "(2S)-2-amino" not in names and "Q9UQ80" not in names
    assert len(names) == to.MAX_GENE_NAMES
    assert len({n.lower() for n in names}) == len(names)


def test_disease_names_shortest_first_and_capped():
    synonyms = ["RA", "rheumatoid arthritis", "arthritis, rheumatoid"] + [f"synonym number {i}" for i in range(30)]
    names = to.disease_names("Rheumatoid Arthritis", synonyms)
    assert names[0] == "Rheumatoid Arthritis"
    assert "RA" not in names  # shorter than four characters
    assert "rheumatoid arthritis" not in names[1:]  # case-insensitive duplicate of the label
    assert len(names) == to.MAX_DISEASE_NAMES
    rest = names[1:]
    assert rest == sorted(rest, key=len)


def test_pair_term_has_both_clauses_and_no_review_exclusion():
    term = to.pair_term(["TNF"], ["rheumatoid arthritis"])("1900", "2007")
    assert term == '("TNF"[tiab]) AND ("rheumatoid arthritis"[tiab]) AND ("1900"[dp] : "2007"[dp])'


def test_pair_epmc_query_ends_the_year_before_the_cutoff():
    q = to.pair_epmc_query(["TNF", "TNF-alpha"], ["rheumatoid arthritis"], 2008)
    assert 'TITLE_ABS:"TNF" OR TITLE_ABS:"TNF-alpha"' in q and 'TITLE_ABS:"rheumatoid arthritis"' in q
    assert "PUB_YEAR:[1900 TO 2007]" in q and "NOT SRC:MED" in q and "HAS_ABSTRACT:Y" in q and "review" not in q


def test_records_without_a_year_or_on_or_after_the_cutoff_are_dropped():
    fetched = [("1", "T1", "A", "J", 1999, "10.1/x", "abs"), ("2", "T2", "A", "J", None, None, "abs"),
               ("3", "T3", "A", "J", 2008, None, "abs"), ("4", "T4", "A", "J", 2007, None, None)]
    rows = to.pubmed_rows(fetched, 2008)
    assert [r["record_id"] for r in rows] == ["PMID:1", "PMID:4"]
    assert rows[0] == {"record_id": "PMID:1", "service": "pubmed", "title": "T1", "abstract": "abs", "year": 1999,
                       "doi": "10.1/x"}
    epmc = [("PPR:1", "PPR", "T", "abs", 2001, None), ("PPR:2", "PPR", "T", "abs", 2009, None),
            ("PPR:3", "PPR", "T", "abs", None, None)]
    assert [r["record_id"] for r in to.epmc_rows(epmc, 2008)] == ["PPR:1"]
    assert to.epmc_rows(epmc, 2008)[0]["service"] == "europepmc"


def rows_for(n: int) -> list[dict]:
    return [{"record_id": f"PMID:{i}", "service": "pubmed", "title": f"T{i}", "abstract": "x" * 2000,
             "year": 1950 + i, "doi": None} for i in range(1, n + 1)]


def test_bundle_takes_earliest_25_and_latest_15_without_repeats():
    ranked = to.ranked(rows_for(60))
    assert [r["rank"] for r in ranked][:3] == [1, 2, 3]
    b = to.bundle(ranked)
    assert len(b) == 40
    assert [r["rank"] for r in b] == list(range(1, 26)) + list(range(46, 61))
    assert len(to.bundle(to.ranked(rows_for(30)))) == 30


def test_bundle_cuts_abstracts():
    b = to.bundle(to.ranked(rows_for(3)))
    assert all(len(r["abstract"]) == to.ABSTRACT_CHARS for r in b)


# --- command line (pipeline.target_disease registers the origin commands) ---

def test_cli_registers_every_command():
    from pipeline import target_disease
    ap = target_disease.parser()
    a = ap.parse_args(["search", "--pairs", "window", "--redo", "--max-records", "3000"])
    assert a.fn.__name__ == "search" and a.pairs == "window" and a.redo and a.max_records == 3000
    assert ap.parse_args(["search"]).pairs == "pilot" and ap.parse_args(["search"]).max_records is None
    a = ap.parse_args(["gate", "--hand-check", "x.csv", "--reader", "Stephen"])
    assert a.fn.__name__ == "gate" and a.hand_check == "x.csv" and a.reader == "Stephen" and a.set == "a"
    a = ap.parse_args(["package", "--set", "b", "--out", "p.html"])
    assert a.fn.__name__ == "package" and a.set == "b" and a.out == "p.html"
    assert ap.parse_args(["label", "--hide-provisional"]).hide_provisional
    assert ap.parse_args(["blind"]).pairs == "set_a"
    for cmd in ["check", "sample", "summary", "build", "provisional"]:
        assert ap.parse_args([cmd]).fn.__name__ == cmd


# --- labelling: validation, rendering, rows ---

URL = "https://patents.google.com/patent/US123"


def label_payload() -> dict:
    return {"ensembl_id": "ENSG1", "mondo_id": "MONDO:1", "symbol": "TNF", "gene_name": "tumor necrosis factor",
            "disease": "rheumatoid arthritis", "cutoff_year": 2008, "n_records_total": 2,
            "records": [{"record_id": "PMID:1", "year": 1999, "title": "T1", "abstract": "a", "rank": 1},
                        {"record_id": "MED:2", "year": 2003, "title": "T2", "abstract": "b", "rank": 2}],
            "first_program": {"entity": "drug x", "sponsor": "Sponsor", "phase": 2, "entry": "2008-03-01",
                              "nct_ids": ["NCT00000001"]},
            "provisional_origin": "mouse_genetics", "provisional_year": 1995}


def good_label() -> dict:
    return {"origin": "diseased_tissue", "origin_year": 1999, "secondary_origin": "mouse_genetics", "grade": "stated",
            "quote": "TNF is raised in synovium", "sources": ["PMID:1"], "source_years": [1999], "rationale": "r",
            "discovery_route": "derived_from_active", "route_quote": "derived from", "route_sources": ["MED:2"],
            "route_source_years": [2003], "retrieved_urls": [URL]}


UNCLEAR = {"origin": "unclear", "origin_year": None, "secondary_origin": None, "grade": "none", "quote": "",
           "sources": [], "source_years": [], "discovery_route": "unclear", "route_quote": "", "route_sources": [],
           "route_source_years": []}


@pytest.mark.parametrize("change, ok", [
    ({}, True),
    (UNCLEAR, True),
    ({"sources": [URL], "source_years": [2005], "origin_year": 2005}, True),
    ({"secondary_origin": "diseased_tissue"}, False),
    ({"origin": "unclear"}, False),
    ({"grade": "none"}, False),
    ({"quote": "  "}, False),
    ({"sources": ["PMID:9"], "source_years": [1999]}, False),
    ({"source_years": [2000]}, False),
    ({"sources": [URL], "source_years": [2008], "origin_year": 2008}, False),
    ({"sources": ["PMID:1", URL], "source_years": [1999]}, False),
    ({"origin_year": 1997}, False),
    ({**UNCLEAR, "origin_year": 1999}, False),
    ({"discovery_route": "unclear"}, False),
    ({"route_sources": [], "route_source_years": []}, False),
    ({"route_sources": ["MED:2"], "route_source_years": [2004]}, False),
    ({"origin": "not_a_category"}, False),
])
def test_validate_label(change, ok):
    out = {**good_label(), **change}
    if ok:
        to.validate_label(label_payload(), out)
    else:
        with pytest.raises(ValueError):
            to.validate_label(label_payload(), out)


def test_render_label_omits_the_provisional_line_when_hidden():
    shown = to.render_label(label_payload())
    assert "mouse_genetics" in shown and "1995" in shown and "PMID:1" in shown and "NCT00000001" in shown
    assert "2007 or earlier" in shown
    hidden = to.render_label({**label_payload(), "provisional_origin": None, "provisional_year": None})
    assert "PROVISIONAL" not in hidden and "mouse_genetics" not in hidden


def test_undecided_is_the_items_not_in_decided():
    items = {"a": {"x": 1}, "b": {"x": 2}}
    assert to.undecided(items, [("a", 1, {})]) == {"b": {"x": 2}}


def test_origin_rows_follow_the_insert_order():
    rows = to.origin_rows([("ENSG1|MONDO:1", 77, good_label())])
    assert rows == [("ENSG1", "MONDO:1", "labelled", "diseased_tissue", 1999, "mouse_genetics", "stated", ["PMID:1"],
                     "TNF is raised in synovium", 77, to.LABEL_METHOD, "not_checked", "derived_from_active",
                     "derived from", ["MED:2"])]
    unclear = to.origin_rows([("ENSG1|MONDO:1", 78, {**good_label(), **UNCLEAR})])[0]
    assert unclear[3:9] == ("unclear", None, None, "none", [], None) and unclear[12:15] == ("unclear", None, [])


def test_replace_rows_only_touches_the_keys_it_decided():
    keys = [("ENSG1", "MONDO:1"), ("ENSG2", "MONDO:2")]
    sql, params = to.replace_sql(keys)
    assert "WHERE basis = 'labelled' AND (ensembl_id, mondo_id) IN %s" in sql
    assert params == (tuple(keys),)


# --- check and blind coder ---

@pytest.mark.parametrize("out, outcome", [
    ({"quote_found": "yes", "year_ok": "yes", "origin_follows": "yes"}, "supported"),
    ({"quote_found": "yes", "year_ok": "yes", "origin_follows": "partly"}, "supported"),
    ({"quote_found": "no", "year_ok": "yes", "origin_follows": "yes"}, "unsupported"),
    ({"quote_found": "yes", "year_ok": "no", "origin_follows": "yes"}, "unsupported"),
    ({"quote_found": "yes", "year_ok": "yes", "origin_follows": "no"}, "unsupported"),
    ({"quote_found": "could_not_open", "year_ok": "unknown", "origin_follows": "yes"}, "unverified"),
    ({"quote_found": "could_not_open", "year_ok": "no", "origin_follows": "yes"}, "unsupported"),
])
def test_check_outcome(out, outcome):
    assert to.check_outcome({**out, "note": ""}) == outcome


def blind_payload() -> dict:
    p = label_payload()
    return {k: p[k] for k in ["ensembl_id", "mondo_id", "symbol", "gene_name", "disease", "cutoff_year",
                              "n_records_total", "records"]}


def test_validate_blind_rejects_a_source_outside_the_bundle():
    good = {"origin": "diseased_tissue", "secondary_origin": None, "grade": "pattern", "quote": "q",
            "source": "PMID:1", "source_year": 1999, "note": ""}
    to.validate_blind(blind_payload(), good)
    for bad in [{"source": URL}, {"source": "PMID:9"}, {"source_year": 2000}, {"origin": "unclear"},
                {"grade": "none"}, {"secondary_origin": "diseased_tissue"}]:
        with pytest.raises(ValueError):
            to.validate_blind(blind_payload(), {**good, **bad})
    to.validate_blind(blind_payload(), {"origin": "unclear", "secondary_origin": None, "grade": "none", "quote": "",
                                        "source": None, "source_year": None, "note": ""})


def test_render_blind_shows_no_provisional_origin_and_no_program():
    text = to.render_blind(blind_payload())
    assert "PMID:1" in text and "2007 or earlier" in text
    assert "PROVISIONAL" not in text and "PROGRAM" not in text and "mouse_genetics" not in text


# --- pilot sample and reader package ---

def cohort_and_modes(n: int = 300):
    cohort = pd.DataFrame({"ensembl_id": [f"ENSG{i:04d}" for i in range(n)], "mondo_id": ["MONDO:1"] * n})
    modes = []
    for i in range(n):
        if i % 3 == 0:
            modes.append((f"ENSG{i:04d}", "MONDO:1", "not_causal"))
        if i % 5 == 0:
            modes.append((f"ENSG{i:04d}", "MONDO:1", "unresolved"))
        if i % 7 == 0:
            modes.append((f"ENSG{i:04d}", "MONDO:1", "drug_fell_short"))
    return cohort, pd.DataFrame(modes, columns=["ensembl_id", "mondo_id", "mode"])


def test_sample_excludes_unresolved_and_splits_sets():
    cohort, modes = cohort_and_modes()
    s = to.sample_pairs(cohort, modes, seed=to.PILOT_SEED)
    assert list(s.columns) == ["ensembl_id", "mondo_id", "group", "hand_check_set"]
    assert s.group.value_counts().to_dict() == {"not_causal": 50, "other": 50}
    assert s.groupby(["group", "hand_check_set"]).size().to_dict() == {("not_causal", "a"): 25, ("not_causal", "b"): 25,
                                                                       ("other", "a"): 25, ("other", "b"): 25}
    assert s.ensembl_id.is_unique
    unresolved = set(modes[modes["mode"] == "unresolved"].ensembl_id)
    assert not set(s.ensembl_id) & unresolved
    nc = set(modes[modes["mode"] == "not_causal"].ensembl_id)
    assert set(s[s.group == "not_causal"].ensembl_id) <= nc
    assert not set(s[s.group == "other"].ensembl_id) & nc
    again = to.sample_pairs(cohort, modes, seed=to.PILOT_SEED)
    assert again.equals(s)
    assert not to.sample_pairs(cohort, modes, seed=1).equals(s)


def test_sample_takes_fewer_when_a_group_is_small():
    cohort, modes = cohort_and_modes(40)
    s = to.sample_pairs(cohort, modes, seed=to.PILOT_SEED)
    nc = s[s.group == "not_causal"]
    assert 0 < len(nc) < 50 and set(nc.hand_check_set) <= {"a", "b"}


def package_rows() -> list[dict]:
    p = label_payload()
    return [{**p, "hand_check_set": "a", "group": "other"},
            {**p, "ensembl_id": "ENSG2", "symbol": "IL6", "gene_name": "interleukin 6", "mondo_id": "MONDO:2",
             "disease": "asthma", "hand_check_set": "a", "group": "not_causal",
             "records": [{"record_id": "PMID:77", "year": 1990, "title": "Unique title seven", "abstract": "z",
                          "rank": 1}], "n_records_total": 1}]


def test_package_holds_every_pair_and_no_label():
    html = to.render_package(package_rows(), "# Codebook\n\nDefinitions here.", "a")
    assert "ENSG1|MONDO:1" in html and "ENSG2|MONDO:2" in html
    assert "Unique title seven" in html and "pubmed.ncbi.nlm.nih.gov/77" in html
    assert "patents.google.com" in html and "before=priority:20080101" in html
    assert "Definitions here." in html and "mouse_genetics" in html  # the provisional origin the model also saw
    assert "retrieved_urls" not in html and "labelled" not in html and "diseased_tissue</option>" in html
    assert "<title>Target origin hand check" in html and len(html.encode()) < 16_000_000


# --- gate ---

def test_every_origin_has_a_broad_category():
    assert set(to.CATEGORY) == set(to.ORIGINS) | set(to.STORED_ONLY)
    assert to.CATEGORY["human_genetics"] == to.CATEGORY["tumour_genetics"] == "human_genetics"
    assert to.CATEGORY["diseased_tissue"] == to.CATEGORY["cell_line_perturbation"] == "in_vitro"
    assert to.CATEGORY["mouse_genetics"] == to.CATEGORY["animal_model_pharmacology"] == "animals"
    assert to.CATEGORY["unclear"] == "unclear"


def gate_frames(disagree: int):
    keys = [(f"ENSG{i:03d}", "MONDO:1") for i in range(50)]
    origins = [to.ORIGINS[i % 12] for i in range(50)]  # every category but unclear, in rotation
    reader = pd.DataFrame([(e, m, o) for (e, m), o in zip(keys, origins)], columns=["ensembl_id", "mondo_id", "origin"])
    stored_origins = list(origins)
    for i in range(disagree):
        stored_origins[i] = to.ORIGINS[(i + 1) % 12]
    stored = pd.DataFrame([(e, m, o) for (e, m), o in zip(keys, stored_origins)],
                          columns=["ensembl_id", "mondo_id", "origin"])
    raw = pd.DataFrame([(e, m, o, None) for (e, m), o in zip(keys, stored_origins)],
                       columns=["ensembl_id", "mondo_id", "origin", "secondary_origin"])
    return reader, stored, raw


def test_gate_passes_at_kappa_point_six_and_gap_ten():
    from sklearn.metrics import cohen_kappa_score
    reader, stored, raw = gate_frames(disagree=10)
    expected = cohen_kappa_score(reader.origin, stored.origin)
    r = to.gate_result(reader, stored, raw, {"not_causal": 0.80, "other": 0.90}, None)
    assert r["n"] == 50 and abs(r["kappa_stored"] - expected) < 1e-9 and r["kappa_raw"] == r["kappa_stored"]
    assert r["gap_points"] == 10.0 and r["pass"] is True and r["kappa_blind_vs_reader"] is None
    assert 0 < r["any_origin_agree"] <= 1
    assert to.gate_result(reader, stored, raw, {"not_causal": 0.78, "other": 0.90}, None)["pass"] is False
    reader, stored, raw = gate_frames(disagree=30)
    assert to.gate_result(reader, stored, raw, {"not_causal": 0.80, "other": 0.90}, None)["pass"] is False


def test_gate_reports_blind_kappas_only_when_given():
    reader, stored, raw = gate_frames(disagree=0)
    blind = reader.rename(columns={"origin": "blind_origin"})
    r = to.gate_result(reader, stored, raw, {"not_causal": 0.9, "other": 0.9}, blind)
    assert r["kappa_blind_vs_reader"] == 1.0 and r["kappa_blind_vs_raw"] == 1.0
    assert r["kappa_stored_category"] == 1.0


# --- model reference: majority of three blind readings ---

def test_majority_reference_and_consistency():
    readings = [("ENSG1|MONDO:1|r1", "human_genetics"), ("ENSG1|MONDO:1|r2", "human_genetics"),
                ("ENSG1|MONDO:1|r3", "mouse_genetics"),
                ("ENSG2|MONDO:1|r1", "unclear"), ("ENSG2|MONDO:1|r2", "unclear"), ("ENSG2|MONDO:1|r3", "unclear"),
                ("ENSG3|MONDO:1|r1", "cell_line_perturbation"), ("ENSG3|MONDO:1|r2", "diseased_tissue"),
                ("ENSG3|MONDO:1|r3", "unclear"),
                ("ENSG4|MONDO:1|r1", "cell_line_perturbation"), ("ENSG4|MONDO:1|r2", "cell_line_perturbation")]
    ref, stats = to.majority_reference(readings)
    assert ref.set_index("ensembl_id").origin.to_dict() == {"ENSG1": "human_genetics", "ENSG2": "unclear",
                                                            "ENSG4": "cell_line_perturbation"}
    assert stats["pairs"] == 4 and stats["unanimous"] == 1 and stats["majority"] == 2 and stats["no_majority"] == 1
    assert stats["replicates"] == 3 and 0 <= stats["pairwise_agreement"] <= 1


def test_blind_items_carry_the_replicate_in_key_and_payload():
    base = {"ENSG1|MONDO:1": {"ensembl_id": "ENSG1", "records": []}}
    items = to.replicate_items(base, 3)
    assert set(items) == {"ENSG1|MONDO:1|r1", "ENSG1|MONDO:1|r2", "ENSG1|MONDO:1|r3"}
    assert items["ENSG1|MONDO:1|r2"]["replicate"] == 2 and items["ENSG1|MONDO:1|r2"]["ensembl_id"] == "ENSG1"
    assert to.split_key("ENSG1|MONDO:1|r2") == ("ENSG1", "MONDO:1")


def test_bundle_tolerates_missing_abstracts_from_a_dataframe():
    import numpy as np
    rows = to.ranked([{"record_id": "PMID:1", "service": "pubmed", "title": "T", "abstract": None, "year": 1999, "doi": None},
                      {"record_id": "PMID:2", "service": "pubmed", "title": "T", "abstract": np.nan, "year": 2000, "doi": np.nan}])
    assert [r["abstract"] for r in to.bundle(rows)] == ["", ""]
    df = pd.DataFrame(rows)
    assert all(r["abstract"] is None for r in to.records_from(df))


def test_schemas_express_nullable_enums_with_anyof():
    for schema in [to.LABEL_SCHEMA, to.BLIND_SCHEMA]:
        sec = schema["properties"]["secondary_origin"]
        assert "enum" not in sec and "type" not in sec
        assert sec["anyOf"] == [{"type": "string", "enum": to.ORIGINS}, {"type": "null"}]
        for prop in schema["properties"].values():
            assert None not in prop.get("enum", [])


def test_check_payload_has_no_nan():
    import json

    import numpy as np
    row = {"ensembl_id": "ENSG1", "mondo_id": "MONDO:1", "origin": "diseased_tissue", "origin_year": 1999.0,
           "secondary_origin": np.nan, "grade": "stated", "quote": np.nan, "sources": ["PMID:1"], "llm_decision_id": 7,
           "parsed_output": {"source_years": [1999]}}
    base = {"ensembl_id": "ENSG1", "mondo_id": "MONDO:1", "symbol": "TNF", "disease": "RA", "cutoff_year": 2008}
    p = to.check_payload(row, base, [{"record_id": "PMID:1", "year": 1999, "title": "T", "abstract": None},
                                     {"record_id": "PMID:2", "year": 2000, "title": "U", "abstract": "x"}])
    assert p["secondary_origin"] is None and p["quote"] == "" and p["origin_year"] == 1999
    assert [r["record_id"] for r in p["records"]] == ["PMID:1"] and p["label_decision_id"] == 7
    json.dumps(p, allow_nan=False)


# --- the re-run's three fixes: protein names, a web-enabled reference reader, a checker that reads PubMed itself ---

def test_protein_names_are_read_from_uniprot_and_hgnc_documents():
    uni = {"proteinDescription": {"recommendedName": {"fullName": {"value": "Prostacyclin receptor"},
                                                      "shortNames": [{"value": "IP"}]},
                                  "alternativeNames": [{"fullName": {"value": "Prostaglandin I2 receptor"},
                                                        "shortNames": [{"value": "PGI receptor"}, {"value": "PGI2 receptor"}]},
                                                       {"fullName": {"value": "Prostanoid IP receptor"}}]}}
    assert to.uniprot_names(uni) == ["Prostacyclin receptor", "IP", "Prostaglandin I2 receptor", "PGI receptor",
                                     "PGI2 receptor", "Prostanoid IP receptor"]
    hg = {"alias_name": ["prostacyclin receptor"], "prev_name": ["prostaglandin I2 (prostacyclin) receptor (IP)"]}
    assert to.hgnc_names(hg) == ["prostacyclin receptor", "prostaglandin I2 (prostacyclin) receptor (IP)"]
    assert to.uniprot_names({}) == [] and to.hgnc_names({}) == []


def test_gene_names_merge_protein_names_after_the_symbol_and_name():
    protein = ["Prostacyclin receptor", "IP", "Prostaglandin I2 receptor", "PGI2 receptor", "prostacyclin receptor",
               "prostaglandin I2 (prostacyclin) receptor (IP)"]
    names = to.gene_names("PTGIR", hgnc(symbol="PTGIR", name="prostaglandin I2 receptor", alias_symbols=["IP"]),
                          "prostaglandin I2 receptor", protein)
    assert names[:2] == ["PTGIR", "prostaglandin I2 receptor"]
    assert "Prostacyclin receptor" in names and "PGI2 receptor" in names
    assert "IP" not in names and "prostaglandin I2 (prostacyclin) receptor (IP)" not in names
    assert len({n.lower() for n in names}) == len(names) and len(names) <= to.MAX_GENE_NAMES


def test_blind_reader_may_cite_a_retrieved_url_before_the_cutoff():
    assert to.BLIND_TASK.tools
    base = {"origin": "clinical_observation", "secondary_origin": None, "grade": "stated", "quote": "q",
            "source": URL, "source_year": 2005, "note": "", "retrieved_urls": [URL]}
    to.validate_blind(blind_payload(), base)
    for bad in [{"retrieved_urls": []}, {"source_year": 2008}, {"source": "PMID:1", "source_year": 2000}]:
        with pytest.raises(ValueError):
            to.validate_blind(blind_payload(), {**base, **bad})
    to.validate_blind(blind_payload(), {**base, "source": "PMID:1", "source_year": 1999})


def test_pmid_from_url():
    assert to.pmid_from_url("https://pubmed.ncbi.nlm.nih.gov/12345/") == "12345"
    assert to.pmid_from_url("https://www.ncbi.nlm.nih.gov/pubmed/12345") == "12345"
    assert to.pmid_from_url("https://europepmc.org/article/MED/12345") == "12345"
    assert to.pmid_from_url("https://europepmc.org/abstract/MED/12345?x=1") == "12345"
    assert to.pmid_from_url("https://pmc.ncbi.nlm.nih.gov/articles/PMC123/") is None
    assert to.pmid_from_url("https://patents.google.com/patent/US123") is None
    assert to.pmid_from_url("PMID:77") is None


def test_check_payload_resolves_pubmed_urls_into_records():
    row = {"ensembl_id": "ENSG1", "mondo_id": "MONDO:1", "origin": "diseased_tissue", "origin_year": 1999,
           "secondary_origin": None, "grade": "stated", "quote": "q",
           "sources": ["https://pubmed.ncbi.nlm.nih.gov/555/", "PMID:1"], "llm_decision_id": 7,
           "parsed_output": {"source_years": [2001, 1999]}}
    base = {"ensembl_id": "ENSG1", "mondo_id": "MONDO:1", "symbol": "TNF", "disease": "RA", "cutoff_year": 2008}
    calls = []
    def fetch(pmids):
        calls.append(list(pmids))
        return [("555", "Fetched title", "A", "J", 2001, None, "fetched abstract")]
    p = to.check_payload(row, base, [{"record_id": "PMID:1", "year": 1999, "title": "T", "abstract": "a"}], fetch=fetch)
    assert calls == [["555"]]
    assert [(r["record_id"], r["year"]) for r in p["records"]] == [("PMID:1", 1999), ("PMID:555", 2001)]
    assert p["records"][1]["url"] == "https://pubmed.ncbi.nlm.nih.gov/555/"
    assert p["sources"] == ["https://pubmed.ncbi.nlm.nih.gov/555/", "PMID:1"]


# --- review fix pass ---

def test_short_symbol_is_searched_only_when_it_is_the_only_name():
    assert to.gene_names("AR", hgnc(symbol="AR", name="androgen receptor"), None, ["Androgen receptor"]) == ["androgen receptor"]
    assert to.gene_names("AR", hgnc(symbol="AR", name="", alias_symbols=[]), None, []) == ["AR"]
    assert to.gene_names("KDR", hgnc(symbol="KDR", name="kinase insert domain receptor"), None,
                         ["Vascular endothelial growth factor receptor 2", "VEGFR-2"])[0] == "kinase insert domain receptor"
    assert to.gene_names("PTGIR", hgnc(symbol="PTGIR", name="prostaglandin I2 receptor"), None, [])[0] == "PTGIR"


def test_hide_provisional_is_part_of_the_decision_input():
    assert "provisional_shown" not in to.CONTEXT and "first_program" in to.CONTEXT
    p = label_payload()
    assert to.own_input({**p, "provisional_shown": False}) != to.own_input({**p, "provisional_shown": True})
    assert "first_program" not in to.own_input(p) and "records" in to.own_input(p)


def test_check_task_ignores_the_label_decision_id():
    assert "label_decision_id" in to.CHECK_CONTEXT


def test_origin_services_filter_every_shared_table_read():
    assert to.ORIGIN_SERVICES == ("pubmed", "europepmc")
    for sql in [to.DELETE_SOURCES, to.DELETE_SEARCH, to.SEARCHED_SQL, to.SOURCES_SQL, to.COVERED_SQL]:
        assert "service IN %s" in sql or "service IN ('pubmed', 'europepmc')" in sql


def test_majority_needs_two_agreeing_readings():
    ref, stats = to.majority_reference([("ENSG4|MONDO:1|r1", "cell_line_perturbation")])
    assert ref.empty and stats["no_majority"] == 1


def test_gate_counts_missing_labels_as_disagreement_and_stratifies_by_coverage():
    reader, stored, raw = gate_frames(disagree=0)
    stored = stored.iloc[:-2]  # two pairs the labeller never decided
    raw = raw.iloc[:-2]
    covered = {(e, m) for e, m in zip(reader.ensembl_id[:30], reader.mondo_id[:30])}
    r = to.gate_result(reader, stored, raw, {"not_causal": 0.9, "other": 0.9}, None, covered=covered)
    assert r["n"] == 50 and r["n_missing"] == 2 and r["kappa_stored"] < 1.0
    assert r["n_covered"] == 30 and r["kappa_covered"] == 1.0 and r["kappa_uncovered"] < 1.0


def test_validation_loose_ends():
    out = {**good_label(), **UNCLEAR, "source_years": [1999]}
    with pytest.raises(ValueError):
        to.validate_label(label_payload(), out)
    with pytest.raises(ValueError):
        to.validate_label(label_payload(), {**good_label(), **UNCLEAR, "secondary_origin": "mouse_genetics"})
    with pytest.raises(ValueError):
        to.validate_label(label_payload(), {**good_label(), "discovery_route": "unclear", "route_quote": "",
                                            "route_sources": [], "route_source_years": [2003]})


def test_sample_refuses_to_overwrite_without_force():
    from pipeline import target_disease
    ap = target_disease.parser()
    assert ap.parse_args(["sample"]).force is False and ap.parse_args(["sample", "--force"]).force is True


def test_gene_names_drop_disease_labels_that_hgnc_lists_as_aliases():
    protein = ["Androgen receptor", "Kennedy disease", "spinal and bulbar muscular atrophy"]
    names = to.gene_names("AR", hgnc(symbol="AR", name="androgen receptor"), None, protein,
                          exclude={"kennedy disease", "spinal and bulbar muscular atrophy"})
    assert names == ["androgen receptor"]


def test_checker_has_the_labellers_search_and_fetch():
    assert to.CHECK_TASK.prompt_version == "v4"
    assert [t["name"] for t in to.CHECK_TASK.tools] == ["web_search", "web_fetch"]
    assert "search" in to.CHECK_SYSTEM.lower()


# --- the definitions follow the evidence chart's lines (owner's one-list decision of 2026-11-20, #146) ---

def definition_of(origin: str) -> str:
    lines = [ln for ln in to.DEFINITIONS.splitlines() if ln.startswith(f"- {origin}: ")]
    assert len(lines) == 1
    return lines[0]


def test_every_origin_has_one_definition_and_a_chart_line_entry():
    assert [ln[2:].split(":")[0] for ln in to.DEFINITIONS.splitlines()] == to.ORIGINS
    assert set(to.CHART_LINE) == set(to.ORIGINS)
    assert set(to.CHART_LINE_PENDING) == {"observational_biomarker", "human_cell_perturbation", "clinical_observation"}
    without = {o for o, c in to.CHART_LINE.items() if c is None}
    assert without == set(to.CHART_LINE_PENDING) | {"phenotypic_screen", "unclear"}


def test_every_origin_kind_is_a_kind_of_the_evidence_list_with_its_chart_column():
    from report import evidence_lines as ev
    assert {o for o in to.ORIGINS if o not in to.NOT_KINDS} <= set(ev.KINDS)
    assert to.CHART_LINE["cell_line_perturbation"] == "cell_line_perturbation"
    assert to.CHART_LINE["earlier_drug_other_disease"] == "approved_other_disease"
    assert to.CHART_LINE["diseased_tissue"] == "expression" and to.CHART_LINE["mouse_genetics"] == "mouse_genetics"


def test_definitions_follow_the_final_list():
    assert "established cell line" in definition_of("cell_line_perturbation")
    assert "primary human cells" in definition_of("human_cell_perturbation")
    assert "another disease" in definition_of("earlier_drug_other_disease")
    assert "animal model" in definition_of("mouse_genetics")
    assert "RNA or protein" in definition_of("diseased_tissue")
    assert "blood" in definition_of("observational_biomarker")
    assert "other than genetics" in definition_of("animal_model_pharmacology")
    # the texts that produced earlier labels and blind readings are gone, so those versions cannot be reused
    assert to.LABEL_TASK.prompt_version not in ("v1", "v2") and to.BLIND_TASK.prompt_version not in ("v2", "v3")


def test_gate_is_scored_on_the_labellers_label_as_read():
    reader, stored, raw = gate_frames(disagree=0)
    rewritten = stored.copy()
    rewritten.loc[:29, "origin"] = "unclear"  # the check rewrote 30 labels the reference agreed with
    r = to.gate_result(reader, rewritten, raw, {"not_causal": 0.8, "other": 0.9}, None)
    assert r["kappa_raw"] == 1.0 and r["kappa_stored"] < 0.6 and r["pass"] is True and r["gate_origin"] == "raw"
    reader, stored, raw = gate_frames(disagree=30)
    r = to.gate_result(reader, reader, raw, {"not_causal": 0.8, "other": 0.9}, None)  # stored agrees, the label did not
    assert r["kappa_stored"] == 1.0 and r["pass"] is False


def test_gate_message_names_the_kappa_the_gate_is_scored_on():
    r = {"pass": True, "kappa_raw": 0.651, "kappa_stored": 0.552, "gap_points": 8.0, "gate_origin": "raw"}
    m = to.gate_message(r)
    assert m.startswith("gate PASSED") and "0.65" in m and "label as read" in m and "stored 0.55" in m
    assert to.gate_message({**r, "pass": False, "kappa_raw": None}).startswith("gate FAILED: kappa None")


# --- check v2: facts in code, judgment by agreement (#146 note of 2026-11-21) ---

def cpayload(origin="diseased_tissue", sources=("PMID:1",), records=((2005,),), cutoff=2010, **kw) -> dict:
    return {"ensembl_id": "ENSG1", "mondo_id": "MONDO:1", "symbol": "ABC", "disease": "a disease",
            "cutoff_year": cutoff, "origin": origin, "origin_year": 2005, "secondary_origin": None, "grade": "stated",
            "quote": "q", "sources": list(sources), "source_years": [2005] * len(sources),
            "records": [{"record_id": f"PMID:{i + 1}", "year": y, "title": "t", "abstract": "a", "url": None}
                        for i, (y,) in enumerate(records)],
            "label_decision_id": 1, **kw}


def cout(quote="yes", year="yes", follows="yes", note="") -> dict:
    return {"quote_found": quote, "year_ok": year, "origin_follows": follows, "note": note}


def test_checkers_are_sonnet_and_opus_on_the_same_text():
    s, o = to.CHECKERS
    assert s is to.CHECK_TASK and s.model == "claude-sonnet-5-5" and s.prompt_version == "v4"
    assert o.model == "claude-opus-5-5" and o.prompt_version == "v5" and o.system == s.system and o.tools == s.tools
    assert to.CHECK_METHOD == "target_origin_check@v2"
    assert to.CHECK_OUTCOMES == ("supported", "unsupported", "unverified", "disputed", "not_checked")


@pytest.mark.parametrize("a, b, expected", [
    ("yes", "yes", "yes"), ("no", "no", "no"), ("yes", "no", "disputed"), ("no", "yes", "disputed"),
    ("yes", "could_not_open", "yes"), ("could_not_open", "no", "no"),
    ("could_not_open", "could_not_open", "unverified"), ("yes", None, "disputed"), (None, None, "disputed"),
])
def test_agree(a, b, expected):
    assert to.agree(a, b, "could_not_open") == expected


def test_check_fields_judgment_by_agreement_and_partly_counts_as_yes():
    f = to.check_fields(cpayload(), None, [cout(follows="partly"), cout(follows="yes")], None)
    assert f == {"quote": "yes", "year": "yes", "category": "yes", "fact": None}
    assert to.check_fields(cpayload(), None, [cout(follows="no"), cout(follows="partly")], None)["category"] == "disputed"
    assert to.check_fields(cpayload(), None, [cout(quote="no"), cout(quote="no")], None)["quote"] == "no"


def test_check_fields_year_is_read_from_the_records_in_code():
    assert to.check_fields(cpayload(records=((2010,),)), None, [cout(), cout()], None)["year"] == "no"
    # no URL source: the records decide and the checkers' field is not consulted
    assert to.check_fields(cpayload(), None, [cout(year="no"), cout(year="unknown")], None)["year"] == "yes"
    # a URL source: the checkers decide where they agree; unknown carries no information
    p = cpayload(sources=("PMID:1", "https://x"))
    assert to.check_fields(p, None, [cout(year="unknown"), cout(year="no")], None)["year"] == "no"
    assert to.check_fields(p, None, [cout(year="yes"), cout(year="no")], None)["year"] == "disputed"
    assert to.check_fields(p, None, [cout(year="unknown"), cout(year="unknown")], None)["year"] == "unverified"


def test_check_fields_earlier_drug_takes_the_category_from_the_approval_fact():
    p = cpayload(origin="earlier_drug_other_disease")
    assert to.check_fields(p, "unrelated", [cout(follows="no"), cout(follows="no")], None)["category"] == "yes"
    assert to.check_fields(p, "related", [cout(), cout()], None)["category"] == "yes"
    assert to.check_fields(p, "close", [cout(), cout()], None)["category"] == "no"
    f = to.check_fields(p, "none", [cout(), cout()], None)
    assert f["category"] == "disputed" and f["fact"] == "none"


def test_check_fields_a_human_verdict_settles_a_dispute():
    f = to.check_fields(cpayload(), None, [cout(follows="no"), cout(follows="yes")], {"category": "yes"})
    assert f["category"] == "yes"
    p = cpayload(origin="earlier_drug_other_disease")
    assert to.check_fields(p, "none", [cout(), cout()], {"category": "no"})["category"] == "no"


def test_check_fields_with_one_checker_missing_is_disputed_unless_the_code_decided():
    f = to.check_fields(cpayload(), None, [cout()], None)
    assert f == {"quote": "disputed", "year": "yes", "category": "disputed", "fact": None}


@pytest.mark.parametrize("fields, outcome", [
    ({"quote": "yes", "year": "yes", "category": "yes"}, "supported"),
    ({"quote": "disputed", "year": "no", "category": "yes"}, "unsupported"),
    ({"quote": "disputed", "year": "unverified", "category": "yes"}, "disputed"),
    ({"quote": "unverified", "year": "yes", "category": "yes"}, "unverified"),
])
def test_check_outcome_v2(fields, outcome):
    assert to.check_outcome_v2({**fields, "fact": None}) == outcome


def test_a_rejected_label_is_stored_unclear_and_a_disputed_one_disputed():
    assert "origin = 'unclear'" not in to.CHECK_UPDATE_SQL["supported"]
    for outcome in ("unsupported", "unverified"):
        assert "origin = 'unclear'" in to.CHECK_UPDATE_SQL[outcome]
    assert "origin = 'disputed'" in to.CHECK_UPDATE_SQL["disputed"]
    assert all("check_fields" in sql for sql in to.CHECK_UPDATE_SQL.values())


def test_a_pair_never_labelled_gets_a_not_reached_row_citing_its_last_attempt():
    keys = [to.key("ENSG1", "MONDO:1"), to.key("ENSG2", "MONDO:2"), to.key("ENSG3", "MONDO:3")]
    rows = to.unreached_rows(keys, labelled={keys[0]}, last_decision={keys[1]: 42})
    assert [(r[0], r[3], r[6], r[9], r[11], r[12]) for r in rows] == [
        ("ENSG2", "not_reached", "none", 42, "not_checked", "unclear"),
        ("ENSG3", "not_reached", "none", None, "not_checked", "unclear")]


def test_approval_fact_on_the_pairs_gene_from_the_dated_index():
    """The fact is about the pair's gene, never another target of the first drug (the fake index has no entity table,
    so an entity-level read raises): close at Lin 0.8 (the hub's validated_at_entry rule), related at 0.5 (the
    chart's b1 line), unrelated when the gene has an earlier approval but none related, none otherwise."""
    from types import SimpleNamespace as NS
    entry = pd.Timestamp("2008-01-01")
    close = {"MONDO:1": {"MONDO:1", "MONDO:1a"}}
    related = {"MONDO:1": {"MONDO:1", "MONDO:1a", "MONDO:9"}}
    ev = NS(first_approval={"ENSG1": pd.Timestamp("2001-01-01"), "ENSG3": pd.Timestamp("1995-01-01")},
            approved={"ENSG1": [("MONDO:9", pd.Timestamp("2001-01-01"))], "ENSG3": [("MONDO:1a", pd.Timestamp("1995-01-01"))]},
            nb=NS(terms=lambda m, thr: (close if thr >= 0.8 else related).get(m, set())))
    assert to.approval_fact(ev, "ENSG3", "MONDO:1", entry) == "close"  # approved for a subtype
    assert to.approval_fact(ev, "ENSG1", "MONDO:1", entry) == "related"  # MONDO:9 is related at 0.5, not close
    assert to.approval_fact(ev, "ENSG1", "MONDO:2", entry) == "unrelated"
    assert to.approval_fact(ev, "ENSG2", "MONDO:1", entry) == "none"
    assert to.approval_fact(ev, "ENSG1", "MONDO:1", pd.Timestamp("2000-06-01")) == "none"  # the approval came after entry
    programs = pd.DataFrame({"ensembl_id": ["ENSG1", "ENSG2"], "mondo_id": ["MONDO:1"] * 2, "moiety_id": [10, 20],
                             "entry": [entry, entry]})
    items = {"ENSG1|MONDO:1": cpayload(origin="earlier_drug_other_disease"),
             "ENSG2|MONDO:1": cpayload(origin="earlier_drug_other_disease", ensembl_id="ENSG2"),
             "ENSG1|MONDO:2": cpayload(origin="diseased_tissue", mondo_id="MONDO:2")}
    assert to.approval_facts(items, programs, ev) == {"ENSG1|MONDO:1": "related", "ENSG2|MONDO:1": "none",
                                                      "ENSG1|MONDO:2": None}


def test_fact_category_close_is_validated_at_entry_and_not_an_origin():
    assert to.FACT_CATEGORY == {"unrelated": "yes", "related": "yes", "close": "no", "none": "disputed"}


def test_dispute_sheet_round_trip(tmp_path):
    items = {"ENSG1|MONDO:1": cpayload(),
             "ENSG2|MONDO:1": cpayload(origin="earlier_drug_other_disease", ensembl_id="ENSG2"),
             "ENSG3|MONDO:1": cpayload(ensembl_id="ENSG3")}
    fields = {"ENSG1|MONDO:1": {"quote": "yes", "year": "disputed", "category": "disputed", "fact": None},
              "ENSG2|MONDO:1": {"quote": "yes", "year": "yes", "category": "disputed", "fact": "none"},
              "ENSG3|MONDO:1": {"quote": "no", "year": "disputed", "category": "yes", "fact": None}}  # unsupported anyway
    outputs = {"ENSG1|MONDO:1": [("claude-sonnet-5-5", cout(year="no", follows="no", note="s")),
                                 ("claude-opus-5-5", cout(note="o"))],
               "ENSG2|MONDO:1": [("claude-sonnet-5-5", cout(note="s2")), ("claude-opus-5-5", cout(note="o2"))]}
    programs = pd.DataFrame({"ensembl_id": ["ENSG1", "ENSG2"], "mondo_id": ["MONDO:1"] * 2,
                             "entity": ["drug a", "drug b"], "entry": [pd.Timestamp("2008-01-01")] * 2})
    sheet = to.dispute_sheet(items, fields, outputs, programs)
    assert list(zip(sheet.subject_key, sheet.field)) == [("ENSG1|MONDO:1", "year"), ("ENSG1|MONDO:1", "category"),
                                                         ("ENSG2|MONDO:1", "category")]  # ENSG3: a verdict changes nothing
    assert sheet.iloc[0].sonnet == "no" and sheet.iloc[0].sonnet_note == "s" and sheet.iloc[0].opus == "yes"
    assert sheet.iloc[1].sonnet == "no" and sheet.iloc[1].opus == "yes"  # the checkers' own words on the field
    assert sheet.iloc[2].fact == "none" and sheet.iloc[2].first_drug == "drug b"
    assert "another disease" in sheet.iloc[2].definition and sheet.iloc[2].entry == "2008-01-01"
    assert (sheet.verdict == "").all()
    path = tmp_path / "d.csv"
    to.write_sheet(path, sheet)
    assert to.read_disputes(path) == {}
    s = pd.read_csv(path, dtype=str).fillna("")
    s.loc[0, "verdict"], s.loc[0, "reader"] = "yes", "sg"
    s.to_csv(path, index=False)
    assert to.read_disputes(path) == {"ENSG1|MONDO:1": {"year": "yes"}}
    to.write_sheet(path, sheet)  # a rewrite keeps the verdicts already given
    s = pd.read_csv(path, dtype=str).fillna("")
    assert s.loc[0, "verdict"] == "yes" and s.loc[0, "reader"] == "sg" and s.loc[1, "verdict"] == ""
    s.loc[1, "verdict"] = "maybe"
    s.to_csv(path, index=False)
    with pytest.raises(SystemExit):
        to.read_disputes(path)


def test_label_row_is_the_label_as_read_in_the_stored_rows_shape():
    row = to.label_row("ENSG1", "MONDO:1", 77, good_label())
    stored = to.origin_rows([("ENSG1|MONDO:1", 77, good_label())])[0]
    assert (row["origin"], row["origin_year"], row["secondary_origin"], row["grade"], row["sources"],
            row["quote"]) == stored[3:9]
    assert row["ensembl_id"] == "ENSG1" and row["mondo_id"] == "MONDO:1" and row["llm_decision_id"] == 77
    assert row["parsed_output"]["source_years"] == [1999]
    assert to.label_row("ENSG1", "MONDO:1", 78, {**good_label(), "quote": "  "})["quote"] is None  # as stored
    # the check reads the label as read, whatever the row holds after an earlier check
    assert "d.parsed_output->>'grade' <> 'none'" in to.CHECK_ITEMS_SQL and "o.grade" not in to.CHECK_ITEMS_SQL


def test_check_update_params_restore_the_label_when_supported():
    p = cpayload()
    sup = to.check_update_params(p, "supported", 5, {"quote": "yes"}, "ENSG1", "MONDO:1")
    assert sup[:2] == ("supported", 5) and sup[3:9] == ("diseased_tissue", 2005, None, "stated", "q", ["PMID:1"])
    assert sup[-2:] == ("ENSG1", "MONDO:1") and to.CHECK_UPDATE_SQL["supported"].count("%s") == len(sup)
    assert to.check_update_params({**p, "quote": ""}, "supported", 5, {}, "E", "M")[7] is None
    dis = to.check_update_params(p, "disputed", 5, {"quote": "disputed"}, "ENSG1", "MONDO:1")
    assert dis[:2] == ("disputed", 5) and dis[-2:] == ("ENSG1", "MONDO:1") and len(dis) == 5
    assert to.CHECK_UPDATE_SQL["disputed"].count("%s") == len(dis)
    assert "origin = %s" in to.CHECK_UPDATE_SQL["supported"]


# --- research: one model reading settles a factual dispute ---

def rrow(subject_key="ENSG1|MONDO:1", field="quote", fact="", first_drug="", entry="", sonnet="no", opus="yes",
         **kw) -> dict:
    return {"subject_key": subject_key, "symbol": "ABC", "disease": "a disease", "cutoff_year": "2010",
            "origin": "diseased_tissue", "grade": "stated", "definition": "d", "quote": "q", "sources": "PMID:1",
            "field": field, "fact": fact, "first_drug": first_drug, "entry": entry, "sonnet": sonnet,
            "sonnet_note": "s", "opus": opus, "opus_note": "o", "verdict": "", "reader": "", "note": "", **kw}


def rout(found=None, dates=(), approvals=(), evidence_url=None, evidence="", note="n") -> dict:
    return {"found": found, "dates": list(dates), "approvals": list(approvals), "evidence_url": evidence_url,
            "evidence": evidence, "note": note}


def rdate(source, year, online_year=None, url="https://u") -> dict:
    return {"source": source, "year": year, "online_year": online_year, "basis": "issue", "evidence_url": url}


def rappr(drug="drug a", regulator="PMDA", date="1988", mondo="MONDO:7", url="https://u", indication="x") -> dict:
    return {"drug": drug, "regulator": regulator, "date": date, "indication": indication, "mondo_id": mondo,
            "evidence_url": url}


def test_research_rows_are_the_factual_rows_of_the_sheet():
    s = pd.DataFrame([rrow(field="quote"), rrow(field="year"),
                      rrow(subject_key="ENSG2|MONDO:1", field="category", fact="none"),
                      rrow(subject_key="ENSG3|MONDO:1", field="category"),
                      rrow(subject_key="ENSG4|MONDO:1", field="category", fact="related")])
    r = to.research_rows(s)
    assert list(zip(r.subject_key, r.field, r.question)) == [("ENSG1|MONDO:1", "quote", "quote"),
                                                             ("ENSG1|MONDO:1", "year", "year"),
                                                             ("ENSG2|MONDO:1", "category", "approval")]
    assert to.research_key("ENSG1|MONDO:1", "year") == "ENSG1|MONDO:1|year"
    assert to.split_key("ENSG1|MONDO:1|year") == ("ENSG1", "MONDO:1")  # the summary's token SQL still finds the pair


def test_research_payload_withholds_the_checkers_answers_and_carries_the_question():
    row = rrow(field="category", fact="none", first_drug="drug a", entry="2008-01-01", sonnet="no", opus="partly")
    p = to.research_payload(cpayload(origin="earlier_drug_other_disease"), {**row, "question": "approval"},
                            ["drug a", "drug b"])
    assert p["question"] == "approval" and p["first_drug"] == "drug a" and p["entry"] == "2008-01-01"
    assert p["gene_drugs"] == ["drug a", "drug b"] and p["records"] == cpayload()["records"]
    assert not any(k.startswith(("sonnet", "opus")) for k in p) and "label_decision_id" not in p
    q = to.research_payload(cpayload(), {**rrow(), "question": "quote"}, ["drug a"])
    assert q["question"] == "quote" and "gene_drugs" not in q and "first_drug" not in q
    text = to.render_research(p)
    assert text.startswith("QUESTION: approval") and "ENTRY DATE: 2008-01-01" in text and "drug a; drug b" in text
    assert "CITED RECORDS" in text and to.render_research(q).startswith("QUESTION: quote")


def test_validate_research_requires_the_answer_the_question_needs():
    quote = {**cpayload(), "question": "quote"}
    year = {**cpayload(sources=("PMID:1", "https://x")), "question": "year"}
    appr = {**cpayload(origin="earlier_drug_other_disease"), "question": "approval", "entry": "2008-01-01"}
    to.validate_research(quote, rout(found="yes", evidence_url="PMID:1"))
    to.validate_research(quote, rout(found="could_not_open"))
    with pytest.raises(ValueError):
        to.validate_research(quote, rout(found=None))
    with pytest.raises(ValueError):
        to.validate_research(quote, rout(found="yes"))  # found where?
    to.validate_research(year, rout(dates=[rdate("PMID:1", 2005), rdate("https://x", None)]))
    with pytest.raises(ValueError):
        to.validate_research(year, rout(dates=[rdate("PMID:1", 2005)]))  # one entry per cited source
    to.validate_research(appr, rout())
    to.validate_research(appr, rout(approvals=[rappr(date="1988-03-01"), rappr(date="1989-01"), rappr(mondo=None)]))
    for bad in (rappr(date="March 1988"), rappr(date="1989-1"), rappr(mondo="7"), rappr(url="")):
        with pytest.raises(ValueError):
            to.validate_research(appr, rout(approvals=[bad]))


def test_research_verdict_quote_is_the_finding_with_its_evidence():
    p = {**cpayload(), "question": "quote"}
    assert to.research_verdict(p, rout(found="yes", evidence_url="https://pmc/1", evidence="the words"), None, {}) == \
        ("yes", "https://pmc/1: the words; n")
    assert to.research_verdict(p, rout(found="no", note="it is in PMID:9, not cited"), None, {}) == \
        ("no", "it is in PMID:9, not cited")
    assert to.research_verdict(p, rout(found="could_not_open"), None, {})[0] == ""


def test_research_verdict_year_is_compared_in_code_on_the_issue_year():
    p = {**cpayload(sources=("PMID:1", "https://x")), "question": "year"}  # cutoff 2010
    v, note = to.research_verdict(p, rout(dates=[rdate("PMID:1", 2005), rdate("https://x", 2009)]), None, {})
    assert v == "yes" and note.startswith("PMID:1 2005; https://x 2009")
    assert to.research_verdict(p, rout(dates=[rdate("PMID:1", 2005), rdate("https://x", 2010)]), None, {})[0] == "no"
    assert to.research_verdict(p, rout(dates=[rdate("PMID:1", 2005), rdate("https://x", None)]), None, {})[0] == ""
    # an online-first date in an earlier year is recorded and flagged, never used for the verdict
    v, note = to.research_verdict(p, rout(dates=[rdate("PMID:1", 2005), rdate("https://x", 2010, 2009)]), None, {})
    assert v == "no" and "online 2009" in note and "online-first" in note


def test_research_verdict_approval_tiers_by_the_index_rule(monkeypatch):
    from types import SimpleNamespace
    close, related = frozenset({"MONDO:1", "MONDO:9"}), frozenset({"MONDO:1", "MONDO:9", "MONDO:5"})
    nb = SimpleNamespace(terms=lambda d, t: close if t == 0.8 else related)
    labels = {"MONDO:1": "a disease", "MONDO:5": "a cousin", "MONDO:9": "a subtype", "MONDO:7": "far away"}
    p = {**cpayload(origin="earlier_drug_other_disease"), "question": "approval", "entry": "2008-01-01",
         "first_drug": "drug a", "gene_drugs": ["drug a"]}
    v, note = to.research_verdict(p, rout(approvals=[rappr(mondo="MONDO:7")]), nb, labels)
    assert v == "yes" and note == "tier unrelated: drug a, PMDA 1988, far away (MONDO:7) https://u; n"
    assert to.research_verdict(p, rout(approvals=[rappr(mondo="MONDO:5")]), nb, labels)[0] == "yes"  # related counts
    assert to.research_verdict(p, rout(approvals=[rappr(mondo="MONDO:9"), rappr(mondo="MONDO:7")]), nb, labels)[1] \
        .startswith("tier close")
    # no approval found, or none before entry: the category does not follow
    assert to.research_verdict(p, rout(note="searched PMDA, EMA"), nb, labels) == \
        ("no", "no approval before 2008-01-01; searched PMDA, EMA")
    assert to.research_verdict(p, rout(approvals=[rappr(date="2009-05-01", mondo="MONDO:7")]), nb, labels)[0] == "no"
    assert to.research_verdict(p, rout(approvals=[rappr(date="2007-12-31", mondo="MONDO:7")]), nb, labels)[0] == "yes"
    # month precision (regulators often give no day): before or after the entry month decides, the entry month does not
    assert to.research_verdict(p, rout(approvals=[rappr(date="2007-12", mondo="MONDO:7")]), nb, labels)[0] == "yes"
    assert to.research_verdict(p, rout(approvals=[rappr(date="2008-02", mondo="MONDO:7")]), nb, labels)[0] == "no"
    assert to.research_verdict(p, rout(approvals=[rappr(date="2008-01", mondo="MONDO:7")]), nb, labels)[0] == ""
    # undecidable: an approval in the entry year without a day, or an indication the ontology does not know
    assert to.research_verdict(p, rout(approvals=[rappr(date="2008", mondo="MONDO:7")]), nb, labels)[0] == ""
    v, note = to.research_verdict(p, rout(approvals=[rappr(mondo="MONDO:3")]), nb, labels)
    assert v == "" and "MONDO:3" in note
    assert to.research_verdict(p, rout(approvals=[rappr(mondo=None)]), nb, labels)[0] == ""
    # an indication given without its id is placed by its exact MONDO label, case aside; no label, no placing
    assert to.research_verdict(p, rout(approvals=[rappr(mondo=None, indication="Far Away")]), nb, labels) == \
        ("yes", "tier unrelated: drug a, PMDA 1988, far away (MONDO:7, placed by its label) https://u; n")
    assert to.research_verdict(p, rout(approvals=[rappr(mondo=None, indication="far, far away")]), nb, labels)[0] == ""
    # ... unless a close approval is already documented, which settles the tier whatever the others are
    assert to.research_verdict(p, rout(approvals=[rappr(mondo="MONDO:9"), rappr(mondo=None)]), nb, labels)[0] == "no"


def test_research_task_is_opus_with_search_and_fetch_and_no_checker_answers():
    t = to.RESEARCH_TASK
    assert t.name == "target_origin_research" and t.prompt_version == "v2" and t.model == "claude-opus-5-5"
    assert [x["name"] for x in t.tools] == ["web_search", "web_fetch"] and t.validate is to.validate_research
    assert t.render is to.render_research and t.schema is to.RESEARCH_SCHEMA
    assert to.RESEARCH_METHOD == "target_origin_research@v1"
    assert "not shown their answers" in t.system and "Nothing you know from memory counts" in t.system


def test_research_sheet_is_a_filled_copy_of_the_disputes_rows(tmp_path):
    rows = to.research_rows(pd.DataFrame([rrow(field="quote"), rrow(field="year"),
                                          rrow(subject_key="ENSG2|MONDO:1", field="category", fact="none")]))
    verdicts = {"ENSG1|MONDO:1|quote": ("yes", "https://u: words", 11),
                "ENSG1|MONDO:1|year": ("", "https://x shows no date", 12)}  # ENSG2: no validated decision
    out = to.research_sheet(rows, verdicts)
    assert list(out.columns) == to.DISPUTE_COLUMNS + ["decision_id"]
    assert list(out.verdict) == ["yes", "", ""] and list(out.reader) == [to.RESEARCH_METHOD, to.RESEARCH_METHOD, ""]
    assert list(out.note) == ["https://u: words", "https://x shows no date", ""]
    assert list(out.decision_id) == ["11", "12", ""]
    path = tmp_path / "r.csv"
    out.to_csv(path, index=False)
    assert to.read_disputes(path) == {"ENSG1|MONDO:1": {"quote": "yes"}}  # check --disputes applies it as it is


def test_research_agreement_counts_each_checker_against_the_verdict():
    out = pd.DataFrame([rrow(field="quote", sonnet="no", opus="yes", verdict="yes"),
                        rrow(field="quote", sonnet="no", opus="yes", verdict="no"),
                        rrow(field="quote", sonnet="could_not_open", opus="yes", verdict=""),
                        rrow(field="year", sonnet="yes", opus="no", verdict="no"),
                        rrow(field="category", fact="none", sonnet="no", opus="partly", verdict="yes")])
    a = to.research_agreement(out).set_index("field")
    assert list(a.index) == ["quote", "year", "category"]
    assert a.loc["quote"].to_dict() == {"rows": 3, "decided": 2, "yes": 1, "no": 1, "agrees_sonnet": 1,
                                        "agrees_opus": 1, "agrees_neither": 0}
    assert a.loc["year"].agrees_sonnet == 0 and a.loc["year"].agrees_opus == 1
    assert a.loc["category"].agrees_opus == 1 and a.loc["category"].agrees_sonnet == 0  # partly counts as yes
