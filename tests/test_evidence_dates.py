"""Evidence dating: source keys, rows dated by known years, yearly association series, trial start bounds."""
from __future__ import annotations

import math
from datetime import date

from pipeline import ctgov, opentargets


def ot_row(**fields) -> dict:
    return {"id": "e1", "targetId": "ENSG1", "diseaseId": "MONDO_0000001", "score": 0.5, **fields}


def test_evidence_key_per_source():
    assert opentargets.evidence_key(ot_row(datasourceId="eva", studyId="RCV000000012")) == "RCV000000012"
    assert opentargets.evidence_key(ot_row(datasourceId="impc",
                                           biologicalModelAllelicComposition="Abca4<tm1a(EUCOMM)Wtsi>/Abca4<+>")) \
        == "Abca4<tm1a(EUCOMM)Wtsi>"
    assert opentargets.evidence_key(ot_row(datasourceId="impc",
                                           biologicalModelAllelicComposition="Foxc1<tm1Blh>/Foxc1<+>")) is None
    assert opentargets.evidence_key(ot_row(datasourceId="intogen", cohortShortName="HARTWIG_WGS_BLCA_2023")) \
        == "HARTWIG_WGS_BLCA_2023"
    assert opentargets.evidence_key(ot_row(datasourceId="reactome")) is None


def test_known_year_replaces_the_rows_own_date():
    known = {("eva", "RCV000000012"): (2013, "clinvar_accession")}
    dated = opentargets.evidence_row(ot_row(datasourceId="eva", studyId="RCV000000012", evidenceDate="2024-12-17"),
                                     1, known)
    own = opentargets.evidence_row(ot_row(datasourceId="eva", studyId="RCV000000099", evidenceDate="2024-12-17"),
                                   1, known)
    undated = opentargets.evidence_row(ot_row(datasourceId="reactome"), 1, known)
    assert (dated[6], dated[-1]) == (2013, "clinvar_accession")
    assert (own[6], own[-1]) == (2024, "open_targets")
    assert (undated[6], undated[-1]) == (None, None)


def test_series_is_the_harmonic_sum_of_items_dated_by_each_year():
    rows = [("a", "T", "D", "gwas", 0.5, None, 2010), ("b", "T", "D", "gwas", 0.9, None, 2012),
            ("c", "T", "D", "gwas", 0.3, None, 2012), ("d", "T", "D", "gwas", 0.4, None, None)]
    [(target, disease, source, years, scores, first)] = opentargets.series(rows)
    norm = math.pi ** 2 / 6
    assert (target, disease, source, years, first) == ("T", "D", "gwas", [2010, 2012], 2010)
    assert math.isclose(scores[0], 0.5 / norm)
    assert math.isclose(scores[1], (0.9 + 0.5 / 4 + 0.3 / 9) / norm)


def study(status: str, **dates) -> dict:
    structs = {k: {"date": v} for k, v in dates.items() if k.endswith("Struct")}
    plain = {k: v for k, v in dates.items() if not k.endswith("Struct")}
    return {"protocolSection": {"identificationModule": {"nctId": "NCT00000001"},
                                "statusModule": {"overallStatus": status, **structs, **plain}}}


def test_started_study_without_start_date_gets_upper_bound():
    row = ctgov.row(study("COMPLETED", studyFirstSubmitDate="1999-11-03",
                          completionDateStruct="2001-06"), 1)
    start, start_type = row[ctgov.COLUMNS.index("start_date")], row[ctgov.COLUMNS.index("start_date_type")]
    assert (start, start_type) == (date(1999, 11, 3), "UPPER_BOUND")


def test_unstarted_study_without_start_date_stays_undated():
    row = ctgov.row(study("WITHDRAWN", studyFirstSubmitDate="1999-11-03"), 1)
    assert row[ctgov.COLUMNS.index("start_date")] is None
