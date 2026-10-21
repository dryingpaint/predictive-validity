-- The development indication each of an entity's diseases belongs to
-- (pipeline.programs indications): an LLM groups the MONDO diseases an entity's
-- trials list into the indications a sponsor runs as separate programs, merging
-- a disease with its subtypes, stages and settings (prostate cancer with
-- castration-resistant prostate carcinoma) and keeping distinct diseases apart.
-- Programs are keyed on the group's representative disease.

BEGIN;
SET LOCAL lock_timeout = '3s';
CREATE TABLE IF NOT EXISTS preclin.program_indication (
    moiety_id         integer NOT NULL REFERENCES preclin.moiety,
    mondo_id          text NOT NULL,
    indication_mondo  text NOT NULL,
    llm_decision_id   bigint NOT NULL REFERENCES pv_evidence.llm_decision,
    PRIMARY KEY (moiety_id, mondo_id)
);
COMMIT;
