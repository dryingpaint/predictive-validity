import pytest

from pipeline.single_target import Response, disease_label, validate_merge, validate_pathway

IL23 = Response(frozenset({"IL-23"}), response=0.75, delta=0.70)
TNF = Response(frozenset({"TNF"}), response=0.45, delta=0.30)
IL6 = Response(frozenset({"IL-6"}), response=0.40, delta=0.25)
DUAL = Response(frozenset({"GLP-1", "GIP"}), response=0.57, delta=0.54)


def test_one_pathway_reaching_goal_is_single_target_enough_whatever_crossover_shows():
    assert disease_label([IL23, TNF], retained=[0.3], combination_beats_single=True) == "single_target_enough"


def test_fewer_than_two_mechanisms_cannot_be_labelled():
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


def test_only_a_two_pathway_drug_reaching_goal_goes_to_the_crossover_rules():
    single = Response(frozenset({"GLP-1"}), response=0.48, delta=0.44)
    assert disease_label([single, DUAL], retained=[], combination_beats_single=True) == "cant_tell"


def test_a_specific_mechanism_names_one_to_three_pathways():
    validate_pathway({}, {"kind": "specific", "pathways": ["IL-17"]})
    validate_pathway({}, {"kind": "broad", "pathways": []})
    with pytest.raises(ValueError):
        validate_pathway({}, {"kind": "specific", "pathways": []})
    with pytest.raises(ValueError):
        validate_pathway({}, {"kind": "broad", "pathways": ["MAPK"]})


def test_the_merge_maps_every_name_exactly_once():
    payload = {"names": [("IL-17", 3), ("IL17", 1)]}
    validate_merge(payload, {"names": [{"name": "IL-17", "canonical": "IL-17"}, {"name": "IL17", "canonical": "IL-17"}]})
    with pytest.raises(ValueError):
        validate_merge(payload, {"names": [{"name": "IL-17", "canonical": "IL-17"}]})
