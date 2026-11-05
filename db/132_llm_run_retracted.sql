-- A completed LLM run can be withdrawn (pipeline.llm retract): its decisions stay as the record, and no later run
-- reuses them, so each of its subjects falls back to the decision it had before.

BEGIN;
SET LOCAL lock_timeout = '3s';
ALTER TABLE pv_evidence.llm_decision_run DROP CONSTRAINT llm_decision_run_status_check;
ALTER TABLE pv_evidence.llm_decision_run ADD CONSTRAINT llm_decision_run_status_check
    CHECK (status IN ('running', 'completed', 'failed', 'retracted'));
COMMENT ON COLUMN pv_evidence.llm_decision_run.status IS
    'running, completed, failed, or retracted: a completed run withdrawn by pipeline.llm retract, whose decisions no later run reuses or reads as latest; parameters.retracted gives the reason and time.';
COMMIT;
