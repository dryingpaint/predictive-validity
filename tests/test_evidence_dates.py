"""Evidence dating: source keys, yearly association series, trial start bounds."""
from __future__ import annotations

import math
from datetime import date

import pytest

from pipeline import ctgov, llm


def scalar(sql: str, *params):
    with llm.connect() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


@pytest.mark.db
def test_evidence_key_per_source():
    key = "SELECT preclin.ot_evidence_key(%s, %s::jsonb)"
    assert scalar(key, "eva", '{"studyId": "RCV000000012"}') == ("RCV000000012",)
    assert scalar(key, "impc", '{"biologicalModelAllelicComposition": "Abca4<tm1a(EUCOMM)Wtsi>/Abca4<+>"}') \
        == ("Abca4<tm1a(EUCOMM)Wtsi>",)
    assert scalar(key, "impc", '{"biologicalModelAllelicComposition": "Idua<em1(IMPC)Hmgu> hom early"}') \
        == ("Idua<em1(IMPC)Hmgu>",)
    assert scalar(key, "impc", '{"biologicalModelAllelicComposition": "Foxc1<tm1Blh>/Foxc1<+>"}') == (None,)
    assert scalar(key, "intogen", '{"cohortShortName": "HARTWIG_WGS_BLCA_2023"}') == ("HARTWIG_WGS_BLCA_2023",)
    assert scalar(key, "reactome", '{"reactionName": "x"}') == (None,)


@pytest.mark.db
def test_series_is_the_harmonic_sum_of_items_dated_by_each_year():
    years, scores = scalar("SELECT * FROM preclin.harmonic_series(%s, %s::float8[])", [2010, 2012, 2012], [0.5, 0.3, 0.9])
    norm = sum(1 / i ** 2 for i in range(1, 1001))
    assert years == [2010, 2012]
    assert math.isclose(scores[0], 0.5 / norm, rel_tol=1e-6)
    assert math.isclose(scores[1], (0.9 + 0.5 / 4 + 0.3 / 9) / norm, rel_tol=1e-6)


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
