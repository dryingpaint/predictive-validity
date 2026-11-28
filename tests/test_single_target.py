import pytest

from pipeline.single_target import (combination_beats_single, how_solved, partner_works_alone, retrieved_source,
                                    stacked_rrr, success_regimen, validate_combos, validate_merge, validate_pathway,
                                    validate_regimen, why_not_one_drug)


def test_one_drug_reaching_half_solves_the_disease():
    assert how_solved([0.70, 0.30], stack=None) == "solved_by_one_drug"


def test_a_stack_reaching_half_when_no_single_drug_does_is_solved_by_stacking():
    assert how_solved([0.25, 0.30], stack=1 - 0.70 * 0.80 * 0.75 * 0.80) == "solved_by_stacking"


def test_neither_reaching_half_is_unsolved():
    assert how_solved([0.20], stack=0.35) == "unsolved"
    assert how_solved([], stack=None) == "unsolved"


def test_the_sensitivity_threshold_moves_the_line():
    assert how_solved([0.46], stack=None) == "unsolved"
    assert how_solved([0.46], stack=None, solved_at=0.40) == "solved_by_one_drug"


def test_stacked_risk_reduction_multiplies_the_add_on_hazard_ratios():
    assert stacked_rrr([0.5, 0.8]) == pytest.approx(0.6)


def test_effect_that_survives_a_switch_means_different_patients():
    assert why_not_one_drug([0.8, 0.9, 0.6], combination_beats_single=False) == "different_patients"


def test_several_targets_needs_both_lost_effect_and_a_winning_combination():
    assert why_not_one_drug([0.3, 0.4], combination_beats_single=True) == "several_targets"
    assert why_not_one_drug([0.3, 0.4], combination_beats_single=False) == "cant_tell"


def test_a_winning_combination_without_crossover_data_cannot_tell():
    assert why_not_one_drug([], combination_beats_single=True) == "cant_tell"


def test_retained_effect_between_the_thresholds_cannot_tell():
    assert why_not_one_drug([0.6], combination_beats_single=True) == "cant_tell"


def test_a_specific_mechanism_names_one_to_three_pathways():
    validate_pathway({}, {"kind": "specific", "pathways": ["IL-17"]})
    validate_pathway({}, {"kind": "broad", "pathways": []})
    with pytest.raises(ValueError):
        validate_pathway({}, {"kind": "specific", "pathways": []})
    with pytest.raises(ValueError):
        validate_pathway({}, {"kind": "broad", "pathways": ["MAPK"]})


def test_the_merge_maps_every_name_exactly_once():
    payload = {"names": [("IL-17", 3), ("IL17", 1)]}
    validate_merge(payload, {"names": [{"name": "IL-17", "canonical": ["IL-17"]},
                                       {"name": "IL17", "canonical": ["IL-17"]}]})
    with pytest.raises(ValueError):
        validate_merge(payload, {"names": [{"name": "IL-17", "canonical": ["IL-17"]}]})
    with pytest.raises(ValueError):
        validate_merge(payload, {"names": [{"name": "IL-17", "canonical": ["IL-17"]}, {"name": "IL17", "canonical": []}]})


def test_one_success_tested_alone_makes_the_target_work_alone():
    assert success_regimen(["combination", "add_on_background"], unread_approvals=1) == "alone"
    assert success_regimen(["monotherapy"], unread_approvals=0) == "alone"


def test_with_partner_needs_every_success_to_be_a_combination():
    assert success_regimen(["combination", "combination"], unread_approvals=0) == "with_partner"


def test_an_approval_with_no_trial_to_read_leaves_combinations_unknown():
    assert success_regimen(["combination"], unread_approvals=1) == "unknown"
    assert success_regimen([], unread_approvals=2) == "unknown"


def test_partners_work_alone_only_when_every_one_does():
    assert partner_works_alone([7, 8], works_alone={7, 8}) is True
    assert partner_works_alone([7, 8], works_alone={7}) is False
    assert partner_works_alone([7, None], works_alone={7}) is None
    assert partner_works_alone([8, None], works_alone={7}) is False


REGIMEN_RECORD = {"moiety_id": 1, "title": "Drug A plus drug B in psoriasis", "official_title": "", "summary": "",
                  "arms": "- A+B (EXPERIMENTAL): A 10 mg and B 5 mg",
                  "interventions": [{"name": "A", "type": "DRUG", "arms": [], "entities": [(1, "a")]},
                                    {"name": "B", "type": "DRUG", "arms": [], "entities": [(2, "b")]}]}


def test_a_combination_names_a_listed_partner_and_quotes_the_record():
    validate_regimen(REGIMEN_RECORD, {"regimen": "combination", "partner": "B", "partner_moiety_id": 2,
                                      "quote": "Drug A plus drug B"})
    validate_regimen(REGIMEN_RECORD, {"regimen": "monotherapy", "partner": None, "partner_moiety_id": None,
                                      "quote": "A 10 mg"})
    validate_regimen(REGIMEN_RECORD, {"regimen": "combination", "partner": "B", "partner_moiety_id": 2,
                                      "quote": "A+B (EXPERIMENTAL): ... B 5 mg"})
    for bad in ({"regimen": "combination", "partner": None, "partner_moiety_id": None, "quote": "A 10 mg"},
                {"regimen": "monotherapy", "partner": "B", "partner_moiety_id": None, "quote": "A 10 mg"},
                {"regimen": "combination", "partner": "B", "partner_moiety_id": 1, "quote": "A 10 mg"},
                {"regimen": "combination", "partner": "B", "partner_moiety_id": 3, "quote": "A 10 mg"},
                {"regimen": "combination", "partner": "B", "partner_moiety_id": 2, "quote": "A with C"},
                {"regimen": "combination", "partner": "B", "partner_moiety_id": 2, "quote": "A 10 mg ... C 5 mg"},
                {"regimen": "combination", "partner": "B", "partner_moiety_id": 2, "quote": "..."}):
        with pytest.raises(ValueError):
            validate_regimen(REGIMEN_RECORD, bad)


def trial(**kw):
    return {"relation": "parallel", "result": "met_primary", "stopped_for_safety": False, **kw}


def test_a_winning_two_pathway_trial_safe_to_use_beats_single():
    assert combination_beats_single([trial(result="missed_primary"), trial()])
    assert combination_beats_single([trial(relation="independent")])

def test_no_trials_or_only_losing_trials_do_not_beat_single():
    assert not combination_beats_single([])
    assert not combination_beats_single([trial(result="missed_primary")])

def test_a_win_stopped_or_abandoned_for_safety_does_not_count():
    assert not combination_beats_single([trial(stopped_for_safety=True)])

def test_more_of_one_pathway_is_not_two_pathways():
    assert not combination_beats_single([trial(relation="same_pathway")])


def combo_output(**kw):
    t = {"trial_name": "BE RADIANT", "nct_id": "NCT03536884", "pmid": "33891380", "year": 2021, "phase": "3",
         "n_randomised": 743, "two_pathway_arm": "bimekizumab", "one_pathway_arm": "secukinumab",
         "comparator_pathways": ["IL-17"], "added_pathway": "IL-17", "design": "head_to_head_multi_pathway",
         "relation": "same_pathway", "primary_endpoint": "PASI 100 wk 16", "result": "met_primary",
         "effect_measure": "risk_difference", "effect": 12.7, "ci_low": 5.8, "ci_high": 19.6, "effect_text": "",
         "limited_by": "none", "stopped_for_safety": False, "sources": ["https://pubmed.ncbi.nlm.nih.gov/33891380/"],
         "quote": "", **kw}
    return {"trials": [t], "retrieved_urls": ["https://pubmed.ncbi.nlm.nih.gov/33891380"]}

def test_a_trial_read_from_retrieved_pages_is_valid():
    validate_combos({}, combo_output())
    validate_combos({}, combo_output(nct_id=None))

def test_a_source_cut_short_stands_for_the_retrieved_url_it_begins():
    long = "https://www.researchgate.net/publication/371368790_Plain_language_summary_of_results_from_ORION-11"
    assert retrieved_source(long[:80], [long]) == long
    assert retrieved_source("https://pubmed.ncbi.nlm.nih.gov/33891380/", [long]) is None
    assert retrieved_source("https://www.r", [long]) is None


@pytest.mark.parametrize("bad", [
    {"sources": ["https://example.org/not-retrieved"]},
    {"sources": []},
    {"nct_id": None, "pmid": None},
    {"nct_id": "NCT123"},
    {"relation": "parallel"},  # the added pathway is already the comparator's
    {"ci_low": 20.0, "ci_high": 5.0},
])

def test_a_trial_without_retrieved_sources_or_with_inconsistent_fields_is_rejected(bad):
    with pytest.raises(ValueError):
        validate_combos({}, combo_output(**bad))

def test_a_trial_listed_twice_is_rejected():
    out = combo_output()
    out["trials"] *= 2
    with pytest.raises(ValueError):
        validate_combos({}, out)
