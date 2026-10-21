-- The kind of endpoint each industry Phase 2/3 trial's governing primary outcome
-- measures (pipeline.outcomes endpoints): its purpose, its class from target
-- engagement through regulatory surrogates, clinical scales and patient reports to
-- disease events and hard outcomes (oncology: response, progression, survival),
-- and how it is measured.

BEGIN;
SET LOCAL lock_timeout = '3s';
CREATE TABLE IF NOT EXISTS preclin.trial_endpoint (
    nct_id            text PRIMARY KEY REFERENCES preclin.ctgov_study,
    purpose           text NOT NULL,
    endpoint_class    text NOT NULL,
    governing_index   integer NOT NULL,
    measurement_type  text NOT NULL,
    scale             text NOT NULL,
    n_primaries       integer NOT NULL,
    llm_decision_id   bigint NOT NULL REFERENCES pv_evidence.llm_decision
);
COMMIT;
