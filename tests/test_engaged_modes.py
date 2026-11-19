import pandas as pd

from report.engaged_modes import ENGAGED_MODES, MODE_LAYER, RELATED_MODES, engaged_mode


def test_a_target_that_never_worked_in_this_disease_is_not_causal():
    assert engaged_mode("worked_elsewhere_only", None, None) == "not_causal"
    assert engaged_mode("never_worked_tried_again", "drug_inadequate", None) == "not_causal"


def test_a_related_success_takes_the_reading_of_the_related_disease():
    assert engaged_mode("worked_related", None, "different_disease") == "not_causal"
    assert engaged_mode("worked_related", None, "wrong_patients") == "wrong_patients"
    assert engaged_mode("worked_related", None, "wrong_time") == "wrong_time"
    assert engaged_mode("worked_related", None, None) == "unresolved"


def test_a_success_here_only_in_biomarker_selected_patients_is_wrong_patients():
    assert engaged_mode("worked_here_selected", "drug_inadequate", None) == "wrong_patients"


def test_where_the_record_leaves_it_open_the_verdict_decides():
    assert engaged_mode("worked_here", "drug_inadequate", None) == "drug_fell_short"
    assert engaged_mode("worked_here", "trial_inadequate", None) == "trial_could_not_answer"
    assert engaged_mode("worked_here", "wrong_stage_or_timing", None) == "wrong_time"
    assert engaged_mode("never_worked_single", "wrong_patients", None) == "wrong_patients"
    assert engaged_mode("never_worked_single", "target_not_causal", None) == "not_causal"


def test_a_not_causal_verdict_the_record_contradicts_stays_unresolved():
    assert engaged_mode("worked_here", "target_not_causal", None) == "unresolved"
    assert engaged_mode("never_worked_single", "unclear", None) == "unresolved"
    assert engaged_mode("no_target", None, None) == "unresolved"


def test_every_mode_has_a_layer_and_the_related_reading_uses_known_categories():
    assert set(MODE_LAYER) == set(ENGAGED_MODES)
    r = pd.read_csv(RELATED_MODES)
    assert r.key.is_unique
    assert set(r.category) <= {"different_disease", "wrong_patients", "wrong_time", "unclear"}
