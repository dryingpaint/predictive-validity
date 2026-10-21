-- Whether a trial can mark its program's entry into the trial's phase. A
-- trial without a disease (healthy volunteers) or with a broader condition
-- ("solid tumors") is shared by several of the entity's programs; it marks
-- entry only for programs already under way when it started and for the
-- program(s) begun next after it (the lead indication at the time). Later
-- indication expansions enter at their own first trial.

BEGIN;
SET LOCAL lock_timeout = '10s';
ALTER TABLE preclin.dev_program_trial ADD COLUMN IF NOT EXISTS marks_entry boolean NOT NULL DEFAULT true;
COMMIT;
