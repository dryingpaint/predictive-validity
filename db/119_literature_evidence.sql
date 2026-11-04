-- PubMed evidence about a drug itself before a phase entry (pipeline.literature): the searches run, the
-- abstracts they returned, and an LLM's screen of each abstract.

BEGIN;
SET LOCAL lock_timeout = '3s';
CREATE TABLE IF NOT EXISTS preclin.literature_search (
    moiety_id   integer NOT NULL REFERENCES preclin.moiety,
    mondo_id    text NOT NULL,
    kind        text NOT NULL CHECK (kind IN ('animal_disease', 'animal_healthy', 'human_engagement')),
    cutoff_year integer NOT NULL,
    query       text NOT NULL,
    n_hits      integer NOT NULL,
    searched_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (moiety_id, mondo_id, kind, cutoff_year)
);
COMMENT ON TABLE preclin.literature_search IS
    'Each PubMed search pipeline.literature ran: an entity, a program disease (empty for the drug-level kinds animal_healthy and human_engagement), the kind of evidence sought and the last publication year searched (the year before the phase entry), with the total number of PubMed results.';

CREATE TABLE IF NOT EXISTS preclin.literature_hit (
    moiety_id   integer NOT NULL,
    mondo_id    text NOT NULL,
    kind        text NOT NULL,
    cutoff_year integer NOT NULL,
    pmid        text NOT NULL REFERENCES public.publications (pmid),
    rank        integer NOT NULL,
    PRIMARY KEY (moiety_id, mondo_id, kind, cutoff_year, pmid),
    FOREIGN KEY (moiety_id, mondo_id, kind, cutoff_year) REFERENCES preclin.literature_search ON DELETE CASCADE
);
COMMENT ON TABLE preclin.literature_hit IS
    'The abstracts a preclin.literature_search kept, in PubMed relevance order.';

CREATE TABLE IF NOT EXISTS preclin.literature_screen (
    moiety_id       integer NOT NULL REFERENCES preclin.moiety,
    mondo_id        text NOT NULL,
    pmid            text NOT NULL REFERENCES public.publications (pmid),
    kind            text NOT NULL CHECK (kind IN ('animal_disease', 'animal_healthy', 'human_engagement')),
    qualifies       boolean NOT NULL,
    species         text,
    detail          text,
    quote           text,
    llm_decision_id bigint NOT NULL REFERENCES pv_evidence.llm_decision,
    PRIMARY KEY (moiety_id, mondo_id, pmid, kind)
);
COMMENT ON TABLE preclin.literature_screen IS
    'Whether an abstract reports the entity itself: tested for efficacy in an animal model of the disease (animal_disease, keyed by the disease), studied in healthy animals for pharmacokinetics, pharmacodynamics or exposure (animal_healthy), or with target engagement or a pharmacodynamic biomarker measured in people (human_engagement); the drug-level kinds have an empty mondo_id. Decided by the referenced pv_evidence.llm_decision.';
COMMIT;
