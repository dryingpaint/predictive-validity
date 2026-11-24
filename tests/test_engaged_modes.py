import pandas as pd

from report.engaged_modes import ENGAGED_MODES, GROUP_OF, GROUPS, RELATED_MODES, engaged_mode, not_causal_basis


def test_a_target_that_never_worked_in_this_disease_is_not_causal():
    assert engaged_mode("worked_elsewhere_only", None, None) == "not_causal"
    assert engaged_mode("never_worked_tried_again", "drug_inadequate", None) == "not_causal"


def test_a_related_success_takes_the_reading_of_the_related_disease():
    assert engaged_mode("worked_related", None, "different_disease") == "not_causal"
    assert engaged_mode("worked_related", None, "wrong_patients") == "wrong_patients"
    assert engaged_mode("worked_related", None, "wrong_time") == "wrong_time"
    assert engaged_mode("worked_related", None, None) == "unresolved"


def test_a_success_here_only_in_biomarker_selected_patients_is_wrong_patients():
    assert engaged_mode("worked_here_selected", None, None) == "wrong_patients"
    assert engaged_mode("worked_here_selected", "target_not_causal", None) == "wrong_patients"


def test_a_drug_that_fell_short_comes_before_wrong_patients_or_wrong_time():
    assert engaged_mode("worked_here_selected", "drug_inadequate", None) == "drug_fell_short"
    assert engaged_mode("worked_related", "drug_inadequate", "wrong_time") == "drug_fell_short"
    assert engaged_mode("worked_related", "drug_inadequate", "different_disease") == "drug_fell_short"


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


def test_the_modes_fall_under_three_groups():
    assert [GROUP_OF[m] for m in ENGAGED_MODES] == ["not_causal", "causal", "causal", "causal", "unclear", "unclear"]
    assert list(GROUPS) == ["not_causal", "causal", "unclear"]


def test_a_not_causal_call_rests_on_the_stop_evidence_or_else_the_target_history():
    assert not_causal_basis("not_causal", "target_not_causal") == "stop_evidence"
    assert not_causal_basis("not_causal", None) == "history"
    assert not_causal_basis("not_causal", "drug_inadequate") == "history"
    assert not_causal_basis("drug_fell_short", "drug_inadequate") is None


def test_the_related_reading_uses_known_categories():
    r = pd.read_csv(RELATED_MODES)
    assert r.key.is_unique
    assert set(r.category) <= {"different_disease", "wrong_patients", "wrong_time", "unclear"}
