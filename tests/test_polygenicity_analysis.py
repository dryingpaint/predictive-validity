"""Polygenicity (#147): the unit, the tertile rule, the pre-comment check (report.polygenicity, first half)."""
import numpy as np
import pandas as pd
import pytest

from report.polygenicity import cutpoints, tertile, unit


def test_cutpoints_are_the_33_and_67_percentiles():
    s = pd.Series(np.arange(1.0, 10.0))     # 1..9
    assert cutpoints(s) == (np.percentile(s, 100 / 3), np.percentile(s, 200 / 3))


def test_tertile_labels_and_none_for_unscored():
    s = pd.Series([1.0, 5.0, 9.0, np.nan])
    assert list(tertile(s, (3.0, 7.0))) == ["bottom", "middle", "top", "none"]
    assert list(tertile(pd.Series([3.0, 7.0]), (3.0, 7.0))) == ["bottom", "middle"]   # a cut value goes down


def test_unit_flags_a_disease_missing_from_the_profile():   # Review Focus 5
    d = pd.DataFrame({"mondo_id": ["M1", "M1", "M2", "M3", "M4"], "phase": [2, 3, 2, 2, 2],
                      "bio_area": ["a", "a", "a", "oncology", "a"], "us_site": [True, True, True, True, False]})
    prof = pd.DataFrame({"mondo_id": ["M1"], "score": [2.0], "ldsc_status": ["ok"]})
    u = unit(d, prof)
    assert list(u.mondo_id) == ["M1", "M2"] and list(u.entries) == [1, 1]
    assert list(u.ldsc_status) == ["ok", "not_profiled"] and list(u.scored) == [True, False]


def test_tests_table_has_one_row_per_hypothesis(tmp_path, monkeypatch):
    from report.render import polygenicity_tests_table
    t = pd.DataFrame({"family": ["primary"] * 3, "test": ["P1", "P2", "P3"], "rr": [1.2, 0.8, 0.9], "lo": [1, .6, .5],
                      "hi": [1.5, 1, 1.4], "p": [.04, .08, .6], "p_one_sided": [.02, .04, .3], "p_holm": [.06, .08, .3],
                      "reading": ["same direction, not confirmed"] * 3, "exposed_entries": [100] * 3,
                      "exposed_events": [20] * 3, "reference_entries": [100] * 3, "reference_events": [10] * 3})
    (tmp_path / "polygenicity").mkdir()
    t.to_csv(tmp_path / "polygenicity" / "tests.csv", index=False)
    monkeypatch.setattr("report.render.OUT", str(tmp_path))
    out = polygenicity_tests_table()
    assert out.count("\n| P") == 3 and "1.20 (1.00–1.50)" in out


def test_area_and_no_score_tables_read_their_csvs(tmp_path, monkeypatch):
    from report.render import polygenicity_area_table, polygenicity_no_score_table
    (tmp_path / "polygenicity").mkdir()
    pd.DataFrame({"tertile": ["top", "top", "bottom"], "bio_area": ["a", "b", "a"], "entries": [5, 6, 7],
                  "diseases": [1, 2, 3]}).to_csv(tmp_path / "polygenicity" / "area.csv", index=False)
    pd.DataFrame({"ldsc_status": ["no_study", "low_z"], "diseases": [10, 2], "entries": [40, 9]}) \
        .to_csv(tmp_path / "polygenicity" / "no_score.csv", index=False)
    monkeypatch.setattr("report.render.OUT", str(tmp_path))
    area = polygenicity_area_table()
    assert "| a | 1 / 5 | 3 / 7 |" in area and "| b | 2 / 6 | 0 / 0 |" in area   # one row per area, a column per tertile
    ns = polygenicity_no_score_table()
    assert "| No GWAS study of the disease or a subtype | 10 | 40 |" in ns and ns.index("No GWAS") < ns.index("z = 4")


def test_membership_carries_the_study_heritability_prevalence_and_loci():
    from report.polygenicity import membership
    u = pd.DataFrame({"mondo_id": ["M1", "M2"], "label": ["a", "b"], "bio_area": ["x", "x"], "entries": [3, 4],
                      "ldsc_status": ["ok", "ok"], "gcst": ["GCST1", "GCST2"], "trait_level": ["exact", "exact"],
                      "k_source": ["gbd", "panukb"], "score": [10.0, 40.0], "concentration": [0.2, 0.5],
                      "mendelian_form": [True, False], "h2_obs": [0.1, 0.2], "h2_z": [5.0, 6.0], "k": [0.01, 0.02],
                      "h2_liab": [0.3, 0.4], "loci": [3, 16], "n_cases": [1000, 2000], "n_controls": [5000, 6000]})
    m = membership(u, (20.0, 30.0))
    assert list(m.tertile) == ["bottom", "top"] and "conc_tertile" not in m.columns
    assert {"h2_obs", "h2_z", "k", "h2_liab", "loci", "n_cases", "n_controls"} <= set(m.columns)


def test_within_area_variance_share():   # Melissa's pre-join check 1
    from report.polygenicity import within_area_variance
    u = pd.DataFrame({"mondo_id": list("abcdef"), "bio_area": ["x", "x", "x", "y", "y", "y"], "scored": True,
                      "log10_score": [1.0, 2.0, 3.0, 1.0, 2.0, 3.0]})
    assert within_area_variance(u)["share"] == pytest.approx(1.0)        # equal area means: every bit of it within
    assert within_area_variance(u.assign(log10_score=[1.0, 1.0, 1.0, 3.0, 3.0, 3.0]))["share"] == pytest.approx(0.0)
    r = within_area_variance(u.assign(log10_score=[1.0, 2.0, 3.0, 2.0, 3.0, 4.0]))
    assert 0 < r["share"] < 1 and r["diseases"] == 6 and r["areas"] == 2
    assert within_area_variance(u.assign(scored=False))["diseases"] == 0


def test_sensitivities_table_shows_the_negative_control_with_its_two_sided_p(tmp_path, monkeypatch):
    from report.render import polygenicity_sensitivities_table
    (tmp_path / "polygenicity").mkdir()
    pd.DataFrame({"family": ["gwas_size", "negative_control", "k_corrected", "post_hoc_residual"], "test": ["P1", "P1", "P1", "P2"],
                  "rr": [1.2, 1.05, 1.1, 0.9], "lo": [1.0, 0.8, 0.9, 0.7], "hi": [1.5, 1.4, 1.3, 1.2], "p": [0.04, 0.3, 0.2, 0.5],
                  "p_one_sided": [0.02, np.nan, 0.1, np.nan], "p_holm": [0.06, np.nan, 0.3, np.nan],
                  "reading": ["same direction, not confirmed", "no association", "same direction, not confirmed", "no association"],
                  "exposed_entries": [100, 90, 100, 100], "exposed_events": [20, 9, 20, 20], "reference_entries": [100, 95, 100, 100],
                  "reference_events": [10, 9, 10, 10]}).to_csv(tmp_path / "polygenicity" / "sensitivities.csv", index=False)
    monkeypatch.setattr("report.render.OUT", str(tmp_path))
    out = polygenicity_sensitivities_table()
    assert "Negative control" in out and "| 0.300 |" in out and "no association" in out
    assert "concentration" not in out.lower() and "continuous" not in out.lower()
    assert "p (one-sided; two-sided where the row says so)" in out   # review of 2026-11-27: the two-sided rows sat under "p (one-sided)"
    assert "Corrected prevalence code (K)" in out and "Post hoc" in out and out.index("Corrected") < out.index("Post hoc")


def test_no_score_reasons_name_every_status_the_profile_can_hold():
    """Review of 2026-11-27: `no_effect` (a chosen study whose file holds no usable effect) had no plain label."""
    from report.render import NO_SCORE_REASONS
    statuses = {"no_study", "no_sumstats", "not_european", "no_case_control", "no_effect", "run_failed", "low_z",
                "out_of_bounds", "no_k", "zero_loci", "targeted_array"}
    assert statuses <= set(NO_SCORE_REASONS)


def test_main_stands_aside_when_the_latest_programme_build_is_not_the_registered_one(tmp_path, monkeypatch):
    """Review of 2026-11-27: a routine programme rebuild must not halt the whole report at this step. The step stands
    aside (the runner carries its cached outputs forward) instead of reading the unit off another build or raising."""
    import report.polygenicity as pg
    from report import frame
    monkeypatch.setattr(pg, "OUT", str(tmp_path))
    monkeypatch.setattr(pg, "BUILD_ID", "registered")
    monkeypatch.setattr(pg, "current_build", lambda: {"build_id": "another", "built_at": "", "snapshot": ""})
    monkeypatch.setattr(pg, "build", lambda: pytest.fail("the step must not read the unit off another build"))
    with pytest.raises(frame.StandAside):
        pg.main()


def test_profile_numeric_columns_come_back_as_floats_not_decimals():
    """psycopg2 returns NUMERIC as decimal.Decimal; the profile's arithmetic (variance share, tertiles, the power
    simulation) needs float64, with NULL as NaN; text columns are untouched."""
    from decimal import Decimal
    from report.polygenicity import floats
    p = pd.DataFrame({"mondo_id": ["M1", "M2"], "score": [Decimal("1.5"), None], "label": ["a", None],
                      "k_via_parent": [True, None]})
    f = floats(p)
    assert f.score.dtype == np.float64 and f.score[0] == 1.5 and np.isnan(f.score[1])
    assert f.label.equals(p.label) and f.mondo_id.tolist() == ["M1", "M2"]   # untouched, however pandas holds None
    assert f.k_via_parent.equals(p.k_via_parent)


def test_pinned_unit_refuses_a_different_build_or_a_moved_disease():
    """After the gate, a report run must sit on the registered unit: the same programme build, no disease the profile
    lacks, and the same tertile for every disease as the committed membership file."""
    from report.polygenicity import pinned_unit
    m = pd.DataFrame({"mondo_id": ["a", "b"], "tertile": ["top", "bottom"]})
    pinned_unit({"build_id": "x", "not_profiled": []}, "x", m, m)
    with pytest.raises(RuntimeError):
        pinned_unit({"build_id": "y", "not_profiled": []}, "x", m, m)
    with pytest.raises(RuntimeError):
        pinned_unit({"build_id": "x", "not_profiled": ["c"]}, "x", m, m)
    with pytest.raises(RuntimeError):
        pinned_unit({"build_id": "x", "not_profiled": []}, "x", m.assign(tertile=["top", "middle"]), m)


def test_descriptives_table_lists_each_check_with_its_readings(tmp_path, monkeypatch):
    import json
    from report.render import polygenicity_descriptives_table
    fit = {"rr": 1.2, "lo": 1.0, "hi": 1.5, "reading": "same direction, not confirmed"}
    desc = {"z_at_least_2": {"diseases": 10, "tests": {"P1": fit, "P2": fit, "P3": {"reading": "not estimable"}}},
            "gbd_k_only": {"diseases": 4, "tests": {}}, "catalog_loci": {"diseases": 9, "tests": {"P1": fit, "P2": fit, "P3": fit}},
            "gwas_genes": {"diseases": 12, "tests": {"P1": fit, "P2": fit, "P3": fit}}}
    (tmp_path / "polygenicity").mkdir()
    (tmp_path / "polygenicity" / "numbers.json").write_text(json.dumps({"descriptives": desc}))
    monkeypatch.setattr("report.render.OUT", str(tmp_path))
    out = polygenicity_descriptives_table()
    assert out.count("\n| ") == 5 and "1.20 (1.00–1.50)" in out and "not estimable" in out and "not run" in out


def test_tertiles_figure_ratio_axis_uses_the_fold_tick_convention(tmp_path, monkeypatch):
    import json
    import matplotlib
    matplotlib.use("Agg")
    from report import figures
    out = tmp_path / "polygenicity"
    out.mkdir()
    pd.DataFrame({"tertile": ["top", "middle", "bottom", "none"], "entries": [673, 375, 286, 1368],
                  "not_causal": [59, 54, 31, 158], "phase2_entries": [483, 269, 208, 988],
                  "s4": [89, 42, 33, 193]}).to_csv(out / "tertiles.csv", index=False)
    (out / "numbers.json").write_text(json.dumps({"tests": {"P3": {
        "cells": {"top_genetics": {"targets": 33}, "bottom_genetics": {"targets": 12}},
        "genetics_within": {"top": {"rr": 1.57, "lo": 0.86, "hi": 2.88, "n_cohort": 483},
                            "bottom": {"estimable": False}}}}}))
    captured = {}
    monkeypatch.setattr(figures, "OUT", str(tmp_path))
    monkeypatch.setattr(figures, "save", lambda fig, name: captured.setdefault(name, fig))
    figures.polygenicity_tertiles()
    ax = captured["polygenicity_tertiles"].axes[2]
    assert [t.get_text() for t in ax.get_xticklabels()] == ["0.5×", "1×", "2×", "4×"]
    assert ax.xaxis.get_minor_locator().__class__.__name__ == "NullLocator"
    for a in captured["polygenicity_tertiles"].axes:   # the house style(ax): no left spine, no tick marks
        assert not a.spines["left"].get_visible()
        assert a.xaxis.get_major_ticks()[0].tick1line.get_markersize() == 0


def test_k_rule_frame_renames_the_long_table_columns_for_one_rule():
    """preclin.disease_polygenicity_k (migration 181) holds one row per disease per rule; the report reads one rule's
    rows as columns suffixed with the rule, to sit beside the profile's registered columns."""
    from report.polygenicity import k_rule
    rows = pd.DataFrame({"mondo_id": ["M1", "M2"], "k": [0.01, None], "k_source": ["panukb", "none"], "k_code": ["401", None],
                         "k_via_parent": [False, False], "h2_liab": [0.1, None], "score": [50.0, None], "ldsc_status": ["ok", "no_k"],
                         "category": [False, True]})
    f = k_rule("v3", rows)
    assert list(f.columns) == ["mondo_id", "k_v3", "k_v3_source", "k_v3_code", "k_v3_via_parent", "h2_liab_v3", "score_v3",
                               "ldsc_status_v3", "category_v3"]
    assert f.score_v3.tolist()[0] == 50.0 and f.category_v3.tolist() == [False, True]
