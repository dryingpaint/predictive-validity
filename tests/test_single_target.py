import pytest

from pipeline.single_target import (combination_beats_single, how_solved, stacked_rrr, validate_combos, validate_merge,
                                    validate_pathway, why_not_one_drug)


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
