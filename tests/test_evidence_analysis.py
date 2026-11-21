import pandas as pd

from report.evidence_analysis import failing, loa_rows, stop_outcomes

# Program 1 entered Phase 1 and jumped straight to Phase 3, so Phase 2 is credited as passed;
# program 2 entered Phase 2 and stopped.
ROWS = pd.DataFrame([
    {"program_id": 1, "phase": 1, "entry": "2012-01-01", "event": "advanced", "credited": False},
    {"program_id": 1, "phase": 2, "entry": "2012-01-01", "event": "advanced", "credited": True},
    {"program_id": 1, "phase": 3, "entry": "2015-06-01", "event": "suspended", "credited": False},
    {"program_id": 2, "phase": 2, "entry": "2013-01-01", "event": "suspended", "credited": False},
])
ENTRIES = pd.DataFrame([
    {"program_id": 1, "phase": 1, "entry_date": pd.Timestamp("2012-01-01").date(), "target": "A", "line": 1.0},
    {"program_id": 1, "phase": 3, "entry_date": pd.Timestamp("2015-06-01").date(), "target": "A", "line": 0.0},
    {"program_id": 2, "phase": 2, "entry_date": pd.Timestamp("2013-01-01").date(), "target": "B", "line": 0.0},
])


def test_a_skipped_phase_carries_the_features_of_the_entry_that_skipped_it():
    out = loa_rows(ENTRIES, ROWS).set_index(["program_id", "phase"])
    assert len(out) == 4
    assert out.loc[(1, 2), "line"] == 1.0  # credited Phase 2 takes the Phase 1 entry's evidence
    assert out.loc[(1, 3), "line"] == 0.0  # the later Phase 3 entry keeps its own
    assert out.loc[(1, 2), "event"] == "advanced"


# Traced stops: a dose cap, a registry PK reason, measured low engagement, engagement coded from another drug's success,
# engaged without benefit, and two safety stops (on-target toxicity offsetting the benefit, and one with no subcause).
STOPS = pd.DataFrame([
    {"likely": "efficacy", "subcause": "engaged_no_benefit", "detail": "dose_capped", "registry_reason": None},
    {"likely": "efficacy", "subcause": "not_stated", "detail": None, "registry_reason": "PK, dose or formulation"},
    {"likely": "efficacy", "subcause": "not_engaged", "detail": None, "registry_reason": None},
    {"likely": "efficacy", "subcause": "not_engaged", "detail": "other_drug_on_target_worked", "registry_reason": None},
    {"likely": "efficacy", "subcause": "engaged_no_benefit", "detail": None, "registry_reason": None},
    {"likely": "safety", "subcause": "on_target_toxicity", "detail": None, "registry_reason": None},
    {"likely": "safety", "subcause": "not_stated", "detail": None, "registry_reason": None},
])


def test_a_stop_where_the_target_was_never_reached_counts_once_whether_dose_or_engagement_kept_it_away():
    out = {k: v.tolist() for k, v in stop_outcomes(STOPS).items()}
    assert out["stop_not_reached"] == [True, True, True, False, False, False, False]
    assert out["stop_no_benefit"] == [False, False, False, False, True, False, False]
    assert out["stop_safety"] == [False] * 5 + [True, True]


# Three stops (efficacy with the target engaged, safety, a sponsor decision), an advance and a program still running.
PHASE_ROWS = pd.DataFrame({"event": ["suspended", "suspended", "suspended", "advanced", "censored"]})
COUNTED = pd.DataFrame({"stop_efficacy": [1.0, 0, 0, 0, 0], "stop_safety": [0, 1.0, 0, 0, 0],
                        "stop_not_reached": [0.0] * 5, "stop_no_benefit": [1.0, 0, 0, 0, 0]})


def test_a_failure_definition_censors_every_stop_it_does_not_count_and_leaves_advances_alone():
    def events(failure):
        return failing(PHASE_ROWS, COUNTED, failure).event.tolist()
    assert events("all") == ["suspended", "suspended", "suspended", "advanced", "censored"]
    assert events("efficacy_safety") == ["suspended", "suspended", "censored", "advanced", "censored"]
    assert events("safety") == ["censored", "suspended", "censored", "advanced", "censored"]
    assert events("no_benefit") == ["suspended", "censored", "censored", "advanced", "censored"]
    assert events("not_reached") == ["censored", "censored", "censored", "advanced", "censored"]
