"""Polygenicity (#147): P1-P3, one-sided Holm, sensitivities and descriptives (report.polygenicity_tests) on
synthetic entries. Nothing here reads the database."""
import numpy as np
import pandas as pd

from report.polygenicity_tests import SIDES, cohort, one_sided, p3, registered, results_table, sensitivities


def synthetic(n=600, seed=0):
    rng = np.random.default_rng(seed)
    t = rng.choice(["bottom", "middle", "top"], n)
    g = rng.integers(0, 2, n)
    s4 = (rng.random(n) < np.where(t == "top", 0.15, 0.3) + 0.1 * g).astype(float)
    mode = (rng.random(n) < np.where(t == "top", 0.3, 0.15)).astype(float)
    score = np.where(t == "top", 3.0, np.where(t == "middle", 2.0, 1.0)) + rng.random(n) * 0.5
    return pd.DataFrame({"tertile": t, "genetics": g.astype(float), "s4": s4, "mode_not_causal": mode,
                         "phase": rng.choice([2, 3], n), "mondo_id": rng.integers(0, 60, n).astype(str),
                         "target": rng.integers(0, 120, n).astype(str), "has_target_disease": True,
                         "bio_area": rng.choice(["a", "b"], n), "modality": "m", "era": rng.choice(["e1", "e2"], n),
                         "novel": 0.0, "precedent": 0.0, "us_site": True, "log10_score": score,
                         "conc_tertile": rng.choice(["bottom", "middle", "top"], n),
                         "mendelian_form": rng.integers(0, 2, n).astype(bool), "log10_n_eff": 4 + rng.random(n),
                         "scored": True, "stop_no_benefit": mode,
                         "stop_unrelated": (rng.random(n) < 0.1).astype(float), "stop_safety": (rng.random(n) < 0.05).astype(float),
                         "tertile_k": rng.choice(["bottom", "middle", "top", "none"], n),
                         "tertile_v3": rng.choice(["bottom", "middle", "top", "none"], n),
                         "tertile_resid": rng.choice(["bottom", "middle", "top"], n)})


def test_cohort_keeps_the_two_levels_with_a_resolved_target_and_the_right_phases():
    d = synthetic()
    c = cohort(d, "s4")
    assert set(c.tertile) == {"top", "bottom"} and c.has_target_disease.all() and set(c.phase) == {2}
    assert set(cohort(d, "mode_not_causal").phase) == {2, 3}
    assert list(c.top.unique()) in ([0.0, 1.0], [1.0, 0.0])


def test_one_sided_halves_p_on_the_registered_side():
    assert one_sided({"rr": 1.5, "p": 0.04}, 1)["p_one_sided"] == 0.02
    assert one_sided({"rr": 0.8, "p": 0.04}, 1)["p_one_sided"] == 0.98
    assert one_sided({}, 1) == {}


def test_registered_runs_three_tests_with_holm_and_readings():
    r = registered(synthetic())
    assert set(r) == set(SIDES) == {"P1", "P2", "P3"}
    assert all("p_holm" in r[k] and "reading" in r[k] for k in r)
    assert r["P1"]["rr"] > 1 and r["P2"]["rr"] < 1
    assert r["P1"]["reading"] in ("confirmed", "same direction, not confirmed")


def test_p3_is_not_estimable_when_a_cell_has_no_event():
    d = synthetic()
    d.loc[(d.tertile == "top") & (d.genetics == 1), "s4"] = 0.0
    r = p3(d)
    assert "rr" not in r and r["estimable"] is False and r["cells"]["top_genetics"]["events"] == 0


def test_sensitivities_have_the_three_amended_families_and_the_corrected_k():   # 2026-11-24 decision; corrected K 2026-11-26
    s = sensitivities(synthetic())
    assert set(s) == {"gwas_size", "mendelian_form", "negative_control", "k_corrected", "k_v3"}
    assert set(s["mendelian_form"]) == {"P1", "P2", "P3"} and "p_holm" in s["gwas_size"]["P1"]
    assert set(s["negative_control"]) == {"P1"}
    assert set(s["k_corrected"]) == {"P1", "P2", "P3"} and "p_holm" in s["k_corrected"]["P1"]   # Holm within, on tertile_k
    assert set(s["k_v3"]) == {"P1", "P2", "P3"} and "p_holm" in s["k_v3"]["P1"]                 # rule v3, on tertile_v3


def test_residual_score_is_log10_score_regressed_on_log10_n_eff_over_the_scored_diseases():
    """Melissa's decision of 2026-11-26, the post hoc: the residual of log10 score on log10 effective sample size,
    fit over the scored diseases only."""
    from report.polygenicity_tests import residual_score
    u = pd.DataFrame({"mondo_id": list("abcdef"), "scored": [True] * 5 + [False], "log10_score": [1.0, 2.0, 3.0, 4.0, 5.5, 9.0],
                      "n_eff": [1e3, 1e4, 1e5, 1e6, 1e7, 1e9]})
    r = residual_score(u)
    assert r["diseases"] == 5 and abs(r["slope"] - 1.1) < 1e-9   # the unscored disease is out of the fit
    assert set(r["residual"].index) == set("abcde") and abs(r["residual"].sum()) < 1e-9 and 0 < r["r2"] <= 1


def test_post_hoc_residual_tests_p1_and_p2_two_sided_without_holm():
    from report.polygenicity_tests import post_hoc
    r = post_hoc(synthetic())
    assert set(r) == {"P1", "P2"}
    for t in r.values():
        assert "rr" in t and "p" in t and "p_one_sided" not in t and "p_holm" not in t and t["sides"] == 2
        assert t["reading"] in ("association", "no association") and t["direction"] in ("registered", "opposite")


def test_tertile_changes_count_the_diseases_whose_tertile_differs_between_two_cuts():
    from report.polygenicity_tests import tertile_changes
    u = pd.DataFrame({"mondo_id": list("abcdef"), "tertile": ["top", "top", "middle", "bottom", "none", "bottom"],
                      "tertile_k": ["top", "middle", "middle", "none", "bottom", "bottom"]})
    assert tertile_changes(u, "tertile", "tertile_k") == {"changed": 3, "between_tertiles": 1, "lost_score": 1, "gained_score": 1,
                                                          "diseases": ["b", "d", "e"]}


def test_alternative_tertiles_recut_the_corrected_k_and_residual_scores_and_count_the_moves():
    from report.polygenicity_tests import alternative_tertiles
    ids = [f"M{i}" for i in range(9)]
    score = [10, 20, 30, 40, 50, 60, 70, 80, 90.0]
    u = pd.DataFrame({"mondo_id": ids, "scored": [True] * 9, "score": score, "log10_score": np.log10(score),
                      "n_eff": 10.0 ** np.arange(3, 12), "score_k_corrected": [90, 80, 70, 40, 50, 60, 30, 20, 10.0],
                      "ldsc_status_k_corrected": ["ok"] * 8 + ["no_k"],
                      "score_v3": score, "ldsc_status_v3": ["no_k"] + ["ok"] * 8, "category_v3": [True] + [False] * 8})
    u2, meta = alternative_tertiles(u, cuts=(30.0, 60.0))
    assert u2.tertile_v3.iloc[0] == "none" and meta["k_v3"]["scored_diseases"] == 8 and meta["k_v3"]["category_scored"] == 1
    assert meta["k_v3"]["changes"]["lost_score"] == 1 and meta["k_v3"]["changes"]["gained_score"] == 0
    assert list(u2.tertile) == ["bottom"] * 3 + ["middle"] * 3 + ["top"] * 3
    assert list(u2.tertile_k) == ["top", "top", "top", "bottom", "middle", "middle", "bottom", "bottom", "none"]
    assert meta["k_corrected"]["scored_diseases"] == 8 and meta["k_corrected"]["changes"]["changed"] == 7
    assert meta["k_corrected"]["changes"] == {"changed": 7, "between_tertiles": 6, "lost_score": 1, "gained_score": 0,
                                              "diseases": ["M0", "M1", "M2", "M3", "M6", "M7", "M8"]}
    assert sorted(u2.tertile_resid.value_counts().tolist()) == [3, 3, 3] and meta["residual"]["diseases"] == 9
    # a disease that stays on GBD under v3 has no code under either rule and is not a changed code
    u3 = u.assign(k_source=["gbd"] + ["panukb"] * 8, k_code=[None] + ["I10"] * 8, k_v3_source=["gbd"] + ["panukb"] * 8,
                  k_v3_code=[None, "401"] + ["I10"] * 7)
    assert alternative_tertiles(u3, cuts=(30.0, 60.0))[1]["k_v3"]["code_changed"] == 1


def test_negative_control_leaves_safety_stops_out_and_is_two_sided():
    from report.polygenicity_tests import negative_control
    d = synthetic()
    r = negative_control(d)
    c = cohort(d, "mode_not_causal")
    assert r["exposed_entries"] + r["reference_entries"] == int((c.stop_safety <= 0).sum())
    assert r["exposed_events"] == int(c.stop_unrelated[(c.top > 0) & (c.stop_safety <= 0)].sum())
    assert "rr" in r and "p" in r and "p_one_sided" not in r and "p_holm" not in r
    assert r["reading"] in ("no association", "association")


def test_power_simulation_reports_power_per_test_and_effect():
    from report.polygenicity_tests import power_simulation
    out = power_simulation(synthetic(), reps=3, seed=1)
    assert set(out["power"]) == {"P1", "P2", "P3"} and out["reps"] == 3
    for by_effect in out["power"].values():
        assert by_effect and all(0.0 <= v["power"] <= 1.0 for v in by_effect.values())
    assert out["base_rates"]["mode_not_causal"] > 0 and out["base_rates"]["s4"] > 0
    assert {"top", "bottom"} <= set(out["entries"])


def test_results_table_rows_and_columns():
    t = results_table({"primary": registered(synthetic())})
    assert list(t.columns) == ["family", "test", "rr", "lo", "hi", "p", "p_one_sided", "p_holm", "reading",
                               "exposed_entries", "exposed_events", "reference_entries", "reference_events"]
    assert list(t.test) == ["P1", "P2", "P3"]


def test_numbers_key_the_tertile_rates_and_cutpoints_and_carry_the_extras():
    from report.polygenicity_tests import numbers
    d = synthetic()
    desc = {"by_tertile": [{"tertile": "bottom", "entries": 10}, {"tertile": "top", "entries": 12}], "no_score": {"diseases": 2}}
    n = numbers(d, {"P1": {}}, {}, desc, cuts=(1.5, 2.5), extra={"daly": {"flags": {"diseases": 3}}})
    assert n["tertiles"]["top"]["entries"] == 12 and n["tertiles"]["bottom"]["entries"] == 10
    assert n["cutpoints"]["score"] == {"lower": 1.5, "upper": 2.5} and "concentration" not in n["cutpoints"]
    assert n["daly"]["flags"]["diseases"] == 3 and n["cohort"]["entries"] == len(d)
    assert n["cohort"]["scored_diseases"] == d.mondo_id.nunique()


def test_descriptives_always_report_each_group_size(monkeypatch):
    from report.polygenicity_tests import descriptives
    monkeypatch.setattr("report.polygenicity_tests.engaged_modes", lambda: pd.DataFrame({"key": [], "not_causal_basis": []}))
    d = synthetic().assign(k_source="panukb", not_causal_basis="history")
    ids = sorted(d.mondo_id.unique())
    u = pd.DataFrame({"mondo_id": ids, "label": ids, "scored": True, "entries": 10, "ldsc_status": "ok", "h2_z": 1.0,
                      "h2_liab": 0.2, "loci": 5, "loci_catalog": None, "gwas_genes_per_10k_cases": None, "me_log10": None,
                      "score": 25.0, "n_eff": 1e4, "panukb_h2_liab": None})
    out = descriptives(d, u)
    assert out["z_at_least_2"]["diseases"] == 0 and out["z_at_least_2"]["tests"] == {}
    assert out["gbd_k_only"]["diseases"] == 0 and out["catalog_loci"]["diseases"] == 0
    assert out["gwas_genes"]["diseases"] == 0 and out["oconnor"]["n"] == 0


def test_holm_keeps_the_registered_family_of_three():
    from report.polygenicity_tests import holm_family
    adj = holm_family({"P1": 0.01, "P2": 0.04, "P3": None})
    assert adj["P1"] == 0.03 and adj["P2"] == 0.08 and "P3" not in adj


def test_rates_count_entries_with_a_resolved_target():
    """The figure and the tertile table sit on the tests' denominator, entries with a resolved primary target; the
    entries without one are counted beside the rate, not inside it."""
    from report.polygenicity_tests import rates
    d = synthetic()
    d.loc[d.index[:60], "has_target_disease"] = False
    r = rates(d, "tertile").set_index("tertile")
    top = d[d.tertile.eq("top")]
    res = top[top.has_target_disease]
    assert r.loc["top", "entries"] == len(res) and r.loc["top", "without_target"] == int((~top.has_target_disease).sum())
    assert r.loc["top", "not_causal"] == int(res.mode_not_causal.sum()) and r.loc["top", "phase2_entries"] == int(res.phase.eq(2).sum())


def test_p3_reports_the_genetics_ratio_within_each_tertile_whose_own_cells_allow_it():
    """When the interaction is not estimable because one tertile's cell is short of target sets, the genetics ratio
    is still fit within the other tertile, and the short one is marked not estimable."""
    d = synthetic()
    d.loc[d[(d.tertile == "bottom") & (d.genetics == 1)].index, "target"] = "t1"
    r = p3(d)
    assert r["estimable"] is False and "rr" not in r
    assert "rr" in r["genetics_within"]["top"] and r["genetics_within"]["bottom"]["estimable"] is False


def test_gwas_size_check_reports_spearman_and_median_n_eff_by_tertile():
    from report.polygenicity_tests import gwas_size_check
    u = pd.DataFrame({"mondo_id": list("abcdef"), "scored": True, "score": [1, 2, 3, 4, 5, 6], "n_eff": [10, 20, 30, 40, 50, 60]})
    m = pd.DataFrame({"mondo_id": list("abcdef"), "tertile": ["bottom"] * 2 + ["middle"] * 2 + ["top"] * 2})
    r = gwas_size_check(u, m)
    assert r["n"] == 6 and abs(r["spearman"] - 1.0) < 1e-9 and r["median_n_eff"] == {"bottom": 15.0, "middle": 35.0, "top": 55.0}


def test_panukb_check_compares_our_liability_h2_with_pan_ukb():
    from report.polygenicity_tests import panukb_check
    u = pd.DataFrame({"mondo_id": list("abcd"), "scored": True, "h2_liab": [0.1, 0.2, 0.3, 0.4], "panukb_h2_liab": [0.4, 0.3, 0.2, None]})
    r = panukb_check(u)
    assert r["n"] == 3 and abs(r["spearman"] + 1.0) < 1e-9


def test_descriptives_count_gbd_k_diseases_among_the_scored_only(monkeypatch):
    from report.polygenicity_tests import descriptives
    monkeypatch.setattr("report.polygenicity_tests.engaged_modes", lambda: pd.DataFrame({"key": [], "not_causal_basis": []}))
    d = synthetic().assign(k_source="gbd", not_causal_basis="history")
    ids = sorted(d.mondo_id.unique())
    d.loc[d.mondo_id.isin(ids[:20]), "scored"] = False
    u = pd.DataFrame({"mondo_id": ids, "label": ids, "scored": [i >= 20 for i in range(len(ids))], "entries": 10, "ldsc_status": "ok",
                      "h2_z": 1.0, "h2_liab": 0.2, "loci": 5, "loci_catalog": None, "gwas_genes_per_10k_cases": None,
                      "me_log10": None, "score": 25.0, "n_eff": 1e4, "panukb_h2_liab": None})
    out = descriptives(d, u)
    assert out["gbd_k_only"]["diseases"] == len(ids) - 20 and "gwas_size" in out and "panukb" in out
