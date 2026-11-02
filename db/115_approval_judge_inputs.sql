-- Inputs the approval judge (pipeline.approvals) reads: the document type of each FDA action document,
-- so an efficacy supplement with no letter is read from its label or review, and each trial's
-- eligibility criteria, so a tissue-agnostic biomarker approval is judged against the trials' enrolment.

BEGIN;
SET LOCAL lock_timeout = '3s';
ALTER TABLE preclin.fda_submission_letter
    ADD COLUMN doc_type text NOT NULL DEFAULT 'letter' CHECK (doc_type IN ('letter', 'label', 'review'));
COMMENT ON COLUMN preclin.fda_submission_letter.doc_type IS
    'letter: the action''s approval letter. label or review: for an efficacy supplement Drugs@FDA posts no letter for, the label PDF posted for the supplement, else its review PDF (pipeline.fda.action_documents).';
ALTER TABLE preclin.ctgov_study ADD COLUMN eligibility_criteria text;
COMMENT ON COLUMN preclin.ctgov_study.eligibility_criteria IS
    'The registered eligibility criteria text (eligibilityModule.eligibilityCriteria), inclusion then exclusion criteria.';
COMMIT;
