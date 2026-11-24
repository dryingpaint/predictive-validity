import pytest

from pipeline.opentargets import signal

TOTAL = {2005: 1000, 2006: 1000, 2007: 1000}
DRUG = {2005: 100, 2006: 100, 2007: 100}
REACTION = {2005: 5, 2006: 5, 2007: 5}


def test_a_reaction_becomes_a_signal_the_first_year_its_cumulative_reports_meet_the_criterion():
    # 2005: one report, too few. 2006: five of the drug's 200 reports against five of the other 1,800 (PRR 9).
    year, reports, prr, chi2 = signal({2005: 1, 2006: 4}, DRUG, REACTION, TOTAL, 2007)
    assert (year, reports) == (2006, 5)
    assert prr == pytest.approx(9.0) and chi2 == pytest.approx(13.68, abs=0.01)


def test_reports_received_after_the_last_counted_year_do_not_count():
    assert signal({2005: 1, 2006: 4}, DRUG, REACTION, TOTAL, 2005)[0] is None


def test_a_reaction_reported_no_more_often_than_for_other_drugs_is_no_signal():
    # one in ten of the reaction's reports names the drug, as one in ten of all reports does: PRR 1
    year, reports, prr, _ = signal({2005: 50, 2006: 50, 2007: 50}, DRUG, {y: 500 for y in TOTAL}, TOTAL, 2007)
    assert year is None and reports == 150 and prr == pytest.approx(1.0)


def test_a_pair_with_no_reports_is_no_signal():
    assert signal({}, DRUG, REACTION, TOTAL, 2007) == (None, 0, None, None)
