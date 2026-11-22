import pandas as pd

from pipeline import literature
from report import evidence_facts, evidence_lines, section3

COLUMNS = ["ensembl_id", "mondo_id", "disease_id", "moiety_id", "value", "value_num", "known_year", "detail", "source",
           "record_key"]


def facts_from(rows: dict[str, list[dict]]):
    """A stand-in for evidence_facts.facts serving the given rows of each fact kind."""
    return lambda key: pd.DataFrame([{c: r.get(c) for c in COLUMNS} for r in rows.get(key, [])], columns=COLUMNS)


def test_a_record_only_the_left_out_source_retrieved_is_dropped(monkeypatch):
    monkeypatch.setattr(evidence_facts, "facts", facts_from({"literature": [
        {"moiety_id": 7, "value": "animal_healthy", "known_year": 2010, "record_key": "7 111",
         "detail": {"hits": [[2012, "pubmed"], [2015, "firecrawl"]]}},
        {"moiety_id": 7, "value": "animal_healthy", "known_year": 2011, "record_key": "7 222",
         "detail": {"hits": [[2015, "firecrawl"]]}}]}))
    every = literature.qualifying()
    assert every.pmid.tolist() == ["111", "222"]
    assert every.search_cutoffs.tolist() == [[2012, 2015], [2015]]
    without = literature.qualifying(without="firecrawl")
    assert without.pmid.tolist() == ["111"]
    assert without.search_cutoffs.tolist() == [[2012]]


def test_a_gene_line_dependency_is_dated_by_its_earliest_screen(monkeypatch):
    monkeypatch.setattr(evidence_facts, "facts", facts_from({
        "screened_line": [{"mondo_id": "MONDO:1", "value": "ACH-1", "known_year": 2014}],
        "dependency": [{"ensembl_id": "ENSG1", "value": "ACH-1", "known_year": 2019, "record_key": "ACH-1 10"},
                       {"ensembl_id": "ENSG1", "value": "ACH-1", "known_year": 2016, "record_key": "ACH-1 11"}]}))
    lines, dep_year = evidence_lines.cell_screens()
    assert lines == {"ACH-1": ("MONDO:1", 2014)}
    assert dep_year == {("ENSG1", "ACH-1"): 2016}


def test_open_targets_tiers_index_by_gene_family_and_disease_with_undated_items_never_known(monkeypatch):
    section3.evidence_index.cache_clear()
    monkeypatch.setattr(evidence_facts, "facts", facts_from({"ot_tier": [
        {"ensembl_id": "ENSG1", "mondo_id": "MONDO:1", "value": "any", "known_year": 2005, "source": "eva"},
        {"ensembl_id": "ENSG1", "mondo_id": "MONDO:1", "value": "strong", "known_year": None, "source": "clingen"},
        {"ensembl_id": "ENSG1", "mondo_id": None, "value": "any", "known_year": 2001, "source": "gwas_credible_sets"}]}))
    idx, germline_first = section3.evidence_index()
    section3.evidence_index.cache_clear()
    years = dict(zip(section3.TIERS, idx["ENSG1"]["mendelian"]["MONDO:1"]))
    assert years["any"] == 2005 and years["strong"] == section3.NEVER and years["mid"] == section3.ABSENT
    assert germline_first == {"ENSG1": 2001}  # a trait with no MONDO term still dates the gene's first germline evidence
