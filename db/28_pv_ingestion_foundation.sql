-- Canonical, replayable raw-evidence ingestion foundation.
--
-- This migration intentionally creates only the source ledger, normalized
-- trial/intervention layer, and a provenance-first assertion table. Literature,
-- phenotype, and assay-specific projections are added by later migrations.

BEGIN;

CREATE SCHEMA IF NOT EXISTS pv_source;
CREATE SCHEMA IF NOT EXISTS pv_core;
CREATE SCHEMA IF NOT EXISTS pv_evidence;

CREATE TABLE pv_source.source_system (
  source_system_id   TEXT PRIMARY KEY,
  provider           TEXT NOT NULL,
  domain             TEXT NOT NULL,
  base_url           TEXT,
  terms_url          TEXT,
  attribution        TEXT,
  created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE pv_source.source_release (
  source_release_id  BIGSERIAL PRIMARY KEY,
  source_system_id   TEXT NOT NULL REFERENCES pv_source.source_system(source_system_id),
  release_label      TEXT NOT NULL,
  provider_date      TIMESTAMPTZ,
  retrieved_at       TIMESTAMPTZ NOT NULL,
  metadata           JSONB NOT NULL DEFAULT '{}'::jsonb,
  UNIQUE (source_system_id, release_label)
);

CREATE TABLE pv_source.acquisition_run (
  acquisition_run_id UUID PRIMARY KEY,
  source_release_id  BIGINT NOT NULL REFERENCES pv_source.source_release(source_release_id),
  adapter             TEXT NOT NULL,
  adapter_version     TEXT NOT NULL,
  git_commit          TEXT CHECK (git_commit IS NULL OR git_commit ~ '^[0-9a-f]{40}$'),
  parameters          JSONB NOT NULL,
  status              TEXT NOT NULL CHECK (status IN ('running', 'completed', 'failed')),
  started_at          TIMESTAMPTZ NOT NULL,
  completed_at        TIMESTAMPTZ,
  discovered_count    INTEGER,
  selected_count      INTEGER,
  stored_count        INTEGER NOT NULL DEFAULT 0,
  reused_count        INTEGER NOT NULL DEFAULT 0,
  failure_count       INTEGER NOT NULL DEFAULT 0,
  error_summary       JSONB NOT NULL DEFAULT '[]'::jsonb
);

CREATE TABLE pv_source.retrieval_query (
  retrieval_query_id BIGSERIAL PRIMARY KEY,
  acquisition_run_id UUID NOT NULL REFERENCES pv_source.acquisition_run(acquisition_run_id),
  query_kind          TEXT NOT NULL,
  query_text          TEXT NOT NULL,
  request_parameters  JSONB NOT NULL,
  expected_total      INTEGER,
  returned_total      INTEGER,
  result_manifest     JSONB NOT NULL,
  manifest_sha256     TEXT NOT NULL CHECK (manifest_sha256 ~ '^[0-9a-f]{64}$'),
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (acquisition_run_id, query_kind)
);

CREATE TABLE pv_source.source_record (
  source_record_id    BIGSERIAL PRIMARY KEY,
  source_system_id    TEXT NOT NULL REFERENCES pv_source.source_system(source_system_id),
  native_record_id    TEXT NOT NULL,
  record_type         TEXT NOT NULL,
  first_seen_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (source_system_id, native_record_id)
);

CREATE TABLE pv_source.object_blob (
  object_blob_id      BIGSERIAL PRIMARY KEY,
  storage_provider    TEXT NOT NULL DEFAULT 'gcs',
  bucket              TEXT NOT NULL,
  object_name         TEXT NOT NULL,
  object_generation   TEXT,
  content_sha256      TEXT NOT NULL CHECK (content_sha256 ~ '^[0-9a-f]{64}$'),
  crc32c              TEXT,
  byte_size           BIGINT NOT NULL CHECK (byte_size >= 0),
  media_type          TEXT NOT NULL,
  rights_tier         TEXT NOT NULL,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (storage_provider, bucket, object_name, object_generation),
  UNIQUE (storage_provider, bucket, object_name, content_sha256)
);

CREATE TABLE pv_source.source_record_version (
  source_record_version_id BIGSERIAL PRIMARY KEY,
  source_record_id         BIGINT NOT NULL REFERENCES pv_source.source_record(source_record_id),
  source_release_id        BIGINT NOT NULL REFERENCES pv_source.source_release(source_release_id),
  acquisition_run_id       UUID NOT NULL REFERENCES pv_source.acquisition_run(acquisition_run_id),
  provider_version         TEXT,
  source_url               TEXT NOT NULL,
  media_type               TEXT NOT NULL,
  content_sha256           TEXT NOT NULL CHECK (content_sha256 ~ '^[0-9a-f]{64}$'),
  byte_size                BIGINT NOT NULL CHECK (byte_size >= 0),
  raw_payload              JSONB NOT NULL,
  raw_payload_text         TEXT NOT NULL,
  object_blob_id           BIGINT REFERENCES pv_source.object_blob(object_blob_id),
  publicly_available_at    TIMESTAMPTZ,
  source_updated_at        TIMESTAMPTZ,
  retrieved_at             TIMESTAMPTZ NOT NULL,
  last_seen_at             TIMESTAMPTZ NOT NULL,
  UNIQUE (source_record_id, content_sha256)
);
CREATE INDEX pv_source_record_version_record_idx
  ON pv_source.source_record_version (source_record_id, retrieved_at DESC);
CREATE INDEX pv_source_record_version_hash_idx
  ON pv_source.source_record_version (content_sha256);

CREATE TABLE pv_source.retrieval_disposition (
  retrieval_query_id      BIGINT NOT NULL REFERENCES pv_source.retrieval_query(retrieval_query_id),
  source_record_id        BIGINT NOT NULL REFERENCES pv_source.source_record(source_record_id),
  source_record_version_id BIGINT REFERENCES pv_source.source_record_version(source_record_version_id),
  result_ordinal          INTEGER NOT NULL CHECK (result_ordinal >= 0),
  disposition            TEXT NOT NULL CHECK (
    disposition IN ('selected_stored', 'selected_reused', 'not_selected', 'failed', 'excluded')
  ),
  detail                  JSONB NOT NULL DEFAULT '{}'::jsonb,
  recorded_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (retrieval_query_id, source_record_id)
);

CREATE TABLE pv_source.license (
  license_id          BIGSERIAL PRIMARY KEY,
  source_system_id    TEXT NOT NULL REFERENCES pv_source.source_system(source_system_id),
  license_name        TEXT,
  terms_url           TEXT NOT NULL,
  terms_retrieved_at  TIMESTAMPTZ NOT NULL,
  terms_sha256        TEXT CHECK (terms_sha256 IS NULL OR terms_sha256 ~ '^[0-9a-f]{64}$'),
  notes               TEXT
);

CREATE TABLE pv_source.rights_assertion (
  rights_assertion_id BIGSERIAL PRIMARY KEY,
  source_record_version_id BIGINT NOT NULL REFERENCES pv_source.source_record_version(source_record_version_id),
  license_id          BIGINT REFERENCES pv_source.license(license_id),
  decision            TEXT NOT NULL CHECK (
    decision IN ('storage_permitted', 'metadata_only', 'review_required', 'storage_prohibited')
  ),
  intended_use        TEXT NOT NULL,
  decided_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  rationale           TEXT NOT NULL
);

CREATE TABLE pv_core.trial (
  nct_id                    TEXT PRIMARY KEY CHECK (nct_id ~ '^NCT[0-9]{8}$'),
  brief_title               TEXT,
  official_title            TEXT,
  study_type                TEXT,
  phases                    TEXT[] NOT NULL DEFAULT '{}',
  overall_status            TEXT,
  lead_sponsor_name         TEXT,
  lead_sponsor_class        TEXT,
  first_submitted_date      DATE,
  first_posted_date         DATE NOT NULL,
  last_update_posted_date   DATE,
  study_start_date_text     TEXT,
  study_start_date          DATE,
  primary_completion_date_text TEXT,
  primary_completion_date   DATE,
  completion_date_text      TEXT,
  completion_date           DATE,
  conditions                TEXT[] NOT NULL DEFAULT '{}',
  has_results               BOOLEAN NOT NULL DEFAULT false,
  latest_source_record_version_id BIGINT NOT NULL
    REFERENCES pv_source.source_record_version(source_record_version_id),
  created_at                TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at                TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX pv_trial_first_posted_idx ON pv_core.trial (first_posted_date, nct_id);

CREATE TABLE pv_core.trial_record_link (
  nct_id                   TEXT NOT NULL REFERENCES pv_core.trial(nct_id),
  source_record_version_id BIGINT NOT NULL
    REFERENCES pv_source.source_record_version(source_record_version_id),
  relationship             TEXT NOT NULL DEFAULT 'registry_record',
  linked_at                TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (nct_id, source_record_version_id, relationship)
);

CREATE TABLE pv_core.trial_arm (
  trial_arm_id             BIGSERIAL PRIMARY KEY,
  nct_id                   TEXT NOT NULL REFERENCES pv_core.trial(nct_id),
  source_record_version_id BIGINT NOT NULL
    REFERENCES pv_source.source_record_version(source_record_version_id),
  source_path              TEXT NOT NULL,
  label                    TEXT NOT NULL,
  arm_type                 TEXT,
  description              TEXT,
  UNIQUE (source_record_version_id, source_path)
);

CREATE TABLE pv_core.intervention_mention (
  intervention_mention_id  BIGSERIAL PRIMARY KEY,
  nct_id                   TEXT NOT NULL REFERENCES pv_core.trial(nct_id),
  source_record_version_id BIGINT NOT NULL
    REFERENCES pv_source.source_record_version(source_record_version_id),
  source_path              TEXT NOT NULL,
  literal_name             TEXT NOT NULL,
  comparison_name          TEXT NOT NULL,
  intervention_type        TEXT,
  description              TEXT,
  other_names              TEXT[] NOT NULL DEFAULT '{}',
  normalization_status     TEXT NOT NULL DEFAULT 'unresolved' CHECK (
    normalization_status IN ('unresolved', 'ambiguous', 'resolved', 'not_applicable')
  ),
  UNIQUE (source_record_version_id, source_path)
);
CREATE INDEX pv_intervention_mention_name_idx
  ON pv_core.intervention_mention (comparison_name);

CREATE TABLE pv_core.arm_intervention (
  trial_arm_id             BIGINT NOT NULL REFERENCES pv_core.trial_arm(trial_arm_id),
  intervention_mention_id  BIGINT NOT NULL
    REFERENCES pv_core.intervention_mention(intervention_mention_id),
  relationship             TEXT NOT NULL DEFAULT 'listed_in_arm',
  PRIMARY KEY (trial_arm_id, intervention_mention_id, relationship)
);

CREATE TABLE pv_core.condition_mention (
  condition_mention_id     BIGSERIAL PRIMARY KEY,
  nct_id                   TEXT NOT NULL REFERENCES pv_core.trial(nct_id),
  source_record_version_id BIGINT NOT NULL
    REFERENCES pv_source.source_record_version(source_record_version_id),
  source_path              TEXT NOT NULL,
  literal_name             TEXT NOT NULL,
  comparison_name          TEXT NOT NULL,
  normalization_status     TEXT NOT NULL DEFAULT 'unresolved' CHECK (
    normalization_status IN ('unresolved', 'ambiguous', 'resolved', 'not_applicable')
  ),
  UNIQUE (source_record_version_id, source_path)
);

CREATE TABLE pv_core.entity (
  entity_id           UUID PRIMARY KEY,
  entity_type         TEXT NOT NULL,
  preferred_name      TEXT NOT NULL,
  provisional         BOOLEAN NOT NULL DEFAULT false,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE pv_core.entity_identifier (
  entity_id           UUID NOT NULL REFERENCES pv_core.entity(entity_id),
  namespace           TEXT NOT NULL,
  identifier          TEXT NOT NULL,
  source_release_id   BIGINT NOT NULL REFERENCES pv_source.source_release(source_release_id),
  is_preferred        BOOLEAN NOT NULL DEFAULT false,
  PRIMARY KEY (entity_id, namespace, identifier, source_release_id),
  UNIQUE (namespace, identifier, source_release_id)
);

CREATE TABLE pv_core.entity_alias (
  entity_alias_id     BIGSERIAL PRIMARY KEY,
  entity_id           UUID NOT NULL REFERENCES pv_core.entity(entity_id),
  entity_type         TEXT NOT NULL,
  alias_text          TEXT NOT NULL,
  alias_normalized    TEXT NOT NULL,
  alias_kind          TEXT NOT NULL,
  language            TEXT,
  taxon_id            INTEGER,
  source_release_id   BIGINT NOT NULL REFERENCES pv_source.source_release(source_release_id),
  source_record_version_id BIGINT
    REFERENCES pv_source.source_record_version(source_record_version_id),
  is_ambiguous        BOOLEAN NOT NULL DEFAULT false
);
CREATE INDEX pv_entity_alias_lookup_idx
  ON pv_core.entity_alias (entity_type, alias_normalized, source_release_id);

CREATE TABLE pv_evidence.assertion (
  assertion_id        BIGSERIAL PRIMARY KEY,
  assertion_kind      TEXT NOT NULL,
  subject_entity_id   UUID NOT NULL REFERENCES pv_core.entity(entity_id),
  predicate_literal   TEXT NOT NULL,
  predicate_normalized TEXT,
  object_entity_id    UUID REFERENCES pv_core.entity(entity_id),
  object_literal      TEXT,
  role                TEXT,
  directness          TEXT,
  source_record_version_id BIGINT NOT NULL
    REFERENCES pv_source.source_record_version(source_record_version_id),
  support_quote       TEXT,
  support_start       INTEGER,
  support_end         INTEGER,
  assertion_date      DATE,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (object_entity_id IS NOT NULL OR object_literal IS NOT NULL),
  CHECK (
    (support_start IS NULL AND support_end IS NULL) OR
    (support_start >= 0 AND support_end > support_start)
  )
);
CREATE INDEX pv_assertion_subject_idx
  ON pv_evidence.assertion (subject_entity_id, assertion_kind);
CREATE INDEX pv_assertion_source_idx
  ON pv_evidence.assertion (source_record_version_id);

-- Every optional LLM enrichment is a versioned run. The decision hash covers
-- schema-validated, decision-bearing JSON rather than free-form prose.
CREATE TABLE pv_evidence.llm_decision_run (
  decision_run_id      UUID PRIMARY KEY,
  task                 TEXT NOT NULL,
  provider             TEXT NOT NULL,
  model                TEXT NOT NULL,
  model_snapshot       TEXT,
  prompt_version       TEXT NOT NULL,
  output_schema_version TEXT NOT NULL,
  code_commit          TEXT CHECK (code_commit IS NULL OR code_commit ~ '^[0-9a-f]{40}$'),
  parameters           JSONB NOT NULL DEFAULT '{}'::jsonb,
  status               TEXT NOT NULL CHECK (status IN ('running', 'completed', 'failed')),
  started_at           TIMESTAMPTZ NOT NULL,
  completed_at         TIMESTAMPTZ,
  compare_to_run_id    UUID REFERENCES pv_evidence.llm_decision_run(decision_run_id),
  created_at           TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX pv_llm_decision_run_task_idx
  ON pv_evidence.llm_decision_run (task, started_at DESC);

CREATE TABLE pv_evidence.llm_decision (
  llm_decision_id      BIGSERIAL PRIMARY KEY,
  decision_run_id      UUID NOT NULL
    REFERENCES pv_evidence.llm_decision_run(decision_run_id),
  task                 TEXT NOT NULL,
  subject_type         TEXT NOT NULL,
  subject_key          TEXT NOT NULL,
  input_sha256         TEXT NOT NULL CHECK (input_sha256 ~ '^[0-9a-f]{64}$'),
  raw_response         TEXT NOT NULL,
  parsed_output        JSONB NOT NULL,
  output_sha256        TEXT NOT NULL CHECK (output_sha256 ~ '^[0-9a-f]{64}$'),
  canonical_decision   JSONB NOT NULL,
  decision_sha256      TEXT NOT NULL CHECK (decision_sha256 ~ '^[0-9a-f]{64}$'),
  prior_decision_id    BIGINT REFERENCES pv_evidence.llm_decision(llm_decision_id),
  change_status        TEXT NOT NULL CHECK (
    change_status IN ('not_compared', 'added', 'changed', 'unchanged')
  ),
  created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (decision_run_id, task, subject_type, subject_key)
);
CREATE INDEX pv_llm_decision_subject_idx
  ON pv_evidence.llm_decision (task, subject_type, subject_key, created_at DESC);

CREATE TABLE pv_evidence.llm_decision_source (
  llm_decision_id      BIGINT NOT NULL
    REFERENCES pv_evidence.llm_decision(llm_decision_id) ON DELETE CASCADE,
  source_record_version_id BIGINT NOT NULL
    REFERENCES pv_source.source_record_version(source_record_version_id),
  ordinal              INTEGER NOT NULL CHECK (ordinal >= 0),
  excerpt_text         TEXT,
  excerpt_sha256       TEXT CHECK (excerpt_sha256 IS NULL OR excerpt_sha256 ~ '^[0-9a-f]{64}$'),
  PRIMARY KEY (llm_decision_id, source_record_version_id, ordinal)
);

CREATE VIEW pv_evidence.v_llm_decision_change AS
SELECT current_decision.decision_run_id,
       current_decision.task,
       current_decision.subject_type,
       current_decision.subject_key,
       current_decision.change_status,
       prior_decision.decision_run_id AS prior_run_id,
       current_decision.decision_sha256,
       prior_decision.decision_sha256 AS prior_decision_sha256,
       current_decision.canonical_decision,
       prior_decision.canonical_decision AS prior_canonical_decision
FROM pv_evidence.llm_decision current_decision
LEFT JOIN pv_evidence.llm_decision prior_decision
  ON prior_decision.llm_decision_id = current_decision.prior_decision_id;

COMMIT;
