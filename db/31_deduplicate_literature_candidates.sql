-- Separate canonical literature candidates from run-specific query observations.

BEGIN;

ALTER TABLE pv_evidence.document_relation_candidate
  RENAME TO document_relation_candidate_legacy;

ALTER INDEX pv_evidence.pv_document_relation_candidate_target_idx
  RENAME TO pv_document_relation_candidate_target_idx_legacy;

CREATE TABLE pv_evidence.document_relation_candidate (
  document_relation_candidate_id BIGSERIAL PRIMARY KEY,
  scholarly_work_id        BIGINT NOT NULL
    REFERENCES pv_source.scholarly_work(scholarly_work_id),
  target_entity_id         UUID REFERENCES pv_core.target(entity_id),
  phenotype_entity_id      UUID REFERENCES pv_core.phenotype(entity_id),
  mechanism_entity_id      UUID REFERENCES pv_core.entity(entity_id),
  candidate_kind           TEXT NOT NULL CHECK (
    candidate_kind IN (
      'target_wide_phenotype', 'target_phenotype',
      'mechanism_wide_phenotype', 'mechanism_phenotype'
    )
  ),
  disposition              TEXT NOT NULL DEFAULT 'unreviewed' CHECK (
    disposition IN ('unreviewed', 'supports', 'does_not_support', 'ambiguous', 'duplicate')
  ),
  created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (target_entity_id IS NOT NULL OR mechanism_entity_id IS NOT NULL),
  CONSTRAINT pv_document_relation_candidate_identity_unique
    UNIQUE NULLS NOT DISTINCT (
      scholarly_work_id, target_entity_id, phenotype_entity_id,
      mechanism_entity_id, candidate_kind
    )
);

INSERT INTO pv_evidence.document_relation_candidate
  (scholarly_work_id,target_entity_id,phenotype_entity_id,
   mechanism_entity_id,candidate_kind,disposition,created_at)
SELECT DISTINCT ON (
         scholarly_work_id,target_entity_id,phenotype_entity_id,
         mechanism_entity_id,candidate_kind
       )
       scholarly_work_id,target_entity_id,phenotype_entity_id,
       mechanism_entity_id,candidate_kind,disposition,created_at
FROM pv_evidence.document_relation_candidate_legacy
ORDER BY scholarly_work_id,target_entity_id,phenotype_entity_id,
         mechanism_entity_id,candidate_kind,created_at;

CREATE TABLE pv_evidence.document_relation_candidate_observation (
  retrieval_query_id       BIGINT NOT NULL
    REFERENCES pv_source.retrieval_query(retrieval_query_id),
  document_relation_candidate_id BIGINT NOT NULL
    REFERENCES pv_evidence.document_relation_candidate(document_relation_candidate_id),
  provider_rank            INTEGER NOT NULL CHECK (provider_rank >= 0),
  observed_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (retrieval_query_id, document_relation_candidate_id)
);

INSERT INTO pv_evidence.document_relation_candidate_observation
  (retrieval_query_id,document_relation_candidate_id,provider_rank,observed_at)
SELECT legacy.retrieval_query_id,
       canonical.document_relation_candidate_id,
       legacy.provider_rank,
       legacy.created_at
FROM pv_evidence.document_relation_candidate_legacy legacy
JOIN pv_evidence.document_relation_candidate canonical
  ON canonical.scholarly_work_id=legacy.scholarly_work_id
 AND canonical.target_entity_id IS NOT DISTINCT FROM legacy.target_entity_id
 AND canonical.phenotype_entity_id IS NOT DISTINCT FROM legacy.phenotype_entity_id
 AND canonical.mechanism_entity_id IS NOT DISTINCT FROM legacy.mechanism_entity_id
 AND canonical.candidate_kind=legacy.candidate_kind;

DROP TABLE pv_evidence.document_relation_candidate_legacy;

CREATE INDEX pv_document_relation_candidate_target_idx
  ON pv_evidence.document_relation_candidate
    (target_entity_id,phenotype_entity_id,disposition);
CREATE INDEX pv_document_relation_candidate_observation_candidate_idx
  ON pv_evidence.document_relation_candidate_observation
    (document_relation_candidate_id,retrieval_query_id);

COMMIT;
