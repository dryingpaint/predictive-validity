-- MONDO disease for each indication, chosen by the referenced LLM decision
-- from OLS4 candidates (pipeline.indications). mondo_id names the core disease
-- without population qualifiers; indication_kind separates diseases from
-- symptoms, procedures and healthy-volunteer studies.

BEGIN;

ALTER TABLE preclin.indication
    ADD COLUMN IF NOT EXISTS mondo_label       text,
    ADD COLUMN IF NOT EXISTS indication_kind   text CHECK (indication_kind IN
        ('disease', 'symptom_or_sign', 'procedure_or_state', 'healthy_volunteers', 'other')),
    ADD COLUMN IF NOT EXISTS mondo_decision_id bigint REFERENCES pv_evidence.llm_decision;

CREATE INDEX IF NOT EXISTS idx_ind_mondo ON preclin.indication (mondo_id);

COMMENT ON COLUMN preclin.indication.mondo_id IS
  'MONDO term for the core disease (no line/stage/biomarker/age qualifiers); set by pipeline.indications from OLS4 candidates.';

COMMIT;
