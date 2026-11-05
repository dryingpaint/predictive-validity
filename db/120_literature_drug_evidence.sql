-- Version 2 of the literature evidence about a drug before a phase entry (pipeline.literature): one PubMed search
-- per drug by its names alone, one LLM screen per abstract deciding every kind of evidence, and the MONDO term of
-- each disease an animal model was said to model. Version 1's rows (migration 119) stay as its record.

BEGIN;
SET LOCAL lock_timeout = '3s';

CREATE TABLE preclin.literature_drug_search (
    moiety_id   integer NOT NULL REFERENCES preclin.moiety,
    cutoff_year integer NOT NULL,
    names       text[] NOT NULL,
    query       text NOT NULL,
    n_hits      integer NOT NULL,
    searched_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (moiety_id, cutoff_year)
);
COMMENT ON TABLE preclin.literature_drug_search IS
    'Each PubMed search by a drug''s names alone (INN, code names, FDA substance-registry, PubChem and ChEMBL synonyms), publications up to cutoff_year, reviews excluded: the latest cutoff of the entity''s entries, so earlier entries filter the hits by year.';

CREATE TABLE preclin.literature_drug_hit (
    moiety_id   integer NOT NULL,
    cutoff_year integer NOT NULL,
    pmid        text NOT NULL REFERENCES public.publications (pmid),
    rank        integer NOT NULL,
    PRIMARY KEY (moiety_id, cutoff_year, pmid),
    FOREIGN KEY (moiety_id, cutoff_year) REFERENCES preclin.literature_drug_search ON DELETE CASCADE
);
COMMENT ON TABLE preclin.literature_drug_hit IS 'The abstracts a preclin.literature_drug_search kept, in PubMed relevance order.';

CREATE TABLE preclin.literature_drug_screen (
    moiety_id          integer NOT NULL REFERENCES preclin.moiety,
    pmid               text NOT NULL REFERENCES public.publications (pmid),
    original_data      boolean NOT NULL,
    animal_disease     boolean NOT NULL,
    modelled_diseases  text[] NOT NULL,
    animal_healthy     boolean NOT NULL,
    human_engagement   boolean NOT NULL,
    species            text,
    detail             text,
    quote              text,
    llm_decision_id    bigint NOT NULL REFERENCES pv_evidence.llm_decision (llm_decision_id),
    PRIMARY KEY (moiety_id, pmid)
);
COMMENT ON TABLE preclin.literature_drug_screen IS
    'An LLM''s reading of one abstract about one drug: whether it reports original data on the drug, and whether it tests the drug for efficacy in an animal model of a disease (and which diseases, as written), reports its pharmacology in healthy animals, or measures its target engagement or a pharmacodynamic biomarker in people.';
COMMENT ON COLUMN preclin.literature_drug_screen.modelled_diseases IS
    'The human diseases the animal models model, as the abstract names them; empty unless animal_disease.';

CREATE TABLE preclin.literature_model_disease (
    modelled_disease text PRIMARY KEY,
    mondo_id         text,
    match            text NOT NULL CHECK (match IN ('exact', 'broader', 'none')),
    llm_decision_id  bigint NOT NULL REFERENCES pv_evidence.llm_decision (llm_decision_id),
    CHECK ((match = 'none') = (mondo_id IS NULL))
);
COMMENT ON TABLE preclin.literature_model_disease IS
    'The MONDO term of each disease an animal model was said to model (preclin.literature_drug_screen.modelled_diseases): the term naming it (exact), else the narrowest term containing it (broader), chosen by an LLM among retrieved candidates as pipeline.indications does.';

COMMIT;
