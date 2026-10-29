-- preclin.stop holds each stop's cause and why its efficacy failed; the efficacy-attribution labels are read
-- from pv_evidence.llm_decision.
BEGIN;
SET LOCAL lock_timeout = '3s';
DROP TABLE IF EXISTS preclin.stop_cause;
DROP TABLE IF EXISTS preclin.efficacy_attribution_search;
DROP TABLE IF EXISTS preclin.efficacy_failure_attribution;
COMMENT ON COLUMN preclin.stop.explanation IS
    'What the row rests on: the efficacy label''s rationale, else the traced source quote or the model''s reasoning for its guess, else the stated reason (or read result) of the trial that gave Section 1 its reason.';
COMMIT;
