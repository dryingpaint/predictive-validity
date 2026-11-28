-- #198 reads estimates from a network meta-analysis, pooled trials or a whole trial, so an estimate from a subgroup of
-- a trial is flagged and left out of the labels (issue #195).

BEGIN;
SET LOCAL lock_timeout = '3s';
ALTER TABLE preclin.mechanism_response
    ADD COLUMN subgroup boolean NOT NULL DEFAULT false,
    ADD COLUMN subgroup_decision_id bigint REFERENCES pv_evidence.llm_decision;
ALTER TABLE preclin.mechanism_response ALTER COLUMN subgroup DROP DEFAULT;
COMMENT ON COLUMN preclin.mechanism_response.subgroup IS 'True when the estimate comes from a subset of the source''s randomised or analysed population defined by a patient characteristic (a baseline-therapy, disease-type, region or biomarker subgroup, a post hoc stratum), other than the prior advanced therapy the question itself names (advanced-therapy-naive patients, or patients who failed failed_pathway). Decided by an LLM (task response_subgroup) from the row''s regimen, source, endpoint, quote and derivation. report.single_target leaves subgroup estimates out of the labels.';
COMMENT ON COLUMN preclin.mechanism_response.subgroup_decision_id IS 'The decision (task response_subgroup, one per row) behind subgroup.';
COMMIT;
