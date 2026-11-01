import math

import pandas as pd

from report.frame import assays_as_of

COLUMNS = ["target_chembl_id", "symbols", "target_type", "standard_type", "pchembl", "functional", "cell_based", "year"]
ASSAYS = pd.DataFrame([
    ("T_HCRTR2", ["HCRTR2"], "SINGLE PROTEIN", "Ki", 7.0, False, False, 2010),
    ("T_HCRTR2", ["HCRTR2"], "SINGLE PROTEIN", "Ki", 9.0, False, False, 2012),
    ("T_HCRTR2", ["HCRTR2"], "SINGLE PROTEIN", "Ki", 8.0, False, False, 2012),
    ("T_HCRTR2", ["HCRTR2"], "SINGLE PROTEIN", "EC50", 7.5, True, True, 2014),
    ("T_HCRTR1", ["HCRTR1"], "SINGLE PROTEIN", "Ki", 5.5, False, False, 2012),
    ("T_FAMILY", ["HCRTR1", "HCRTR2"], "PROTEIN FAMILY", "Ki", 6.0, False, False, 2012),
], columns=COLUMNS)


def test_nothing_known_before_the_first_paper():
    r = assays_as_of(ASSAYS, {"HCRTR2"}, 2009)
    assert not r["measured"] and math.isnan(r["best"]) and not r["potent"] and not r["selective"]


def test_one_paper_gives_potency_but_no_selectivity_without_an_off_target():
    r = assays_as_of(ASSAYS, {"HCRTR2"}, 2010)
    assert r["measured"] and r["best"] == 7.0 and r["potent"] and not r["very_potent"]
    assert math.isnan(r["margin"]) and not r["selective"]


def test_potency_is_the_median_per_target_and_type_and_selectivity_the_margin_to_single_protein_off_targets():
    r = assays_as_of(ASSAYS, {"HCRTR2"}, 2012)
    assert r["best"] == 8.0  # median of Ki 7, 9, 8; the family holding HCRTR2 counts as primary
    assert r["margin"] == 2.5 and r["selective"]  # against HCRTR1 at 5.5
    assert not r["cell_functional"]


def test_cell_based_functional_potency_counts_once_published():
    assert assays_as_of(ASSAYS, {"HCRTR2"}, 2014)["cell_functional"]
