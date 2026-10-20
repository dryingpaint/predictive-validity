-- FDA approval of each development program's disease (pipeline.approvals judge).
-- first_approval_date is the action date of the earliest covering approval
-- event; date_basis says when no dated event exists (before_2015: only the
-- current label or a pre-2015 original approval shows it). Programs whose
-- entity has no FDA application have no row.

BEGIN;

-- Fail fast instead of queueing ahead of writers to pv_evidence.llm_decision.
SET LOCAL lock_timeout = '90s';

CREATE TABLE IF NOT EXISTS preclin.dev_program_approval (
    program_id          integer PRIMARY KEY REFERENCES preclin.dev_program ON DELETE CASCADE,
    approved            text NOT NULL CHECK (approved IN ('yes', 'no', 'uncertain')),
    first_approval_date date,
    date_basis          text NOT NULL CHECK (date_basis IN ('dated', 'before_2015', 'undated', 'none')),
    relation            text NOT NULL,
    evidence            text NOT NULL,
    llm_decision_id     bigint NOT NULL REFERENCES pv_evidence.llm_decision
);

COMMIT;
