"""What the outcome and endpoint classifiers are shown: registered primaries with publications, targets with endpoints."""
from __future__ import annotations

from pipeline import outcomes

REGISTERED = [{"measure": "Number of subjects with adverse events", "description": "Over 18 weeks",
               "timeFrame": "18 weeks", "type": "PRIMARY"},
              {"measure": "Cmax of the A-strand", "description": None, "timeFrame": "Day 1"}]


def publication_payload(registered: list[dict]) -> dict:
    payload = outcomes.trial_payload("NCT00000001", "Example siRNA in pancreatic cancer", ["PHASE1", "PHASE2"],
                                     "COMPLETED", 29, "2013-01-01", "2016-01-01", ["Pancreatic Cancer"],
                                     ["Atu027", "Gemcitabine"], None,
                                     "PMID 111 (2020): A phase 1b/2a trial\nMedian PFS 2.9 vs 1.6 months, p = 0.025.")
    return {**payload, "primary_outcomes": outcomes.primary_outcomes(registered)}


def test_publication_message_gives_the_registered_primaries_before_the_papers():
    text = outcomes.PUBLICATION_TASK.render(publication_payload(REGISTERED))
    primaries = text.index("Registered primary outcome measures:")
    first, second = (text.index("1. Number of subjects with adverse events | Over 18 weeks | time frame: 18 weeks"),
                     text.index("2. Cmax of the A-strand | time frame: Day 1"))
    papers = text.index("Results publications:\nPMID 111 (2020)")
    assert primaries < first < second < papers
    assert "Posted results" not in text


def test_publication_message_says_when_no_primary_is_registered():
    text = outcomes.PUBLICATION_TASK.render(publication_payload([]))
    assert "Registered primary outcome measures:\n(none registered)\n\nResults publications:" in text


def test_payload_keeps_only_the_shown_fields_of_each_primary():
    assert outcomes.primary_outcomes(REGISTERED)[0] == {
        "measure": "Number of subjects with adverse events", "description": "Over 18 weeks", "timeFrame": "18 weeks"}
    assert outcomes.primary_outcomes(None) == []


def endpoint_payload(drugs: list[list] | None) -> dict:
    return {"conditions": ["Cystic Fibrosis"], "phases": ["PHASE2"], "allocation": "RANDOMIZED", "masking": "DOUBLE",
            "model": "PARALLEL", "primary_outcomes": outcomes.primary_outcomes(
                [{"measure": "Change in sweat chloride", "timeFrame": "Day 28"}]),
            "investigational_targets": outcomes.investigational_targets(drugs)}


def test_endpoint_message_lists_each_drugs_targets_once_in_a_stable_order():
    one = endpoint_payload([["human_protein", "GUCY1A1 (activator); GUCY1B1 (activator)"],
                            ["pathogen", None], ["human_protein", "GUCY1A1 (activator); GUCY1B1 (activator)"]])
    other = endpoint_payload([["pathogen", None], ["human_protein", "GUCY1A1 (activator); GUCY1B1 (activator)"]])
    assert one == other
    text = outcomes.ENDPOINT_TASK.render(one)
    assert ("Targets of the investigational drug(s), one line per drug:\n"
            "- GUCY1A1 (activator); GUCY1B1 (activator)\n- acts on a pathogen, no human protein target\n\n"
            "Primary outcome measures:\n1. Change in sweat chloride | time frame: Day 28") in text


def test_endpoint_message_says_why_a_drug_has_no_target():
    text = outcomes.ENDPOINT_TASK.render(endpoint_payload([["no_single_target", None], ["unknown", None],
                                                           [None, None]]))
    assert "- no single molecular target\n- target unknown\n\n" in text
    assert "(no investigational drug identified)" in outcomes.ENDPOINT_TASK.render(endpoint_payload(None))
