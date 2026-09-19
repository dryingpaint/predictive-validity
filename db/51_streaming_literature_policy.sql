-- Activate the retrieval policy that separates provider discovery from later
-- evidence classification, and make large Europe PMC inventories page-streamed.
--
-- Provider queries under this policy are only:
--   * verified asset aliases AND one normalized indication; and
--   * one effective human target context, without phenotype vocabulary.
-- Target--indication candidates are a local lexical projection of the retained
-- target-only corpus, never a third provider query.

BEGIN;

CREATE TABLE pv_core.literature_retrieval_policy (
  literature_policy_version TEXT PRIMARY KEY,
  definition                JSONB NOT NULL,
  is_active                 BOOLEAN NOT NULL DEFAULT false,
  created_at                TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (btrim(literature_policy_version) <> ''),
  CHECK (jsonb_typeof(definition) = 'object')
);

CREATE UNIQUE INDEX pv_one_active_literature_policy_idx
  ON pv_core.literature_retrieval_policy (is_active)
  WHERE is_active;

INSERT INTO pv_core.literature_retrieval_policy
  (literature_policy_version,definition,is_active)
VALUES (
  'pv_literature_v2',
  jsonb_build_object(
    'provider_queries', jsonb_build_array(
      'asset_aliases AND normalized_indication_aliases',
      'effective_human_target_only'
    ),
    'target_indication', 'local_projection_of_target_only_corpus',
    'preclinical_vocabulary_in_retrieval', false,
    'ranking', 'Europe PMC CITED desc retained as provider_rank only',
    'storage', 'all metadata and abstracts, raw provider pages, page-level progress',
    'broad_target_rule',
      'use a verified self-contained subfamily or isoform instead of its broad ChEMBL parent; otherwise qualify the parent with verified context',
    'classification', 'downstream_not_retrieval'
  ),
  true
);

ALTER TABLE pv_source.retrieval_query
  ADD COLUMN stream_status TEXT NOT NULL DEFAULT 'completed' CHECK (
    stream_status IN ('running','completed','truncated','failed')
  ),
  ADD COLUMN next_cursor TEXT,
  ADD COLUMN pages_committed INTEGER NOT NULL DEFAULT 0 CHECK (pages_committed >= 0),
  ADD COLUMN results_committed INTEGER NOT NULL DEFAULT 0 CHECK (results_committed >= 0),
  ADD COLUMN stream_completed_at TIMESTAMPTZ;

COMMENT ON COLUMN pv_source.retrieval_query.result_manifest IS
  'For streamed queries, an ordered page manifest. Exact result identities remain reconstructable from immutable raw pages and retrieval_disposition rows.';

CREATE TABLE pv_source.retrieval_query_target_context (
  retrieval_query_id BIGINT NOT NULL
    REFERENCES pv_source.retrieval_query(retrieval_query_id),
  asset_target_context_assertion_id BIGINT NOT NULL
    REFERENCES pv_evidence.asset_target_context_assertion(asset_target_context_assertion_id),
  use_role TEXT NOT NULL CHECK (use_role IN ('search_term','provenance_only')),
  PRIMARY KEY (retrieval_query_id,asset_target_context_assertion_id)
);

ALTER TABLE pv_evidence.document_relation_candidate
  DROP CONSTRAINT document_relation_candidate_candidate_kind_check;
ALTER TABLE pv_evidence.document_relation_candidate
  ADD CONSTRAINT document_relation_candidate_candidate_kind_check CHECK (
    candidate_kind IN (
      'target_wide_phenotype', 'target_phenotype',
      'mechanism_wide_phenotype', 'mechanism_phenotype',
      'asset_preclinical_wide', 'asset_indication_preclinical',
      'target_indication_preclinical', 'asset_mention',
      'asset_indication_v2', 'effective_target_only_v1'
    )
  );

ALTER TABLE pv_source.literature_work_item
  DROP CONSTRAINT literature_work_item_work_kind_check;
ALTER TABLE pv_source.literature_work_item
  ADD CONSTRAINT literature_work_item_work_kind_check CHECK (
    work_kind IN (
      'target_phenotype','asset_preclinical','asset_mention',
      'asset_indication','effective_target'
    )
  );
ALTER TABLE pv_source.literature_work_item
  DROP CONSTRAINT literature_work_item_subject_check;
ALTER TABLE pv_source.literature_work_item
  ADD CONSTRAINT literature_work_item_subject_check CHECK (
    (work_kind='target_phenotype' AND target_entity_id IS NOT NULL
      AND phenotype_entity_id IS NOT NULL AND asset_entity_id IS NULL)
    OR
    (work_kind IN ('asset_preclinical','asset_mention')
      AND asset_entity_id IS NOT NULL
      AND target_entity_id IS NULL AND phenotype_entity_id IS NULL)
    OR
    (work_kind='asset_indication' AND asset_entity_id IS NOT NULL
      AND phenotype_entity_id IS NOT NULL AND target_entity_id IS NULL)
    OR
    (work_kind='effective_target' AND target_entity_id IS NOT NULL
      AND phenotype_entity_id IS NULL AND asset_entity_id IS NULL)
  );

CREATE VIEW pv_evidence.v_active_asset_indication_literature_candidate AS
SELECT candidate.document_relation_candidate_id,
       candidate.scholarly_work_id,
       candidate.asset_entity_id,
       candidate.phenotype_entity_id,
       observation.retrieval_query_id,
       observation.provider_rank
FROM pv_evidence.document_relation_candidate candidate
JOIN pv_evidence.document_relation_candidate_observation observation
  USING (document_relation_candidate_id)
JOIN pv_source.retrieval_query query
  USING (retrieval_query_id)
JOIN pv_source.acquisition_run run
  USING (acquisition_run_id)
WHERE candidate.candidate_kind='asset_indication_v2'
  AND query.stream_status='completed'
  AND run.status='completed';

CREATE VIEW pv_evidence.v_active_effective_target_literature_candidate AS
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
FROM pv_evidence.document_relation_candidate candidate
JOIN pv_evidence.document_relation_candidate_observation observation
  USING (document_relation_candidate_id)
JOIN pv_source.retrieval_query query
  USING (retrieval_query_id)
JOIN pv_source.acquisition_run run
  USING (acquisition_run_id)
LEFT JOIN pv_source.retrieval_query_target_context mapping
  USING (retrieval_query_id)
LEFT JOIN pv_evidence.asset_target_context_assertion context
  USING (asset_target_context_assertion_id)
WHERE candidate.candidate_kind='effective_target_only_v1'
  AND query.stream_status='completed'
  AND run.status='completed'
GROUP BY candidate.document_relation_candidate_id,candidate.scholarly_work_id,
         candidate.target_entity_id,observation.retrieval_query_id,
         observation.provider_rank;

CREATE VIEW pv_evidence.v_target_indication_literature_candidate AS
WITH target_indications AS (
  SELECT DISTINCT target_entity_id,phenotype_entity_id
  FROM pv_core.v_target_phenotype_literature_scope
  WHERE policy_version='human_therapeutics_v2'
), phenotype_terms AS (
  SELECT phenotype.entity_id AS phenotype_entity_id,
         phenotype.preferred_name AS term
  FROM pv_core.phenotype phenotype
  UNION
  SELECT alias.entity_id,alias.alias_text
  FROM pv_core.entity_alias alias
  WHERE alias.entity_type='phenotype'
    AND alias.alias_kind IN ('preferred_label','exact_synonym','related_synonym','query_label')
    AND alias.is_ambiguous=false
), matches AS (
  SELECT candidate.document_relation_candidate_id,
         candidate.scholarly_work_id,
         candidate.target_entity_id,
         scoped.phenotype_entity_id,
         candidate.retrieval_query_id,
         candidate.provider_rank,
         term.term AS matched_phenotype_term
  FROM pv_evidence.v_active_effective_target_literature_candidate candidate
  JOIN target_indications scoped
    ON scoped.target_entity_id=candidate.target_entity_id
  JOIN pv_source.scholarly_work work
    ON work.scholarly_work_id=candidate.scholarly_work_id
  JOIN phenotype_terms term
    ON term.phenotype_entity_id=scoped.phenotype_entity_id
  WHERE btrim(term.term) <> ''
    AND to_tsvector('simple',coalesce(work.title,'') || ' ' || coalesce(work.abstract_text,''))
        @@ phraseto_tsquery('simple',term.term)
)
SELECT document_relation_candidate_id,scholarly_work_id,target_entity_id,
       phenotype_entity_id,retrieval_query_id,provider_rank,
       array_agg(DISTINCT matched_phenotype_term ORDER BY matched_phenotype_term)
         AS matched_phenotype_terms
FROM matches
GROUP BY document_relation_candidate_id,scholarly_work_id,target_entity_id,
         phenotype_entity_id,retrieval_query_id,provider_rank;

COMMIT;
