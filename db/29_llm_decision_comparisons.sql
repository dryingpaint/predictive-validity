-- Persist complete comparisons between optional LLM enrichment runs.
-- A separate table is required because a removed subject has no decision row
-- in the current run on which to store its change state.

BEGIN;

CREATE TABLE pv_evidence.llm_decision_comparison (
  current_run_id       UUID NOT NULL
    REFERENCES pv_evidence.llm_decision_run(decision_run_id),
  compare_to_run_id    UUID NOT NULL
    REFERENCES pv_evidence.llm_decision_run(decision_run_id),
  task                 TEXT NOT NULL,
  subject_type         TEXT NOT NULL,
  subject_key          TEXT NOT NULL,
  change_status        TEXT NOT NULL CHECK (
    change_status IN ('added', 'removed', 'changed', 'unchanged')
  ),
  current_decision_id  BIGINT REFERENCES pv_evidence.llm_decision(llm_decision_id),
  prior_decision_id    BIGINT REFERENCES pv_evidence.llm_decision(llm_decision_id),
  field_diff           JSONB NOT NULL DEFAULT '[]'::jsonb,
  compared_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (
    current_run_id, compare_to_run_id, task, subject_type, subject_key
  ),
  CHECK (
    (change_status = 'added' AND current_decision_id IS NOT NULL AND prior_decision_id IS NULL) OR
    (change_status = 'removed' AND current_decision_id IS NULL AND prior_decision_id IS NOT NULL) OR
    (change_status IN ('changed', 'unchanged') AND
      current_decision_id IS NOT NULL AND prior_decision_id IS NOT NULL)
  )
);
CREATE INDEX pv_llm_decision_comparison_status_idx
  ON pv_evidence.llm_decision_comparison
    (current_run_id, compare_to_run_id, change_status);

COMMIT;
