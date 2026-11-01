import math

from report.frame import essential_as_of
from report.render import band_label

LISTS = {2019: {"ENSG_A", "ENSG_B"}, 2021: {"ENSG_B"}}


def test_no_list_before_the_first_release():
    assert not essential_as_of(LISTS, ["ENSG_A"], 2018)


def test_latest_list_at_or_before_the_year_decides():
    assert essential_as_of(LISTS, ["ENSG_A"], 2020)
    assert not essential_as_of(LISTS, ["ENSG_A"], 2021)  # dropped from the 2021 list
    assert essential_as_of(LISTS, ["ENSG_X", "ENSG_B"], 2024)


def test_band_labels_name_the_score_range():
    assert band_label("none", 0.0, 0.0) == "0 (no genetic support)"
    assert band_label("low", 0.0, 0.61) == "up to 0.61 (lowest third)"
    assert band_label("middle", 0.61, 0.88) == "0.61–0.88 (middle third)"
    assert band_label("high", 0.88, math.inf) == "above 0.88 (highest third)"
