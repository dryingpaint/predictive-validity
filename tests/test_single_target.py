import pytest

from pipeline.single_target import Response, disease_label, event_label, validate_merge, validate_pathway

IL23 = Response(frozenset({"IL-23"}), delta=0.70, one_drug=True)
TNF = Response(frozenset({"TNF"}), delta=0.30, one_drug=True)
IL6 = Response(frozenset({"IL-6"}), delta=0.25, one_drug=True)
SEMAGLUTIDE = Response(frozenset({"GLP-1"}), delta=0.46, one_drug=True)
TIRZEPATIDE = Response(frozenset({"GLP-1", "GIP"}), delta=0.54, one_drug=True)


def test_one_drug_reaching_goal_solves_the_disease_whatever_crossover_shows():
    assert disease_label([IL23, TNF], retained=[0.3], combination_beats_single=True) == "solved_by_one_drug"


def test_a_drug_spanning_two_pathways_counts_as_one_drug():
    assert disease_label([SEMAGLUTIDE, TIRZEPATIDE], retained=[], combination_beats_single=False) == "solved_by_one_drug"


def test_two_drugs_given_together_do_not_count_as_one_drug():
    together = Response(frozenset({"TNF", "IL-6"}), delta=0.60, one_drug=False)
    assert disease_label([TNF, IL6, together], retained=[], combination_beats_single=True) == "cant_tell"


def test_a_drug_spanning_four_pathways_is_not_one_drug_solving_it():
    broad = Response(frozenset({"A", "B", "C", "D"}), delta=0.60, one_drug=True)
    assert disease_label([TNF, broad], retained=[], combination_beats_single=False) == "cant_tell"


def test_the_sensitivity_threshold_moves_the_line():
    assert disease_label([SEMAGLUTIDE, TNF], retained=[], combination_beats_single=False) == "cant_tell"
    assert disease_label([SEMAGLUTIDE, TNF], retained=[], combination_beats_single=False,
                         solved_delta=0.40) == "solved_by_one_drug"


def test_fewer_than_two_mechanisms_cannot_be_labelled_unless_solved():
    assert disease_label([TNF], retained=[0.9], combination_beats_single=False) == "cant_tell"


def test_partial_mechanisms_whose_effect_survives_a_switch_are_different_patients():
    assert disease_label([TNF, IL6], retained=[0.8, 0.9, 0.6], combination_beats_single=False) == "different_patients"


def test_several_targets_needs_both_lost_effect_and_a_winning_combination():
    assert disease_label([TNF, IL6], retained=[0.3, 0.4], combination_beats_single=True) == "several_targets_needed"
    assert disease_label([TNF, IL6], retained=[0.3, 0.4], combination_beats_single=False) == "cant_tell"


def test_a_winning_combination_without_crossover_data_cannot_be_labelled():
    assert disease_label([TNF, IL6], retained=[], combination_beats_single=True) == "cant_tell"


def test_retained_effect_between_the_thresholds_cannot_be_labelled():
    assert disease_label([TNF, IL6], retained=[0.6], combination_beats_single=True) == "cant_tell"


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


def test_one_drug_preventing_most_events_solves_an_event_disease():
    assert event_label([0.36], add_on_hrs=[]) == "solved_by_one_drug"


def test_a_stack_of_add_ons_preventing_most_events_is_solved_by_stacking():
    assert event_label([0.75, 0.80], add_on_hrs=[0.70, 0.80, 0.75, 0.80]) == "solved_by_stacking"


def test_neither_one_drug_nor_the_stack_reaching_half_the_events_is_unsolved():
    assert event_label([0.80], add_on_hrs=[0.85, 0.90]) == "unsolved"
    assert event_label([], add_on_hrs=[]) == "unsolved"
