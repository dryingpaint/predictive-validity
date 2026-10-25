-- Explicit asset/target/phenotype relations and candidate literature links.
-- Query matches are candidates; they do not become biological assertions until
-- a source span or structured source row is evaluated.

BEGIN;

ALTER TABLE pv_source.retrieval_query
  ADD COLUMN query_key TEXT;
UPDATE pv_source.retrieval_query
SET query_key = query_kind
WHERE query_key IS NULL;
ALTER TABLE pv_source.retrieval_query
  ALTER COLUMN query_key SET NOT NULL;
ALTER TABLE pv_source.retrieval_query
  DROP CONSTRAINT retrieval_query_acquisition_run_id_query_kind_key;
ALTER TABLE pv_source.retrieval_query
  ADD CONSTRAINT retrieval_query_run_key_unique
  UNIQUE (acquisition_run_id, query_key);

CREATE TABLE pv_core.asset (
  entity_id            UUID PRIMARY KEY REFERENCES pv_core.entity(entity_id),
  asset_kind           TEXT NOT NULL,
  active_moiety_name   TEXT NOT NULL,
  created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE pv_core.target (
  entity_id            UUID PRIMARY KEY REFERENCES pv_core.entity(entity_id),
  hgnc_id              TEXT UNIQUE,
  approved_symbol      TEXT NOT NULL,
  approved_name        TEXT NOT NULL,
  taxon_id             INTEGER NOT NULL DEFAULT 9606,
  uniprot_accession    TEXT,
  created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (approved_symbol, taxon_id)
);

CREATE TABLE pv_core.phenotype (
  entity_id            UUID PRIMARY KEY REFERENCES pv_core.entity(entity_id),
  ontology_namespace   TEXT,
  ontology_identifier  TEXT,
  preferred_name       TEXT NOT NULL,
  phenotype_kind       TEXT NOT NULL,
  created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (ontology_namespace, ontology_identifier)
);

CREATE TABLE pv_core.trial_asset_link (
  nct_id                   TEXT NOT NULL REFERENCES pv_core.trial(nct_id),
  asset_entity_id          UUID NOT NULL REFERENCES pv_core.asset(entity_id),
  intervention_mention_id  BIGINT REFERENCES pv_core.intervention_mention(intervention_mention_id),
  link_role                TEXT NOT NULL CHECK (
    link_role IN ('registered_intervention', 'title_mention', 'background_therapy', 'component')
  ),
  source_record_version_id BIGINT NOT NULL
    REFERENCES pv_source.source_record_version(source_record_version_id),
  resolution_status        TEXT NOT NULL CHECK (
    resolution_status IN ('resolved', 'ambiguous', 'unresolved')
  ),
  resolution_method        TEXT NOT NULL,
  support_text             TEXT,
  created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (nct_id, asset_entity_id, intervention_mention_id, link_role, source_record_version_id)
);

CREATE TABLE pv_evidence.asset_target_assertion (
  asset_target_assertion_id BIGSERIAL PRIMARY KEY,
  asset_entity_id           UUID NOT NULL REFERENCES pv_core.asset(entity_id),
  target_entity_id          UUID NOT NULL REFERENCES pv_core.target(entity_id),
  action_literal            TEXT NOT NULL,
  action_normalized         TEXT,
  role                      TEXT NOT NULL,
  directness                TEXT NOT NULL,
  source_record_version_id  BIGINT NOT NULL
    REFERENCES pv_source.source_record_version(source_record_version_id),
  support_quote             TEXT NOT NULL,
  assertion_date            DATE,
  created_at                TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (
    asset_entity_id, target_entity_id, source_record_version_id,
    action_literal, role
  )
);

CREATE TABLE pv_evidence.asset_mechanism_assertion (
  asset_mechanism_assertion_id BIGSERIAL PRIMARY KEY,
  asset_entity_id           UUID NOT NULL REFERENCES pv_core.asset(entity_id),
  mechanism_entity_id       UUID NOT NULL REFERENCES pv_core.entity(entity_id),
  action_literal            TEXT NOT NULL,
  action_normalized         TEXT,
  source_record_version_id  BIGINT NOT NULL
    REFERENCES pv_source.source_record_version(source_record_version_id),
  support_quote             TEXT NOT NULL,
  assertion_date            DATE,
  created_at                TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (
    asset_entity_id, mechanism_entity_id, source_record_version_id,
    action_literal
  )
);

CREATE TABLE pv_evidence.target_phenotype_assertion (
  target_phenotype_assertion_id BIGSERIAL PRIMARY KEY,
  target_entity_id          UUID NOT NULL REFERENCES pv_core.target(entity_id),
  phenotype_entity_id       UUID NOT NULL REFERENCES pv_core.phenotype(entity_id),
  relationship_literal      TEXT NOT NULL,
  relationship_normalized   TEXT,
  direction                 TEXT,
  biological_context        JSONB NOT NULL DEFAULT '{}'::jsonb,
  evidence_category         TEXT NOT NULL,
  source_record_version_id  BIGINT NOT NULL
    REFERENCES pv_source.source_record_version(source_record_version_id),
  support_quote             TEXT,
  support_locator           JSONB NOT NULL DEFAULT '{}'::jsonb,
  assertion_date            DATE,
  created_at                TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (
    target_entity_id, phenotype_entity_id, source_record_version_id,
    relationship_literal, evidence_category
  )
);

CREATE TABLE pv_evidence.mechanism_phenotype_assertion (
  mechanism_phenotype_assertion_id BIGSERIAL PRIMARY KEY,
  mechanism_entity_id       UUID NOT NULL REFERENCES pv_core.entity(entity_id),
  phenotype_entity_id       UUID NOT NULL REFERENCES pv_core.phenotype(entity_id),
  relationship_literal      TEXT NOT NULL,
  relationship_normalized   TEXT,
  biological_context        JSONB NOT NULL DEFAULT '{}'::jsonb,
  evidence_category         TEXT NOT NULL,
  source_record_version_id  BIGINT NOT NULL
    REFERENCES pv_source.source_record_version(source_record_version_id),
  support_quote             TEXT,
  support_locator           JSONB NOT NULL DEFAULT '{}'::jsonb,
  assertion_date            DATE,
  created_at                TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (
    mechanism_entity_id, phenotype_entity_id, source_record_version_id,
    relationship_literal, evidence_category
  )
);

CREATE TABLE pv_source.retrieval_query_subject (
  retrieval_query_id   BIGINT NOT NULL REFERENCES pv_source.retrieval_query(retrieval_query_id),
  entity_id            UUID NOT NULL REFERENCES pv_core.entity(entity_id),
  subject_role         TEXT NOT NULL CHECK (
    subject_role IN ('target', 'phenotype', 'asset', 'mechanism')
  ),
  PRIMARY KEY (retrieval_query_id, entity_id, subject_role)
);

CREATE TABLE pv_source.retrieval_query_page (
  retrieval_query_id       BIGINT NOT NULL
    REFERENCES pv_source.retrieval_query(retrieval_query_id),
  page_index               INTEGER NOT NULL CHECK (page_index >= 0),
  source_record_version_id BIGINT NOT NULL
    REFERENCES pv_source.source_record_version(source_record_version_id),
  input_cursor             TEXT,
  output_cursor            TEXT,
  result_count             INTEGER NOT NULL CHECK (result_count >= 0),
  PRIMARY KEY (retrieval_query_id, page_index)
);

CREATE TABLE pv_source.scholarly_work (
  scholarly_work_id    BIGSERIAL PRIMARY KEY,
  canonical_key        TEXT NOT NULL UNIQUE,
  title                TEXT,
  abstract_text        TEXT,
  journal_title        TEXT,
  publication_date_text TEXT,
  first_publication_date DATE,
  author_string        TEXT,
  publication_types    TEXT[] NOT NULL DEFAULT '{}',
  is_open_access       BOOLEAN,
  is_retracted         BOOLEAN,
  cited_by_count       INTEGER,
  created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE pv_source.scholarly_work_identifier (
  scholarly_work_id    BIGINT NOT NULL
    REFERENCES pv_source.scholarly_work(scholarly_work_id) ON DELETE CASCADE,
  namespace            TEXT NOT NULL,
  identifier           TEXT NOT NULL,
  PRIMARY KEY (scholarly_work_id, namespace, identifier),
  UNIQUE (namespace, identifier)
);

CREATE TABLE pv_source.scholarly_work_record (
  scholarly_work_id        BIGINT NOT NULL
    REFERENCES pv_source.scholarly_work(scholarly_work_id) ON DELETE CASCADE,
  source_record_version_id BIGINT NOT NULL
    REFERENCES pv_source.source_record_version(source_record_version_id),
  relationship             TEXT NOT NULL DEFAULT 'bibliographic_metadata',
  PRIMARY KEY (scholarly_work_id, source_record_version_id, relationship)
);

CREATE TABLE pv_evidence.document_relation_candidate (
  retrieval_query_id       BIGINT NOT NULL
    REFERENCES pv_source.retrieval_query(retrieval_query_id),
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
  provider_rank            INTEGER NOT NULL CHECK (provider_rank >= 0),
  disposition              TEXT NOT NULL DEFAULT 'unreviewed' CHECK (
    disposition IN ('unreviewed', 'supports', 'does_not_support', 'ambiguous', 'duplicate')
  ),
  created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (retrieval_query_id, scholarly_work_id),
  CHECK (target_entity_id IS NOT NULL OR mechanism_entity_id IS NOT NULL)
);
CREATE INDEX pv_document_relation_candidate_target_idx
  ON pv_evidence.document_relation_candidate
    (target_entity_id, phenotype_entity_id, disposition);

COMMIT;
