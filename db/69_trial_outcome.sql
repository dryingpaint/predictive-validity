-- What happened in each classified trial (pipeline.outcomes classify): how
-- far it ran, the stated reason for stopping, whether the primary endpoint
-- was met according to posted results, and any safety signal. Replaces the
-- why_stopped rows in preclin.classification for analyses on preclin.dev_program.

BEGIN;
SET LOCAL lock_timeout = '90s';
CREATE TABLE IF NOT EXISTS preclin.trial_outcome (
    nct_id            text PRIMARY KEY REFERENCES preclin.ctgov_study,
    execution         text NOT NULL,
    stop_reason       text NOT NULL,
    secondary_reasons text[] NOT NULL,
    primary_endpoint  text NOT NULL,
    safety_signal     text NOT NULL,
    efficacy_failure  boolean NOT NULL,
    evidence          text NOT NULL,
    llm_decision_id   bigint NOT NULL REFERENCES pv_evidence.llm_decision
);
COMMIT;
