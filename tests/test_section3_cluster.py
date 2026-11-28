"""section3: the cluster column of the modified Poisson fits is an argument (default the primary-target set)."""
import numpy as np
import pandas as pd

from report.section3 import adjusted, estimate, poisson


def frame():
    rng = np.random.default_rng(0)
    n = 400
    return pd.DataFrame({"x": rng.integers(0, 2, n).astype(float), "y": rng.integers(0, 2, n).astype(float),
                         "target": rng.integers(0, 40, n).astype(str), "mondo_id": rng.integers(0, 8, n).astype(str),
                         "bio_area": "a", "modality": "m", "era": "e", "novel": 0.0, "precedent": 0.0})


def test_cluster_column_changes_standard_errors_not_coefficients():
    d = frame()
    a, b = poisson(d, "y", ["x"]), poisson(d, "y", ["x"], cluster="mondo_id")
    assert abs(a.params["x"] - b.params["x"]) < 1e-9 and a.bse["x"] != b.bse["x"]


def test_estimate_and_adjusted_take_the_cluster():
    d = frame()
    e = estimate(d, "y", "x", cluster="mondo_id")
    assert e["n_targets"] == d[d.x > 0].target.nunique() and "rr" in e
    assert adjusted(d, "y", ["x"], cluster="mondo_id")["rr"] == e["rr"]
