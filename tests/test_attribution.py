"""Efficacy-failure attribution: which decisions the validator accepts, and what the model is shown."""
from __future__ import annotations

import pytest

from pipeline import attribution


def bundle() -> dict:
    return {
        "drug": "examplumab", "codes": ["EX-1234"], "modality": "monoclonal_antibody", "targets": ["IL5 (binder_neutralizer)"],
        "disease": "atopic eczema", "phase": 2, "approvals": ["asthma (2015-11-04)"],
        "index": {"nct_id": "NCT00000001", "title": "Examplumab in atopic eczema", "phases": ["PHASE2"],
                  "status": "TERMINATED", "start": "2016-01-01", "enrollment": 40, "conditions": ["Atopic Dermatitis"],
                  "why_stopped": "lack of efficacy", "stop_reason": "efficacy_futility", "primary_endpoint": "not_met",
                  "evidence": "lack of efficacy", "endpoint_class": "B5_clinician_scale",
                  "primary_outcomes": "EASI-50 [week 16]", "results": ""},
        "trials": [{"nct_id": "NCT00000002", "phase": 3, "start": "2012-01-01", "sponsor": "industry",
                    "title": "Examplumab in severe asthma", "conditions": "Asthma", "status": "COMPLETED",
                    "stop_reason": "not_applicable", "primary_endpoint": "met", "endpoint_class": "B7_disease_events",
                    "evidence": "exacerbations reduced"}],
        "phase1_results": [], "same_target": [],
        "papers": [{"pmid": "111", "year": 2010, "title": "Blood eosinophils fall after examplumab",
                    "abstract": "Eosinophils fell by 90%."}],
    }


def decision(**changes) -> dict:
    out = {"exposure": "inferred_adequate", "engagement": "adequate", "pathway": "adequate",
           "engagement_in_disease": False, "engagement_before_index": True, "dose_limited": False,
           "primary_code": "F2", "secondary_codes": [], "confidence": "high",
           "sources": ["PMID:111", "NCT00000002"], "rationale": "Engaged; no benefit."}
    return {**out, **changes}


def test_engaged_without_benefit_is_accepted():
    attribution.validate(bundle(), decision())


@pytest.mark.parametrize("changes", [
    {"sources": ["PMID:999"]},  # a paper the model was not shown
    {"engagement": "no_human_data"},  # F2 without engagement
    {"primary_code": "F1a"},  # not engaged, with every pillar adequate
    {"primary_code": "U"},  # indeterminate although engagement was shown
    {"primary_code": "F1b"},  # molecule-specific although engagement was adequate
])
def test_inconsistent_decisions_are_rejected(changes):
    with pytest.raises(ValueError):
        attribution.validate(bundle(), decision(**changes))


def test_indeterminate_needs_no_engagement_data():
    attribution.validate(bundle(), decision(engagement="no_human_data", exposure="no_human_data",
                                            pathway="no_human_data", primary_code="U", sources=[]))


def test_rendered_bundle_shows_every_citable_source():
    text = attribution.TASK.render(bundle())
    for source in attribution.source_ids(bundle()):
        assert source.removeprefix("PMID:") in text


def test_search_skips_short_code_names():
    assert attribution.search_names("aspirin", ["ASA", "TF2", "BAY1019036"]) == ["aspirin", "BAY1019036"]
