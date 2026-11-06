-- Version 3 of the literature evidence about a drug before a phase entry (pipeline.literature), the third and
-- user-directed attempt of report/translation_plan.md: every PubMed abstract matching the drug's names (no cap),
-- abstracts outside MEDLINE from Europe PMC, papers from Firecrawl's research index (semantic search and
-- citation-graph expansion), a cheap prefilter for drugs with a very large literature, and the version 2 screen.
-- Versions 1 and 2 keep their rows (migrations 119, 120) as their record.

BEGIN;
SET LOCAL lock_timeout = '3s';

CREATE TABLE preclin.literature_record (
    record_id  text PRIMARY KEY,
    source     text NOT NULL,
    title      text NOT NULL,
    abstract   text,
    year       integer,
    doi        text
);
COMMENT ON TABLE preclin.literature_record IS
    'Abstracts outside MEDLINE that a version 3 literature search retrieved from Europe PMC (preprints, patents, theses, Agricola and other sources), keyed "<Europe PMC source>:<id>". PubMed abstracts stay in public.publications.';

CREATE TABLE preclin.literature_v3_search (
    moiety_id   integer NOT NULL REFERENCES preclin.moiety,
    cutoff_year integer NOT NULL,
    source      text NOT NULL CHECK (source IN ('pubmed', 'europepmc')),
    names       text[] NOT NULL,
    query       text NOT NULL,
    n_hits      integer NOT NULL,
    searched_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (moiety_id, cutoff_year, source)
);
COMMENT ON TABLE preclin.literature_v3_search IS
    'Each version 3 search by a drug''s names alone, up to cutoff_year (the latest cutoff of the entity''s entries), reviews excluded: PubMed titles and abstracts, every hit kept; Europe PMC titles and abstracts outside MEDLINE with an abstract.';

CREATE TABLE preclin.literature_v3_firecrawl (
    moiety_id   integer NOT NULL REFERENCES preclin.moiety,
    mondo_id    text NOT NULL,
    cutoff_year integer NOT NULL,
    mode        text NOT NULL CHECK (mode IN ('search', 'related')),
    query       text NOT NULL,
    n_results   integer NOT NULL,
    searched_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (moiety_id, mondo_id, cutoff_year, mode)
);
COMMENT ON TABLE preclin.literature_v3_firecrawl IS
    'Each call to Firecrawl''s research index: a semantic search for one entry (the drug''s names, its disease and the three kinds, papers up to cutoff_year; mondo_id is the entry''s disease) or a citation-graph expansion (related papers, mode similar) from one qualifying record of the drug (mondo_id empty; results kept up to cutoff_year).';

CREATE TABLE preclin.literature_v3_hit (
    moiety_id   integer NOT NULL REFERENCES preclin.moiety,
    cutoff_year integer NOT NULL,
    source      text NOT NULL CHECK (source IN ('pubmed', 'europepmc', 'firecrawl')),
    record_id   text NOT NULL,
    PRIMARY KEY (moiety_id, cutoff_year, source, record_id)
);
COMMENT ON TABLE preclin.literature_v3_hit IS
    'Every record a version 3 retrieval returned for a drug, by source: a PMID (public.publications) or a preclin.literature_record id. cutoff_year is the latest cutoff of the drug''s entries. A record returned by several sources has a row for each.';

CREATE TABLE preclin.literature_v3_prefilter (
    moiety_id       integer NOT NULL REFERENCES preclin.moiety,
    record_id       text NOT NULL,
    possibly        boolean NOT NULL,
    llm_decision_id bigint NOT NULL REFERENCES pv_evidence.llm_decision (llm_decision_id),
    PRIMARY KEY (moiety_id, record_id)
);
COMMENT ON TABLE preclin.literature_v3_prefilter IS
    'For a drug whose searches returned more than PREFILTER_ABOVE records, a cheap first reading of each: whether it possibly reports original data on the drug of any of the three kinds. Only records read as possibly go to the full screen.';

CREATE TABLE preclin.literature_v3_screen (
    moiety_id          integer NOT NULL REFERENCES preclin.moiety,
    record_id          text NOT NULL,
    original_data      boolean NOT NULL,
    animal_disease     boolean NOT NULL,
    modelled_diseases  text[] NOT NULL,
    animal_healthy     boolean NOT NULL,
    human_engagement   boolean NOT NULL,
    species            text,
    detail             text,
    quote              text,
    llm_decision_id    bigint NOT NULL REFERENCES pv_evidence.llm_decision (llm_decision_id),
    PRIMARY KEY (moiety_id, record_id)
);
COMMENT ON TABLE preclin.literature_v3_screen IS
    'The version 2 screen (task literature_drug_screen) of each version 3 record that reached it: whether it reports original data on the drug, tests it in an animal model of a disease (and which, as written; mapped in preclin.literature_model_disease), reports its pharmacology in healthy animals, or measures its target engagement in people.';

COMMIT;
