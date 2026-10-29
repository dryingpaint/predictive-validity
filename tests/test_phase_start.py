"""An extension study (starts_phase false) neither marks phase entry nor advances a program."""
from __future__ import annotations

from datetime import date

import pandas as pd

from report.section1 import phase_rows
from report.windows import RECENT


def program() -> pd.DataFrame:
    return pd.DataFrame([{"program_id": 1, "moiety_id": 10, "mondo_id": "MONDO:0000001", "approved": "no",
                          "first_approval_date": None, "date_basis": None, "moiety_first_fda_approval": None,
                          "bio_area": "oncology", "modality": "small_molecule"}])


def trial(nct: str, phase: int, start: str, end: str, starts_phase: bool) -> dict:
    return {"program_id": 1, "nct_id": nct, "phase": phase, "attach": "disease", "marks_entry": True,
            "starts_phase": starts_phase, "industry": True, "overall_status": "COMPLETED",
            "start_date": date.fromisoformat(start), "start_date_type": "ACTUAL", "last_update_posted": date.fromisoformat(end),
            "primary_completion_date": date.fromisoformat(end), "completion_date": date.fromisoformat(end),
            "us_site": False, "has_results": False}


def phase2_event(extension_starts_phase: bool) -> str:
    trials = pd.DataFrame([trial("NCT1", 2, "2016-01-01", "2018-01-01", True),
                           trial("NCT2", 3, "2018-06-01", "2020-01-01", extension_starts_phase)])
    rows = phase_rows(program(), trials, date(2026, 10, 20), window=RECENT)
    return rows[(rows.phase == 2) & ~rows.credited].event.iloc[0]


def test_extension_does_not_advance_the_program():
    assert phase2_event(extension_starts_phase=True) == "advanced"
    assert phase2_event(extension_starts_phase=False) == "suspended"


def test_phase_role_output_names_only_listed_drugs():
    import pytest

    from pipeline.programs import validate_phase_role
    validate_phase_role({"drugs": ["atrasentan", "zigakibart"]}, {"main_period_drugs": ["atrasentan"]})
    with pytest.raises(ValueError):
        validate_phase_role({"drugs": ["atrasentan"]}, {"main_period_drugs": ["sparsentan"]})


def test_phase_role_names_in_the_trials_own_wording_resolve_to_listed_drugs():
    from pipeline.programs import listed_drug
    two = {"drugs": ["tacrolimus anhydrous", "sirolimus"],
           "interventions": [{"name": "Prograf", "otherNames": ["tacrolimus"]}, {"name": "Rapamune"}]}
    assert listed_drug("Tacrolimus", two) == "tacrolimus anhydrous"
    assert listed_drug("Prograf", two) == "tacrolimus anhydrous"
    assert listed_drug("AZOPT (brinzolamide)", {"drugs": ["brinzolamide", "levobetaxolol"]}) == "brinzolamide"
    assert listed_drug("RAD001", {"drugs": ["everolimus"], "interventions": [{"name": "RAD001"}]}) == "everolimus"
    assert listed_drug("Rapamune", two) is None  # its entry names no listed drug, and the trial has two
    assert listed_drug("sparsentan", {"drugs": ["atrasentan"], "interventions": [{"name": "atrasentan"}]}) is None
