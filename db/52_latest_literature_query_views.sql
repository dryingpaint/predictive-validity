-- Active literature views expose only the latest complete execution of each
-- stable query key. Historical runs and observations remain immutable for
-- replay audits, but exact reruns do not multiply the analytical corpus.

BEGIN;

CREATE OR REPLACE VIEW pv_evidence.v_active_asset_indication_literature_candidate AS
WITH latest_query AS (
  SELECT query.retrieval_query_id,
         row_number() OVER (
           PARTITION BY query.query_kind,query.query_key
           ORDER BY run.started_at DESC,query.retrieval_query_id DESC
         ) AS query_rank
  FROM pv_source.retrieval_query query
  JOIN pv_source.acquisition_run run USING (acquisition_run_id)
  WHERE query.query_kind='asset_indication_v2'
    AND query.stream_status='completed'
    AND run.status='completed'
)
SELECT candidate.document_relation_candidate_id,
       candidate.scholarly_work_id,
       candidate.asset_entity_id,
       candidate.phenotype_entity_id,
       observation.retrieval_query_id,
       observation.provider_rank
FROM latest_query latest
JOIN pv_evidence.document_relation_candidate_observation observation
  USING (retrieval_query_id)
JOIN pv_evidence.document_relation_candidate candidate
  USING (document_relation_candidate_id)
WHERE latest.query_rank=1
  AND candidate.candidate_kind='asset_indication_v2';

CREATE OR REPLACE VIEW pv_evidence.v_active_effective_target_literature_candidate AS
WITH latest_query AS (
  SELECT query.retrieval_query_id,
         row_number() OVER (
           PARTITION BY query.query_kind,query.query_key
           ORDER BY run.started_at DESC,query.retrieval_query_id DESC
         ) AS query_rank
  FROM pv_source.retrieval_query query
  JOIN pv_source.acquisition_run run USING (acquisition_run_id)
  WHERE query.query_kind='effective_target_only_v1'
    AND query.stream_status='completed'
    AND run.status='completed'
)
SELECT candidate.document_relation_candidate_id,
       candidate.scholarly_work_id,
       candidate.target_entity_id,
       observation.retrieval_query_id,
       observation.provider_rank,
       coalesce(
         array_agg(DISTINCT context.context_name)
           FILTER (WHERE mapping.use_role='search_term'),
         '{}'::text[]
       ) AS effective_contexts,
       coalesce(
         array_agg(DISTINCT context.context_name)
           FILTER (WHERE mapping.use_role='provenance_only'),
         '{}'::text[]
       ) AS provenance_only_contexts
FROM latest_query latest
JOIN pv_evidence.document_relation_candidate_observation observation
  USING (retrieval_query_id)
JOIN pv_evidence.document_relation_candidate candidate
  USING (document_relation_candidate_id)
LEFT JOIN pv_source.retrieval_query_target_context mapping
  USING (retrieval_query_id)
LEFT JOIN pv_evidence.asset_target_context_assertion context
  USING (asset_target_context_assertion_id)
WHERE latest.query_rank=1
  AND candidate.candidate_kind='effective_target_only_v1'
GROUP BY candidate.document_relation_candidate_id,candidate.scholarly_work_id,
         candidate.target_entity_id,observation.retrieval_query_id,
         observation.provider_rank;

COMMIT;
