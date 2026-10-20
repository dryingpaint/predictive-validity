-- Molecular entities behind each intervention name (pipeline.drugs).
-- preclin.moiety: one row per distinct active entity, keyed by its
-- nonproprietary name (or sponsor code when none exists).
-- preclin.drug_moiety: drug_id -> active components, with the LLM decision
-- that resolved them. Drugs resolved to placebo, vehicle or non-drug
-- interventions have no drug_moiety rows; preclin.drug.entity_kind says which.

BEGIN;

CREATE TABLE IF NOT EXISTS preclin.moiety (
    moiety_id   serial PRIMARY KEY,
    moiety_key  text NOT NULL UNIQUE CHECK (moiety_key ~ '^[a-z0-9]+$'),
    name        text NOT NULL,
    code_names  text[] NOT NULL DEFAULT '{}',
    chembl_id   text
);

CREATE TABLE IF NOT EXISTS preclin.drug_moiety (
    drug_id         integer NOT NULL REFERENCES preclin.drug,
    moiety_id       integer NOT NULL REFERENCES preclin.moiety,
    role            text NOT NULL CHECK (role IN ('investigational', 'background')),
    biosimilar_of   text,
    llm_decision_id bigint NOT NULL REFERENCES pv_evidence.llm_decision,
    PRIMARY KEY (drug_id, moiety_id)
);
CREATE INDEX IF NOT EXISTS drug_moiety_moiety_idx ON preclin.drug_moiety (moiety_id);

ALTER TABLE preclin.drug
    ADD COLUMN IF NOT EXISTS entity_kind text CHECK (entity_kind IN
        ('drug', 'combination', 'placebo_or_vehicle', 'vaccine', 'non_drug', 'unclear')),
    ADD COLUMN IF NOT EXISTS moiety_decision_id bigint REFERENCES pv_evidence.llm_decision;

COMMIT;
