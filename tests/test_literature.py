import pandas as pd

from pipeline.literature import drug_names, entry_matches


def test_drug_names_keep_names_a_paper_would_use_and_drop_identifiers():
    names = drug_names(["alvocidib"], ["L86-8275", "TF2"], ["FLAVOPIRIDOL"],
                       ["Alvocidib [INN]", "146426-40-6", "CHEMBL428690", "45AD6X575G", "compound 3",
                        "2-(2-chlorophenyl)-5,7-dihydroxy-8-[(3S,4R)-3-hydroxy-1-methylpiperidin-4-yl]chromen-4-one",
                        "orb1685546", "Q4063441"], [])
    assert names == ["alvocidib", "L86-8275", "FLAVOPIRIDOL"]


def test_drug_names_are_distinct_ignoring_case_and_capped():
    many = [f"ABC-{i:04d}" for i in range(80)]
    names = drug_names(["Drugmab"], ["DRUGMAB"], many)
    assert names[0] == "Drugmab" and "DRUGMAB" not in names and len(names) == 50


QUALIFYING = pd.DataFrame([
    {"moiety_id": 1, "pmid": "10", "year": 2010, "kind": "animal_disease", "mondo_id": "MONDO:A1"},
    {"moiety_id": 1, "pmid": "11", "year": 2010, "kind": "animal_disease", "mondo_id": "MONDO:B"},
    {"moiety_id": 1, "pmid": "12", "year": 2016, "kind": "animal_healthy", "mondo_id": None},
    {"moiety_id": 1, "pmid": "13", "year": 2012, "kind": "human_engagement", "mondo_id": None},
])
RELATED = {"MONDO:A": {"MONDO:A", "MONDO:A1"}}


def matched(entries):
    out = entry_matches(pd.DataFrame(entries), QUALIFYING, lambda d: RELATED.get(d, {d}))
    return {(r["phase"], r["kind"]): r["pmids"] for r in out}


def test_an_animal_model_counts_only_for_a_related_disease():
    got = matched([{"moiety_id": 1, "mondo_id": "MONDO:A", "phase": 2, "cutoff_year": 2015}])
    assert got[(2, "animal_disease")] == ["10"]


def test_an_entry_counts_only_abstracts_published_by_its_cutoff():
    got = matched([{"moiety_id": 1, "mondo_id": "MONDO:A", "phase": 2, "cutoff_year": 2011}])
    assert got[(2, "animal_healthy")] == [] and got[(2, "human_engagement")] == []


def test_human_engagement_is_judged_for_phase_2_and_3_entries_only():
    got = matched([{"moiety_id": 1, "mondo_id": "MONDO:A", "phase": 1, "cutoff_year": 2018}])
    assert (1, "human_engagement") not in got and got[(1, "animal_healthy")] == ["12"]


def test_firecrawl_results_after_the_cutoff_are_dropped_and_ids_prefer_pmid():
    from pipeline.literature import firecrawl_ids
    results = [{"ids": {"pmid": ["123"], "doi": ["10.1/a"]}, "createdDate": "2010-05-01"},
               {"ids": {"pmcid": ["PMC9"]}, "createdDate": "2011-01-01"},
               {"ids": {"doi": ["10.1101/b"]}, "createdDate": "2009-02-02"},
               {"ids": {"pmid": ["456"]}, "createdDate": "2013-01-01"}]
    assert firecrawl_ids(results, 2011) == [("123", "10.1/a"), ("PMC:PMC9", None), ("DOI:10.1101/b", "10.1101/b")]


def test_a_europe_pmc_record_is_keyed_by_its_source_and_id():
    from pipeline.literature import epmc_record
    rec = epmc_record({"source": "PPR", "id": "PPR42", "title": "T", "abstractText": "A", "pubYear": "2016",
                       "doi": "10.1101/x"})
    assert rec == ("PPR:PPR42", "PPR", "T", "A", 2016, "10.1101/x")


def test_a_search_request_retries_then_reports_the_service_down(monkeypatch):
    import requests
    from pipeline import literature
    calls, logged = [], []

    class Resp:
        ok, status_code, text = False, 503, "Search service is temporarily unavailable"

    monkeypatch.setattr(requests, "request", lambda *a, **k: calls.append(1) or Resp())
    monkeypatch.setattr(literature.time, "sleep", lambda s: None)
    try:
        literature.request("POST", "https://example.org/search", logged.append)
    except literature.SourceDown as e:
        assert "503" in str(e)
    else:
        raise AssertionError("expected SourceDown")
    assert len(calls) == literature.RETRIES and len(logged) == literature.RETRIES
    assert all("HTTP 503" in line for line in logged)


def test_a_search_request_succeeds_after_a_transient_failure(monkeypatch):
    import requests
    from pipeline import literature
    responses = iter([type("R", (), {"ok": False, "status_code": 503, "text": ""})(),
                      type("R", (), {"ok": True, "status_code": 200, "text": "{}"})()])
    monkeypatch.setattr(requests, "request", lambda *a, **k: next(responses))
    monkeypatch.setattr(literature.time, "sleep", lambda s: None)
    assert literature.request("GET", "https://example.org/search", lambda m: None).ok


def test_a_rate_limited_firecrawl_call_raises_and_is_not_an_empty_result(monkeypatch):
    import subprocess
    from pipeline import literature
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(
        a, 1, "", "Error: Request failed with status code 429"))
    try:
        literature.firecrawl_cli(["search-papers", "q"])
    except literature.FirecrawlError as e:
        assert e.rate_limited and not e.out_of_credits
    else:
        raise AssertionError("a failed call must raise, not return no results")


def test_the_throttle_spaces_requests_from_separate_callers(tmp_path, monkeypatch):
    import time
    from pipeline import throttle
    monkeypatch.setattr(throttle, "DIR", str(tmp_path))
    start = time.time()
    for _ in range(5):
        throttle.wait("svc", 20)
    assert time.time() - start >= 4 / 20 - 0.01
