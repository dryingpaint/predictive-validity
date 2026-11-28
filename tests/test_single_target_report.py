import pandas as pd
import pytest

from report.single_target import (approved_pathways, crossover_pairs, disease_labels, label_table, shortlist_table,
                                  tried_by_area)

PSORIASIS = "MONDO:0005083"


def test_an_entity_without_a_resolved_target_counts_as_labelled_but_adds_no_pathway():
    labelled = pd.DataFrame({"mondo_id": [PSORIASIS, PSORIASIS], "moiety_id": [1, 2]})
    out = approved_pathways(labelled, {1: ("IL17A|binder_neutralizer", "IL17A", "binder_neutralizer")},
                            {"IL17A|binder_neutralizer": ("specific", ["IL-17"])})
    assert out.set_index("moiety_id").loc[1, "pathways"] == ["IL-17"]
    assert out.set_index("moiety_id").loc[2, "kind"] == "unresolved"


def test_a_disease_stays_with_three_approved_pathways_and_tried_success_is_the_overlap():
    approved = pd.DataFrame({"mondo_id": [PSORIASIS] * 3, "moiety_id": [1, 2, 3], "kind": ["specific"] * 3,
                             "pathways": [["IL-17"], ["IL-23"], ["TNF", "IL-17"]]})
    tried = pd.DataFrame({"mondo_id": [PSORIASIS] * 3, "pathway": ["IL-17", "JAK-STAT", "IL-23"]})
    row = shortlist_table(tried, approved).set_index("mondo_id").loc[PSORIASIS]
    assert (row.approved_pathways, row.tried_pathways, row.tried_approved, bool(row.stays)) == (3, 3, 2, True)


def test_a_disease_with_two_approved_pathways_is_dropped():
    approved = pd.DataFrame({"mondo_id": [PSORIASIS] * 2, "moiety_id": [1, 2], "kind": ["specific"] * 2,
                             "pathways": [["IL-17"], ["IL-23"]]})
    row = shortlist_table(pd.DataFrame(columns=["mondo_id", "pathway"]), approved).set_index("mondo_id").loc[PSORIASIS]
    assert not row.stays


def test_oncology_and_infectious_disease_are_flagged_apart():
    tried = pd.DataFrame({"area": ["oncology", "autoimmune", "autoimmune"], "mondo_id": ["a", "b", "b"],
                          "pathway": ["EGFR", "TNF", "IL-17"]})
    t = tried_by_area(tried).set_index("area")
    assert t.loc["oncology", "reported_apart"] and not t.loc["autoimmune", "reported_apart"]
    assert t.loc["autoimmune", "median_pathways"] == 2


def estimate(**kw):
    row = {"mondo_id": PSORIASIS, "question": "response", "regimen": "drug", "pathways": ["IL-17"], "one_drug": True,
           "endpoint": "PASI 90", "measure": "share", "population": "naive", "failed_pathway": None,
           "stack_position": None, "pair_key": None, "estimate": 40.0, "source_name": "s", "source_kind": "trial",
           "trial_weeks": 100.0, "drugs": ["drug"], "subgroup": False}
    return {**row, **kw}


def test_one_drug_at_half_solves_and_its_pathways_are_counted():
    rows = pd.DataFrame([estimate(regimen="bimekizumab", estimate=70.0), estimate(regimen="bispecific", estimate=30.0,
                                                                                 pathways=["IL-17", "TNF"])])
    out = disease_labels(rows, [])
    assert (out["how_solved_50"], out["best_one_drug"], out["best_one_drug_pathways"]) == ("solved_by_one_drug",
                                                                                          "bimekizumab", 1)
    assert out["why_not_one_drug"] is None


def test_a_prior_failure_estimate_does_not_count_toward_how_solved():
    rows = pd.DataFrame([estimate(estimate=45.0), estimate(question="crossover", population="prior_failure",
                                                           failed_pathway="TNF", pair_key="a", estimate=80.0)])
    out = disease_labels(rows, [])
    assert (out["how_solved_40"], out["how_solved_50"]) == ("solved_by_one_drug", "unsolved")


def test_an_event_stack_multiplies_hazard_ratios_in_position_order():
    rows = pd.DataFrame([estimate(question="events", measure="hazard_ratio", estimate=hr, stack_position=i + 1,
                                  regimen=f"d{i}") for i, hr in enumerate([0.8, 0.7, 0.75])])
    out = disease_labels(rows, [])
    assert out["stack_effect"] == pytest.approx(1 - 0.8 * 0.7 * 0.75, abs=1e-3)
    assert (out["how_solved_50"], out["best_one_drug_effect"]) == ("solved_by_stacking", 0.3)
    assert out["why_not_one_drug"] == "cant_tell"


def test_a_multi_drug_regimen_against_placebo_is_the_stack_and_an_add_on_is_not():
    rows = pd.DataFrame([estimate(estimate=30.0), estimate(one_drug=False, estimate=55.0, regimen="a + b"),
                         estimate(one_drug=False, population="on_background", estimate=70.0)])
    out = disease_labels(rows, [])
    assert (out["how_solved_50"], out["stack"]) == ("solved_by_stacking", "a + b")


def test_retained_effect_is_prior_failure_over_naive_per_comparison():
    rows = pd.DataFrame([estimate(estimate=20.0)]
                        + [estimate(question="crossover", population=p, failed_pathway="TNF" if p != "naive" else None,
                                    pair_key=k, estimate=e)
                           for k, p, e in [("a", "prior_failure", 10.0), ("a", "naive", 25.0),
                                           ("b", "prior_failure", 12.0), ("b", "naive", 30.0)]])
    pairs = crossover_pairs(rows)
    assert sorted(pairs.retained) == pytest.approx([0.4, 0.4])
    winning = [{"relation": "parallel", "result": "met_primary", "stopped_for_safety": False}]
    assert disease_labels(rows, winning)["why_not_one_drug"] == "several_targets"
    assert disease_labels(rows, [])["why_not_one_drug"] == "cant_tell"


def test_a_subgroup_estimate_does_not_solve_a_disease():
    rows = pd.DataFrame([estimate(estimate=30.0), estimate(estimate=70.0, subgroup=True)])
    assert disease_labels(rows, [])["how_solved_50"] == "unsolved"


def test_a_subgroup_stack_position_takes_the_whole_trial_estimate_of_its_pathway():
    hr = {"question": "events", "measure": "hazard_ratio"}
    rows = pd.DataFrame([estimate(**hr, estimate=0.8, stack_position=1, pathways=["RAS"]),
                         estimate(**hr, estimate=0.4, stack_position=2, pathways=["MR"], subgroup=True),
                         estimate(**hr, estimate=0.82, pathways=["MR"], source_kind="trial"),
                         estimate(**hr, estimate=0.77, pathways=["MR"], source_kind="pooled_trials")])
    out = disease_labels(rows, [])
    assert out["stack_effect"] == pytest.approx(1 - 0.8 * 0.77, abs=1e-3)
    assert out["best_one_drug_effect"] == pytest.approx(0.23)


def test_the_fda_sensitivity_leaves_out_drugs_without_a_label():
    responses = pd.DataFrame([estimate(drugs=["netakimab"], estimate=64.0, regimen="netakimab"),
                              estimate(drugs=["bimekizumab"], estimate=34.0, regimen="bimekizumab")])
    combos = pd.DataFrame(columns=["mondo_id", "relation", "result", "stopped_for_safety"])
    row = label_table(responses, combos, {"bimekizumab"}).set_index("mondo_id").loc[PSORIASIS]
    assert (row.how_solved_50, row.how_solved_50_fda_approved_only) == ("solved_by_one_drug", "unsolved")
    assert row.best_one_drug_fda_approved_only == "bimekizumab"
