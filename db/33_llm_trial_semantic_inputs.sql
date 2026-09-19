-- Retain the exact per-subject packet and provider audit metadata for replayable
-- LLM semantic-extraction runs.

BEGIN;

ALTER TABLE pv_evidence.llm_decision
  ADD COLUMN input_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN provider_request_id TEXT,
  ADD COLUMN model_parameters JSONB NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN usage JSONB NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN validation_status TEXT NOT NULL DEFAULT 'validated' CHECK (
    validation_status IN ('validated', 'invalid')
  ),
  ADD COLUMN validation_detail JSONB NOT NULL DEFAULT '[]'::jsonb;

COMMIT;
