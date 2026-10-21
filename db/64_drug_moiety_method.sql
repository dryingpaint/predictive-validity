-- How each intervention name was resolved to its molecular entity: by the
-- referenced LLM decision, or because the name is exactly (case- and
-- punctuation-insensitively) an entity's nonproprietary name or sponsor code.

BEGIN;

SET LOCAL lock_timeout = '90s';

ALTER TABLE preclin.drug_moiety
    ADD COLUMN IF NOT EXISTS method text NOT NULL DEFAULT 'llm' CHECK (method IN ('llm', 'exact_name')),
    ALTER COLUMN llm_decision_id DROP NOT NULL;
ALTER TABLE preclin.drug_moiety
    ADD CONSTRAINT drug_moiety_method_decision CHECK ((method = 'llm') = (llm_decision_id IS NOT NULL));

COMMIT;
