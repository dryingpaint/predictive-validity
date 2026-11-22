from report.frame import essential_as_of

LISTS = {2019: {"ENSG_A", "ENSG_B"}, 2021: {"ENSG_B"}}


def test_no_list_before_the_first_release():
    assert not essential_as_of(LISTS, ["ENSG_A"], 2018)


def test_latest_list_at_or_before_the_year_decides():
    assert essential_as_of(LISTS, ["ENSG_A"], 2020)
    assert not essential_as_of(LISTS, ["ENSG_A"], 2021)  # dropped from the 2021 list
    assert essential_as_of(LISTS, ["ENSG_X", "ENSG_B"], 2024)
