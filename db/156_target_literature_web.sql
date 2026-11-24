-- The target-biology literature of issue #154, second retrieval arm: a web-enabled model searches the web for each
-- target-disease pair's qualifying studies (iterative searches, full text, reviews, citations), as the pilot's
-- reference did. Every study it names is kept with how its identifier was verified; the verified ones are hits of
-- the pair (source web_agent) and go through the same screen as every other record. A differently set up
-- web-enabled model lists the studies of a seeded sample of pairs as the yardstick for both arms' recall
-- (report/audits/target_literature_web.md). The kinds stay descriptive (report/audits/target_literature_gate.md).

BEGIN;
SET LOCAL lock_timeout = '3s';

ALTER TABLE preclin.target_literature_search DROP CONSTRAINT target_literature_search_source_check;
ALTER TABLE preclin.target_literature_search ADD CONSTRAINT target_literature_search_source_check
    CHECK (source IN ('pubmed', 'europepmc', 'firecrawl', 'firecrawl_related', 'origin_pubmed', 'origin_europepmc',
                      'web_agent'));
COMMENT ON COLUMN preclin.target_literature_search.source IS
    'pubmed and europepmc: title and abstract searches by gene names and disease names or model terms; firecrawl: Firecrawl''s research index, once per kind; firecrawl_related: papers related to the pair''s first screened-in record; origin_pubmed and origin_europepmc: the origin search''s records (#146, preclin.target_disease_source), linked as hits; web_agent: a web-enabled model''s search of the web for the pair''s studies of every kind (preclin.target_literature_web_study, arm web).';

CREATE TABLE preclin.target_literature_web_study (
    arm             text NOT NULL CHECK (arm IN ('web', 'yardstick')),
    ensembl_id      text NOT NULL,
    mondo_id        text NOT NULL,
    cutoff_year     integer NOT NULL,
    ordinal         integer NOT NULL,
    kind            text NOT NULL,
    title           text NOT NULL,
    year            integer,
    venue           text,
    pmid_given      text,
    doi_given       text,
    record_id       text,
    verification    text NOT NULL CHECK (verification IN ('pmid_matched', 'pmid_corrected', 'doi_resolved', 'unverified')),
    llm_decision_id bigint,
    PRIMARY KEY (arm, ensembl_id, mondo_id, ordinal),
    FOREIGN KEY (ensembl_id, mondo_id) REFERENCES preclin.target_disease (ensembl_id, mondo_id)
);
CREATE INDEX target_literature_web_study_record_idx ON preclin.target_literature_web_study (record_id);

COMMENT ON TABLE preclin.target_literature_web_study IS
    'Every study a web-enabled model named for a target-disease pair (#154). arm web: the second retrieval arm over every cohort pair (its verified studies are the pair''s web_agent hits in preclin.target_literature_hit and are screened like any record); arm yardstick: a differently set up model''s list for a seeded sample of pairs, the reference both arms'' recall is scored against. Both arms and the yardstick are model web searches, so the yardstick is not fully independent of the web arm.';
COMMENT ON COLUMN preclin.target_literature_web_study.arm IS 'web (the retrieval arm) or yardstick (the recall reference).';
COMMENT ON COLUMN preclin.target_literature_web_study.ensembl_id IS 'The pair''s gene (preclin.target_disease).';
COMMENT ON COLUMN preclin.target_literature_web_study.mondo_id IS 'The pair''s disease (preclin.target_disease).';
COMMENT ON COLUMN preclin.target_literature_web_study.cutoff_year IS 'The year before the pair''s latest 2008-2019 cohort entry; the model was asked for studies published in or before it.';
COMMENT ON COLUMN preclin.target_literature_web_study.ordinal IS 'The study''s position in the model''s answer.';
COMMENT ON COLUMN preclin.target_literature_web_study.kind IS 'The kind the model listed the study under (pipeline.target_literature.REFERENCE_KINDS; animal_model_pharmacology_other excludes the program drugs). The screen, not this label, decides which kinds a record counts for.';
COMMENT ON COLUMN preclin.target_literature_web_study.title IS 'The title the model gave.';
COMMENT ON COLUMN preclin.target_literature_web_study.year IS 'The publication year the model gave.';
COMMENT ON COLUMN preclin.target_literature_web_study.venue IS 'The journal, conference or other venue the model gave.';
COMMENT ON COLUMN preclin.target_literature_web_study.pmid_given IS 'The PMID the model gave, as given.';
COMMENT ON COLUMN preclin.target_literature_web_study.doi_given IS 'The DOI the model gave, as given.';
COMMENT ON COLUMN preclin.target_literature_web_study.record_id IS 'The verified record: a PMID whose PubMed title matches the stated title, else the one PubMed record a title search matches, else the PubMed or Europe PMC record the DOI resolves to; null when none verifies.';
COMMENT ON COLUMN preclin.target_literature_web_study.verification IS 'pmid_matched: the given PMID''s title matches; pmid_corrected: a PubMed title search found the record; doi_resolved: the DOI resolved through Europe PMC; unverified: no record found (not a hit).';
COMMENT ON COLUMN preclin.target_literature_web_study.llm_decision_id IS 'The model''s decision (pv_evidence.llm_decision) the study comes from; null for the pilot''s reference studies, which are read from report/audits/target_literature_reference.';

COMMIT;
