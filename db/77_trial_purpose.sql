-- What each industry trial contributes to development (pipeline.programs
-- purposes): developing the drug for its listed indication(s), a basket across
-- several indications, early development (first-in-human or clinical
-- pharmacology before an indication is chosen), or support of an existing
-- product (bioequivalence, formulation bridging, food effect, interactions,
-- generic or biosimilar comparative PK). Product-support trials are not part
-- of any development program; basket trials are shared like healthy-volunteer
-- trials (dev_program_trial.attach = 'basket').

BEGIN;
SET LOCAL lock_timeout = '3s';
CREATE TABLE IF NOT EXISTS preclin.trial_purpose (
    nct_id                 text PRIMARY KEY REFERENCES preclin.ctgov_study,
    purpose                text NOT NULL CHECK (purpose IN ('indication_development', 'multi_indication',
                                                            'early_development', 'product_support', 'other')),
    development_conditions text[] NOT NULL,
    llm_decision_id        bigint NOT NULL REFERENCES pv_evidence.llm_decision
);
ALTER TABLE preclin.dev_program_trial DROP CONSTRAINT IF EXISTS dev_program_trial_attach_check;
ALTER TABLE preclin.dev_program_trial ADD CONSTRAINT dev_program_trial_attach_check
    CHECK (attach IN ('disease', 'broader_condition', 'no_disease', 'non_disease_condition', 'basket'));
COMMIT;
