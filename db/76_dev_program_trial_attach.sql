-- A trial whose conditions are symptoms, procedures or other non-disease
-- conditions without a MONDO term (e.g. "postoperative pain", "contraception")
-- attaches only to its entity's condition-unspecified program, never to the
-- entity's disease programs: a Phase 3 in low back pain is not progress of the
-- same drug's osteoarthritis program.

BEGIN;
SET LOCAL lock_timeout = '10s';
ALTER TABLE preclin.dev_program_trial DROP CONSTRAINT IF EXISTS dev_program_trial_attach_check;
ALTER TABLE preclin.dev_program_trial ADD CONSTRAINT dev_program_trial_attach_check
    CHECK (attach IN ('disease', 'broader_condition', 'no_disease', 'non_disease_condition'));
COMMIT;
