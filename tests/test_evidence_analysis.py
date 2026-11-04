import pandas as pd

from report.evidence_analysis import loa_rows

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
