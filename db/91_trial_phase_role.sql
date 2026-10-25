-- Whether a trial can mark its programs' entry into its phase: an extension study that enrolls only
-- earlier trials' participants cannot, nor can a trial for a drug that enters only in a later
-- sub-study or extension period of another drug's trial (pipeline.programs build, LLM-judged for
-- phase-start candidates).

BEGIN;
SET LOCAL lock_timeout = '3s';
CREATE TABLE IF NOT EXISTS preclin.trial_phase_role (
    nct_id                text PRIMARY KEY REFERENCES preclin.ctgov_study,
    extension             boolean NOT NULL,
    main_period_moieties  integer[] NOT NULL,
    llm_decision_id       bigint NOT NULL REFERENCES pv_evidence.llm_decision
);
COMMENT ON TABLE preclin.trial_phase_role IS
    'Phase-start candidates judged by an LLM (pipeline.programs build): whether the trial is an extension of '
    'earlier trials, and which of its investigational entities its main period tests';
ALTER TABLE preclin.dev_program_trial ADD COLUMN IF NOT EXISTS starts_phase boolean NOT NULL DEFAULT true;
COMMENT ON COLUMN preclin.dev_program_trial.starts_phase IS
    'Whether the trial can mark the program''s entry into, or advancement to, its phase: false for an extension '
    'study, or when the program''s entity enters the trial only after its main period (preclin.trial_phase_role)';
COMMIT;
