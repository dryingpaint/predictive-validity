-- Asset-linked preclinical document candidates and source-grounded experiment
-- projections. Candidate retrieval is raw ingestion; experiment extraction is
-- a later, independently versioned enrichment over retained documents.

BEGIN;

ALTER TABLE pv_evidence.document_relation_candidate
  DROP CONSTRAINT document_relation_candidate_candidate_kind_check1;
ALTER TABLE pv_evidence.document_relation_candidate
  ADD COLUMN asset_entity_id UUID REFERENCES pv_core.asset(entity_id);
ALTER TABLE pv_evidence.document_relation_candidate
  ADD CONSTRAINT document_relation_candidate_candidate_kind_check CHECK (
    candidate_kind IN (
      'target_wide_phenotype', 'target_phenotype',
      'mechanism_wide_phenotype', 'mechanism_phenotype',
      'asset_preclinical_wide', 'asset_indication_preclinical',
      'target_indication_preclinical'
    )
  );
ALTER TABLE pv_evidence.document_relation_candidate
  DROP CONSTRAINT document_relation_candidate_check1;
ALTER TABLE pv_evidence.document_relation_candidate
  ADD CONSTRAINT document_relation_candidate_subject_check CHECK (
    target_entity_id IS NOT NULL OR mechanism_entity_id IS NOT NULL
    OR asset_entity_id IS NOT NULL
  );
ALTER TABLE pv_evidence.document_relation_candidate
  DROP CONSTRAINT pv_document_relation_candidate_identity_unique;
ALTER TABLE pv_evidence.document_relation_candidate
  ADD CONSTRAINT pv_document_relation_candidate_identity_unique
  UNIQUE NULLS NOT DISTINCT (
    scholarly_work_id, target_entity_id, phenotype_entity_id,
    mechanism_entity_id, asset_entity_id, candidate_kind
  );
CREATE INDEX pv_document_relation_candidate_asset_idx
  ON pv_evidence.document_relation_candidate
    (asset_entity_id,phenotype_entity_id,disposition);

CREATE TABLE pv_evidence.preclinical_experiment (
  preclinical_experiment_id BIGSERIAL PRIMARY KEY,
  asset_entity_id           UUID NOT NULL REFERENCES pv_core.asset(entity_id),
  scholarly_work_id         BIGINT NOT NULL
    REFERENCES pv_source.scholarly_work(scholarly_work_id),
  source_record_version_id  BIGINT NOT NULL
    REFERENCES pv_source.source_record_version(source_record_version_id),
  experiment_key            TEXT NOT NULL,
  model_system_literal      TEXT,
  assay_literal             TEXT,
  endpoint_literal          TEXT,
  intervention_literal      TEXT,
  comparator_literal        TEXT,
  reported_result_class     TEXT NOT NULL CHECK (
    reported_result_class IN (
      'positive', 'negative', 'null', 'mixed', 'not_reported', 'unclear'
    )
  ),
  reported_criterion_literal TEXT,
  author_conclusion_literal TEXT,
  extraction_method         TEXT NOT NULL,
  extraction_run_id         UUID REFERENCES pv_evidence.llm_decision_run(decision_run_id),
  detail                    JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at                TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (btrim(experiment_key) <> ''),
  CHECK (btrim(extraction_method) <> ''),
  UNIQUE (asset_entity_id,scholarly_work_id,experiment_key,extraction_method)
);

CREATE TABLE pv_evidence.preclinical_experiment_evidence (
  preclinical_experiment_id BIGINT NOT NULL
    REFERENCES pv_evidence.preclinical_experiment(preclinical_experiment_id)
    ON DELETE CASCADE,
  source_path               TEXT NOT NULL,
  support_quote             TEXT NOT NULL,
  support_start             INTEGER,
  support_end               INTEGER,
  evidence_role             TEXT NOT NULL CHECK (
    evidence_role IN (
      'model', 'assay', 'endpoint', 'intervention', 'comparator',
      'result', 'criterion', 'author_conclusion'
    )
  ),
  created_at                TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (btrim(source_path) <> ''),
  CHECK (btrim(support_quote) <> ''),
  CHECK (
    (support_start IS NULL AND support_end IS NULL)
    OR (support_start >= 0 AND support_end > support_start)
  ),
  PRIMARY KEY (preclinical_experiment_id,source_path,evidence_role)
);

COMMIT;
