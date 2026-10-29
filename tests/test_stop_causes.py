"""What preclin.stop records for a stop, from its registry reason, inference decision and efficacy label."""
from __future__ import annotations

from pipeline.stop_causes import stop_row

TRIAL = {"nct_id": "NCT00000001", "stated": None}


def inferred(cause: str, likely: str | None = None, **changes) -> dict:
    out = {"cause": cause, "likely_cause": likely or cause, "quote": "", "likely_basis": "", "rationale": "",
           "sources": ["https://example.org/release"]}
    return {"llm_decision_id": 11, "parsed_output": {**out, **changes}}


def label(**changes) -> dict:
    out = {"subcause": "engaged_no_benefit", "detail": None, "quote": "", "rationale": "Occupancy was high; no benefit.",
           "sources": ["PMID:1"], "llm_decision_id": 22}
    return {**out, **changes}


def test_a_registry_efficacy_stop_takes_why_efficacy_failed_from_its_label():
    row = stop_row("efficacy: stated", None, None, label(), None, TRIAL)
    assert (row["cause"], row["subcause"], row["traced"]) == ("efficacy", "engaged_no_benefit", False)
    assert row["explanation"] == "Occupancy was high; no benefit."
    assert (row["sources"], row["decision_ids"]) == (["PMID:1"], [22])


def test_an_efficacy_stop_without_a_label_is_not_attributed():
    row = stop_row("PK, dose or formulation", None, None, None, None, TRIAL)
    assert (row["cause"], row["subcause"]) == ("efficacy", "not_attributed")


def test_a_label_of_off_target_toxicity_makes_the_stop_a_safety_stop():
    row = stop_row("efficacy: primary endpoint not met", "safety", None, label(subcause=None), None, TRIAL)
    assert (row["cause"], row["subcause"], row["traced"]) == ("safety", "off_target_toxicity", True)
    assert row["decision_ids"] == [22]


def test_a_traced_company_event_is_a_sponsor_decision():
    row = stop_row("stopped, no reason stated", "infer", inferred("company_event", quote="The company wound down."),
                   None, "sponsor_went_quiet", TRIAL)
    assert (row["cause"], row["subcause"], row["guess"]) == ("sponsor_decision", "company_event", None)
    assert (row["explanation"], row["decision_ids"]) == ("The company wound down.", [11])


def test_an_unexplained_stop_keeps_the_guess_and_what_happened_next():
    row = stop_row("completed, no results posted, no reason stated", "infer",
                   inferred("unknown", "business_strategic", likely_basis="Dropped quietly."), None, "drug_dropped",
                   TRIAL)
    assert (row["cause"], row["subcause"], row["guess"]) == ("unknown", "drug_dropped", "sponsor_decision")
    assert row["explanation"] == "Dropped quietly."


def test_a_stop_inference_could_not_decide_has_no_guess():
    row = stop_row("stopped, no reason stated", "infer", None, None, "sponsor_went_quiet", TRIAL)
    assert (row["cause"], row["subcause"], row["guess"], row["decision_ids"]) == \
        ("unknown", "sponsor_went_quiet", None, [])


def test_a_stop_the_registry_explains_quotes_its_trial():
    row = stop_row("business or strategic (explicit)", None, None, None, None,
                   {"nct_id": "NCT00000002", "stated": " termination due to portfolio prioritization "})
    assert (row["cause"], row["explanation"], row["sources"]) == \
        ("sponsor_decision", "termination due to portfolio prioritization", ["NCT00000002"])


def test_a_label_explains_an_efficacy_stop_before_its_trial_does():
    row = stop_row("efficacy: stated", None, None, label(), None, {"nct_id": "NCT00000003", "stated": "Futility."})
    assert (row["explanation"], row["sources"]) == ("Occupancy was high; no benefit.", ["PMID:1"])
