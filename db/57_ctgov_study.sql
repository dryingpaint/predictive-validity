-- ClinicalTrials.gov snapshot of every interventional study with a DRUG or
-- BIOLOGICAL intervention, any sponsor and any date (pipeline.ctgov).
-- Dates given only to the month are stored as the 1st of that month; the
-- *_date_type columns keep ACTUAL vs ESTIMATED.

BEGIN;

CREATE TABLE IF NOT EXISTS preclin.ctgov_study (
    nct_id                       text PRIMARY KEY CHECK (nct_id ~ '^NCT[0-9]{8}$'),
    brief_title                  text,
    official_title               text,
    overall_status               text,
    why_stopped                  text,
    phases                       text[] NOT NULL,
    start_date                   date,
    start_date_type              text,
    primary_completion_date      date,
    primary_completion_date_type text,
    completion_date              date,
    completion_date_type         text,
    first_posted                 date,
    last_update_posted           date,
    results_first_posted         date,
    has_results                  boolean NOT NULL,
    lead_sponsor                 text,
    lead_sponsor_class           text,
    collaborators                jsonb NOT NULL,
    enrollment                   integer,
    allocation                   text,
    intervention_model           text,
    masking                      text,
    primary_purpose              text,
    healthy_volunteers           boolean,
    conditions                   text[] NOT NULL,
    keywords                     text[] NOT NULL,
    interventions                jsonb NOT NULL,
    arm_groups                   jsonb NOT NULL,
    references_                  jsonb NOT NULL,
    source_release_id            bigint NOT NULL REFERENCES preclin.evidence_source_release
);
CREATE INDEX IF NOT EXISTS ctgov_study_status_idx ON preclin.ctgov_study (overall_status);
CREATE INDEX IF NOT EXISTS ctgov_study_start_idx ON preclin.ctgov_study (start_date);

COMMIT;
