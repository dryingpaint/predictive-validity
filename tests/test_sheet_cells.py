"""Values written to the classifications sheet: dates as ISO text, missing values empty, numpy scalars plain."""
from datetime import date

import numpy as np
import pandas as pd

from report.sheet import cell


def test_dates_become_iso_text():
    assert cell(date(2026, 11, 2)) == "2026-11-02"
    assert cell(pd.Timestamp("2021-08-17 00:00")) == "2021-08-17"


def test_missing_values_become_empty():
    assert cell(None) == "" and cell(float("nan")) == "" and cell(pd.NaT) == ""


def test_numpy_scalars_become_plain_values():
    assert cell(np.int64(3)) == 3 and type(cell(np.int64(3))) is int
    assert cell("text") == "text"
