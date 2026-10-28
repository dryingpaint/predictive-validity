-- Web-search pass of the efficacy attribution (pipeline.attribution search): each Phase 2/3
-- program that the bundle-only label (preclin.efficacy_failure_attribution) left indeterminate,
-- labelled again by a model that reads the same bundle and searches the web for human evidence of
-- exposure, engagement and pathway effect. Same pillars and codes as the bundle label; sources may
-- also be URLs the decision retrieved. Keyed by entity, disease and phase so rows survive a programs rebuild.

BEGIN;
SET LOCAL lock_timeout = '3s';

CREATE TABLE IF NOT EXISTS preclin.efficacy_attribution_search (
    moiety_id               integer NOT NULL REFERENCES preclin.moiety,
    mondo_id                text NOT NULL,
    phase                   integer NOT NULL,
    exposure                text NOT NULL,
    engagement              text NOT NULL,
    pathway                 text NOT NULL,
    engagement_in_disease   boolean NOT NULL,
    engagement_before_index boolean NOT NULL,
    dose_limited            boolean NOT NULL,
    primary_code            text NOT NULL,
    secondary_codes         text[] NOT NULL,
    confidence              text NOT NULL,
    quote                   text NOT NULL,
    sources                 text[] NOT NULL,
    llm_decision_id         bigint NOT NULL REFERENCES pv_evidence.llm_decision,
    method_id               text NOT NULL REFERENCES preclin.analysis_method,
    PRIMARY KEY (moiety_id, mondo_id, phase)
);
COMMENT ON TABLE preclin.efficacy_attribution_search IS
    'Efficacy attribution of programs the bundle-only label left indeterminate (code U), from the same bundle plus web search for human pharmacology: full-text papers, conference reports, regulatory reviews, company releases. Codes and pillars as in preclin.efficacy_failure_attribution.';
COMMENT ON COLUMN preclin.efficacy_attribution_search.quote IS 'The decisive sentence from a source, when one states the engagement evidence or the reason for failure; empty otherwise.';
COMMENT ON COLUMN preclin.efficacy_attribution_search.sources IS 'NCT ids, PMID:n or URLs the decision cites; every URL was retrieved during the decision.';
COMMIT;
