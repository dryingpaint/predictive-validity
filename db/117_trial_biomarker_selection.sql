-- Whether a trial restricts enrolment to patients selected by a molecular biomarker
-- (pipeline.outcomes biomarkers): an adjustment for patient selection in the evidence analyses.

BEGIN;
SET LOCAL lock_timeout = '3s';
CREATE TABLE preclin.trial_biomarker_selection (
    nct_id text PRIMARY KEY REFERENCES preclin.ctgov_study(nct_id),
    selected boolean NOT NULL,
    biomarker text,
    kind text CHECK (kind IN ('germline_variant', 'somatic_mutation', 'expression', 'signature', 'other_molecular')),
    quote text,
    llm_decision_id bigint NOT NULL REFERENCES pv_evidence.llm_decision(llm_decision_id),
    CHECK (selected = (kind IS NOT NULL))
);
COMMENT ON TABLE preclin.trial_biomarker_selection IS
    'Industry trials starting a phase of a development program from 2008 to 2019: whether eligibility requires a molecular biomarker (a germline variant, somatic mutation, protein or gene expression, gene signature or other measured molecular marker). Clinical diagnoses, disease stage and ordinary laboratory thresholds do not count. Judged by an LLM from the title, conditions, summary and eligibility criteria.';
COMMENT ON COLUMN preclin.trial_biomarker_selection.selected IS 'Enrolment is restricted to patients with the biomarker.';
COMMENT ON COLUMN preclin.trial_biomarker_selection.biomarker IS 'The biomarker as the registry record writes it; null when not selected.';
COMMENT ON COLUMN preclin.trial_biomarker_selection.kind IS 'germline_variant, somatic_mutation, expression (protein or RNA level, including receptor status), signature (multi-gene score) or other_molecular; null when not selected.';
COMMENT ON COLUMN preclin.trial_biomarker_selection.quote IS 'The eligibility text that states the requirement; null when not selected.';
COMMIT;
