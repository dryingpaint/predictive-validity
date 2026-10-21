-- Modality of each molecular entity (pipeline.drugs modality) and BIO 2021
-- disease area of each program disease (pipeline.indications areas), each
-- set by the referenced LLM decision. These replace preclin.drug.modality,
-- preclin.drug_bio_class and preclin.indication_bio_class for every analysis
-- built on preclin.dev_program.

BEGIN;

SET LOCAL lock_timeout = '90s';

ALTER TABLE preclin.moiety
    ADD COLUMN IF NOT EXISTS modality text,
    ADD COLUMN IF NOT EXISTS modality_decision_id bigint REFERENCES pv_evidence.llm_decision;

CREATE TABLE IF NOT EXISTS preclin.mondo_bio_area (
    mondo_id        text PRIMARY KEY,
    bio_area        text NOT NULL,
    llm_decision_id bigint NOT NULL REFERENCES pv_evidence.llm_decision
);

COMMIT;
