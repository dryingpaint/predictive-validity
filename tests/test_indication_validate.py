"""The condition mapper's checks: a term outside the candidates is refused, and a condition that is
not a disease keeps a term only when the term names the condition itself."""
import pytest

from pipeline.indications import kept_term, validate

CANDIDATES = [{"mondo_id": "MONDO:0005148", "label": "type 2 diabetes mellitus", "synonyms": ["T2DM"]},
              {"mondo_id": "MONDO:0005618", "label": "anxiety", "synonyms": []}]


def payload(name, variants=()):
    return {"name": name, "variants": list(variants), "candidates": CANDIDATES}


def test_term_outside_candidates_is_refused():
    with pytest.raises(ValueError):
        validate(payload("Gout"), {"kind": "disease", "mondo_id": "MONDO:0005393"})


def test_disease_keeps_any_candidate():
    assert kept_term(payload("Diabetes Mellitus, Type 2"), {"kind": "disease", "mondo_id": "MONDO:0005148"}) \
        == "MONDO:0005148"


def test_non_disease_keeps_a_term_that_names_it():
    assert kept_term(payload("Anxiety"), {"kind": "symptom_or_sign", "mondo_id": "MONDO:0005618"}) == "MONDO:0005618"
    assert kept_term(payload("t2dm", variants=["T2DM"]), {"kind": "other", "mondo_id": "MONDO:0005148"}) \
        == "MONDO:0005148"


def test_non_disease_drops_a_term_naming_something_else():
    assert kept_term(payload("Glucose Lowering"), {"kind": "procedure_or_state", "mondo_id": "MONDO:0005148"}) is None


def test_no_term_stays_none():
    assert kept_term(payload("Healthy"), {"kind": "healthy_volunteers", "mondo_id": None}) is None
