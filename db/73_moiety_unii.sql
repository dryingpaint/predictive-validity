-- Each molecular entity's FDA UNII substance (pipeline.drugs unii) and its
-- aliases: names of entities merged into it because they resolved to the same
-- substance. chembl_id was never populated; UNII is the substance identifier.

BEGIN;
SET LOCAL lock_timeout = '3s';
ALTER TABLE preclin.moiety
    DROP COLUMN IF EXISTS chembl_id,
    ADD COLUMN IF NOT EXISTS unii text REFERENCES preclin.unii_substance,
    ADD COLUMN IF NOT EXISTS unii_decision_id bigint REFERENCES pv_evidence.llm_decision,
    ADD COLUMN IF NOT EXISTS aliases text[] NOT NULL DEFAULT '{}';
COMMIT;
