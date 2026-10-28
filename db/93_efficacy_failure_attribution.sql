-- Why each program that stopped for efficacy failed (pipeline.attribution): the
-- PubMed papers retrieved for each entity's human pharmacology and for each of its
-- program diseases, and the LLM's three-pillar reading and failure code per
-- (entity, disease, phase). Keyed by entity and disease, not program_id, so the
-- rows survive a programs rebuild.

BEGIN;
SET LOCAL lock_timeout = '3s';

CREATE TABLE IF NOT EXISTS preclin.moiety_publication (
    moiety_id     integer NOT NULL REFERENCES preclin.moiety,
    mondo_id      text NOT NULL,
    pmid          text NOT NULL REFERENCES public.publications (pmid),
    query_kind    text NOT NULL CHECK (query_kind IN ('pharmacology', 'disease')),
    rank          integer NOT NULL,
    query         text NOT NULL,
    retrieved_at  timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (moiety_id, mondo_id, query_kind, pmid)
);
COMMENT ON TABLE preclin.moiety_publication IS
    'PubMed search results (relevance order) for an entity: its human pharmacology (mondo_id = '''') and the entity in one program disease.';
COMMENT ON COLUMN preclin.moiety_publication.mondo_id IS 'Program disease of a disease query; empty for a pharmacology query.';
COMMENT ON COLUMN preclin.moiety_publication.rank IS 'Position in PubMed relevance order, from 1.';
COMMENT ON COLUMN preclin.moiety_publication.query IS 'The PubMed query string as sent.';

CREATE TABLE IF NOT EXISTS preclin.efficacy_failure_attribution (
    moiety_id            integer NOT NULL REFERENCES preclin.moiety,
    mondo_id             text NOT NULL,
    phase                integer NOT NULL,
    index_nct_id         text NOT NULL REFERENCES preclin.ctgov_study,
    exposure             text NOT NULL,
    engagement           text NOT NULL,
    pathway              text NOT NULL,
    engagement_in_disease boolean NOT NULL,
    engagement_before_index boolean NOT NULL,
    dose_limited         boolean NOT NULL,
    primary_code         text NOT NULL,
    secondary_codes      text[] NOT NULL,
    confidence           text NOT NULL,
    sources              text[] NOT NULL,
    llm_decision_id      bigint NOT NULL REFERENCES pv_evidence.llm_decision,
    PRIMARY KEY (moiety_id, mondo_id, phase)
);
COMMENT ON TABLE preclin.efficacy_failure_attribution IS
    'Failure code of each program Section 1 records as stopped for efficacy, from the three pillars (Morgan et al. 2012) read in the sources assembled for it. Plan: report/attribution_plan.md.';
COMMENT ON COLUMN preclin.efficacy_failure_attribution.index_nct_id IS 'The trial that gave the program its efficacy reason in Section 1.';
COMMENT ON COLUMN preclin.efficacy_failure_attribution.exposure IS 'Pillar 1, drug at the site of action in humans: adequate, inferred_adequate, inadequate or no_human_data.';
COMMENT ON COLUMN preclin.efficacy_failure_attribution.engagement IS 'Pillar 2, binding or engagement of the target in humans: adequate, inferred_adequate, inadequate or no_human_data.';
COMMENT ON COLUMN preclin.efficacy_failure_attribution.pathway IS 'Pillar 3, the expected functional or pathway effect in humans: adequate, inferred_adequate, inadequate or no_human_data.';
COMMENT ON COLUMN preclin.efficacy_failure_attribution.engagement_in_disease IS 'Engagement evidence came from patients with the program disease.';
COMMENT ON COLUMN preclin.efficacy_failure_attribution.engagement_before_index IS 'Engagement evidence was public or registered before the index trial started.';
COMMENT ON COLUMN preclin.efficacy_failure_attribution.dose_limited IS 'Tolerability capped the dose below what engagement needed.';
COMMENT ON COLUMN preclin.efficacy_failure_attribution.primary_code IS 'F1a, F1b, F2-F9 or U, as defined in report/attribution_plan.md.';
COMMENT ON COLUMN preclin.efficacy_failure_attribution.sources IS 'Source ids (NCT ids, PMID:n) the decision cites; every one was shown to the model.';
COMMIT;
