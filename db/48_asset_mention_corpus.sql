-- Replace assay-vocabulary-bounded asset retrieval with an unclassified
-- title/abstract asset-mention corpus.  Historical preclinical-query rows are
-- retained with their original candidate kinds and work items.

BEGIN;

ALTER TABLE pv_evidence.document_relation_candidate
  DROP CONSTRAINT document_relation_candidate_candidate_kind_check;
ALTER TABLE pv_evidence.document_relation_candidate
  ADD CONSTRAINT document_relation_candidate_candidate_kind_check CHECK (
    candidate_kind IN (
      'target_wide_phenotype', 'target_phenotype',
      'mechanism_wide_phenotype', 'mechanism_phenotype',
      'asset_preclinical_wide', 'asset_indication_preclinical',
      'target_indication_preclinical', 'asset_mention'
    )
  );

ALTER TABLE pv_source.literature_work_item
  DROP CONSTRAINT literature_work_item_work_kind_check;
ALTER TABLE pv_source.literature_work_item
  ADD CONSTRAINT literature_work_item_work_kind_check CHECK (
    work_kind IN ('target_phenotype','asset_preclinical','asset_mention')
  );
ALTER TABLE pv_source.literature_work_item
  DROP CONSTRAINT literature_work_item_check;
ALTER TABLE pv_source.literature_work_item
  ADD CONSTRAINT literature_work_item_subject_check CHECK (
    (work_kind='target_phenotype' AND target_entity_id IS NOT NULL
      AND phenotype_entity_id IS NOT NULL AND asset_entity_id IS NULL)
    OR
    (work_kind IN ('asset_preclinical','asset_mention')
      AND asset_entity_id IS NOT NULL
      AND target_entity_id IS NULL AND phenotype_entity_id IS NULL)
  );

COMMIT;
