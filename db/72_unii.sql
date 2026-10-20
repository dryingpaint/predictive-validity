-- FDA Global Substance Registration System lists (pipeline.unii): every
-- registered substance (UNII) and all its registered names: official, common,
-- code, systematic and brand. preclin.moiety gains the UNII of its active
-- substance (pipeline.drugs unii) and aliases, the other names of entities
-- merged into it because they resolved to the same substance.

BEGIN;
SET LOCAL lock_timeout = '90s';

CREATE TABLE IF NOT EXISTS preclin.unii_substance (
    unii              text PRIMARY KEY,
    display_name      text NOT NULL,
    substance_type    text,
    ingredient_type   text,
    inn_id            text,
    usan_id           text,
    rxcui             text,
    pubchem_cid       text,
    inchikey          text,
    source_release_id bigint NOT NULL REFERENCES preclin.evidence_source_release
);

CREATE TABLE IF NOT EXISTS preclin.unii_name (
    unii      text NOT NULL REFERENCES preclin.unii_substance,
    name      text NOT NULL,
    name_type text NOT NULL CHECK (name_type IN ('of', 'cn', 'cd', 'sys', 'bn', 'mn')),
    name_key  text NOT NULL,
    PRIMARY KEY (unii, name, name_type)
);
CREATE INDEX IF NOT EXISTS unii_name_key_idx ON preclin.unii_name (name_key);

ALTER TABLE preclin.moiety
    DROP COLUMN IF EXISTS chembl_id,
    ADD COLUMN IF NOT EXISTS unii text REFERENCES preclin.unii_substance,
    ADD COLUMN IF NOT EXISTS unii_decision_id bigint REFERENCES pv_evidence.llm_decision,
    ADD COLUMN IF NOT EXISTS aliases text[] NOT NULL DEFAULT '{}';

COMMIT;
