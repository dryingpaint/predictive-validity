"""Values written to the classifications sheet: dates as ISO text, missing values empty, numpy scalars plain."""
from datetime import date

import numpy as np
import pandas as pd

from report.sheet import cell, words


def test_dates_become_iso_text():
    assert cell(date(2026, 11, 2)) == "2026-11-02"
    assert cell(pd.Timestamp("2021-08-17 00:00")) == "2021-08-17"


def test_missing_values_become_empty():
    assert cell(None) == "" and cell(float("nan")) == "" and cell(pd.NaT) == ""


def test_numpy_scalars_become_plain_values():
    assert cell(np.int64(3)) == 3 and type(cell(np.int64(3))) is int
    assert cell("text") == "text"


def test_category_codes_become_words():
    assert words("B3_regulatory_surrogate") == "B3 regulatory surrogate"
    assert words("PHASE1, PHASE2") == "Phase 1, Phase 2"
    assert words("car_t") == "CAR-T" and words("mrna") == "mRNA" and words("covid19") == "COVID-19"
    assert words("sponsor_decision") == "Sponsor decision"
