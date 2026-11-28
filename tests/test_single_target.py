import pytest

from pipeline.single_target import how_solved, stacked_rrr, validate_merge, validate_pathway, why_not_one_drug


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
