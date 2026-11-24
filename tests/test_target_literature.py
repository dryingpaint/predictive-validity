import pytest

from pipeline.target_literature import KINDS, clauses, counts, validate_screen


def decision(original=True, disease="same_or_subtype", agent=None, **kinds):
    return {"original_data": original, "system": "none", "disease_match": disease, "agent_is_program_drug": agent,
            "kinds": {k: kinds.get(k, False) for k in KINDS}, "quote": ""}


def test_a_record_counts_only_when_original_same_disease_and_showing_the_kind():
    assert counts(decision(observational_biomarker=True), "observational_biomarker")
    assert not counts(decision(original=False, observational_biomarker=True), "observational_biomarker")
    assert not counts(decision(disease="related", observational_biomarker=True), "observational_biomarker")
    assert not counts(decision(observational_biomarker=True), "clinical_observation")


def test_animal_pharmacology_with_the_program_drug_counts_for_the_pooled_kind_but_not_for_other_agents():
    own = decision(animal_model_pharmacology=True, agent=True)
    other = decision(animal_model_pharmacology=True, agent=False)
    assert counts(own, "animal_model_pharmacology") and not counts(own, "animal_model_pharmacology_other")
    assert counts(other, "animal_model_pharmacology") and counts(other, "animal_model_pharmacology_other")


def test_the_agent_flag_is_set_exactly_when_animal_pharmacology_is_read():
    validate_screen({}, decision(animal_model_pharmacology=True, agent=False))
    validate_screen({}, decision())
    with pytest.raises(ValueError):
        validate_screen({}, decision(agent=True))
    with pytest.raises(ValueError):
        validate_screen({}, decision(animal_model_pharmacology=True))


def test_a_pair_is_searched_by_a_gene_name_and_a_disease_name_or_model_term():
    pm, ep = clauses({"gene": ["TNF", "TNF-alpha"], "disease": ["rheumatoid arthritis"],
                      "models": ["collagen-induced arthritis", "Rheumatoid Arthritis"]})
    assert pm == ('("TNF"[tiab] OR "TNF-alpha"[tiab]) AND ("rheumatoid arthritis"[tiab] OR '
                  '"collagen-induced arthritis"[tiab])')
    assert ep == ('(TITLE_ABS:"TNF" OR TITLE_ABS:"TNF-alpha") AND (TITLE_ABS:"rheumatoid arthritis" OR '
                  'TITLE_ABS:"collagen-induced arthritis")')


def test_web_shards_split_the_pairs_without_overlap_or_gaps():
    import pandas as pd
    from pipeline.target_literature import shard_of
    p = pd.DataFrame({"ensembl_id": [f"ENSG{i:011d}" for i in range(200)], "mondo_id": ["MONDO:0005015"] * 200})
    parts = [shard_of(p, f"{i}/8") for i in range(1, 9)]
    keys = [k for part in parts for k in zip(part.ensembl_id, part.mondo_id)]
    assert len(keys) == len(set(keys)) == len(p)


def test_a_model_named_pmid_counts_only_when_its_title_matches():
    from pipeline.target_literature import TITLE_MATCH, title_match
    assert title_match("IL-23 blockade attenuates colitis in mice", "Il-23 blockade attenuates colitis in mice.") >= TITLE_MATCH
    assert title_match("IL-23 blockade attenuates colitis in mice", "A survey of hospital staffing") < TITLE_MATCH
