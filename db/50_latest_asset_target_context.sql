-- Expose one current mechanism-context decision per asset while retaining all
-- immutable LLM runs and projections for reproducibility and change audits.

BEGIN;

CREATE VIEW pv_evidence.v_latest_asset_target_context AS
WITH ranked_decision AS (
  SELECT decision.llm_decision_id,
         decision.subject_key,
         row_number() OVER (
           PARTITION BY decision.task,decision.subject_type,decision.subject_key
           ORDER BY run.started_at DESC,decision.llm_decision_id DESC
         ) AS decision_rank
  FROM pv_evidence.llm_decision decision
  JOIN pv_evidence.llm_decision_run run
    ON run.decision_run_id=decision.decision_run_id
  WHERE decision.task='chembl_mechanism_context_extraction'
    AND decision.subject_type='asset'
    AND decision.validation_status='validated'
    AND run.status='completed'
)
SELECT context.*
FROM pv_evidence.asset_target_context_assertion context
JOIN ranked_decision decision
  ON decision.llm_decision_id=context.llm_decision_id
 AND decision.decision_rank=1;

COMMIT;
