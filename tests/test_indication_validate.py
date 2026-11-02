"""The condition mapper's validation: a term outside the candidates, or a term on a non-disease
condition that the term does not name, is refused."""
import pytest

from pipeline.indications import validate

CANDIDATES = [{"mondo_id": "MONDO:0005148", "label": "type 2 diabetes mellitus", "synonyms": ["T2DM"]},
              {"mondo_id": "MONDO:0005618", "label": "anxiety", "synonyms": []}]


def payload(name, variants=()):
    return {"name": name, "variants": list(variants), "candidates": CANDIDATES}


def test_disease_may_take_any_candidate():
    validate(payload("Diabetes Mellitus, Type 2"), {"kind": "disease", "mondo_id": "MONDO:0005148"})


def test_term_outside_candidates_is_refused():
    with pytest.raises(ValueError):
        validate(payload("Gout"), {"kind": "disease", "mondo_id": "MONDO:0005393"})


def test_non_disease_keeps_a_term_that_names_it():
    validate(payload("Anxiety"), {"kind": "symptom_or_sign", "mondo_id": "MONDO:0005618"})
    validate(payload("t2dm", variants=["T2DM"]), {"kind": "other", "mondo_id": "MONDO:0005148"})


def test_non_disease_with_a_term_naming_something_else_is_refused():
    with pytest.raises(ValueError):
        validate(payload("Glucose Lowering"), {"kind": "procedure_or_state", "mondo_id": "MONDO:0005148"})


def test_broader_pass_output_has_no_kind():
    validate(payload("Diabetes"), {"match": "broader", "mondo_id": "MONDO:0005148"})
