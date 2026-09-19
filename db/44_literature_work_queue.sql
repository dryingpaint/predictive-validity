-- Durable, lease-based orchestration for large literature retrieval batches.

BEGIN;

CREATE TABLE pv_source.literature_work_item (
  literature_work_item_id BIGSERIAL PRIMARY KEY,
  work_key                TEXT NOT NULL UNIQUE CHECK (work_key ~ '^[0-9a-f]{64}$'),
  cohort_id               TEXT NOT NULL REFERENCES pv_core.trial_cohort(cohort_id),
  policy_version          TEXT NOT NULL REFERENCES pv_core.development_scope_policy(policy_version),
  work_kind               TEXT NOT NULL CHECK (
    work_kind IN ('target_phenotype','asset_preclinical')
  ),
  target_entity_id        UUID REFERENCES pv_core.target(entity_id),
  phenotype_entity_id     UUID REFERENCES pv_core.phenotype(entity_id),
  asset_entity_id         UUID REFERENCES pv_core.asset(entity_id),
  arguments               JSONB NOT NULL,
  status                  TEXT NOT NULL DEFAULT 'pending' CHECK (
    status IN ('pending','running','completed','failed')
  ),
  attempt_count           INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
  lease_token             UUID,
  leased_at               TIMESTAMPTZ,
  completed_at            TIMESTAMPTZ,
  last_error              TEXT,
  created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (jsonb_typeof(arguments)='object'),
  CHECK (
    (work_kind='target_phenotype' AND target_entity_id IS NOT NULL
      AND phenotype_entity_id IS NOT NULL AND asset_entity_id IS NULL)
    OR
    (work_kind='asset_preclinical' AND asset_entity_id IS NOT NULL
      AND target_entity_id IS NULL AND phenotype_entity_id IS NULL)
  ),
  CHECK (
    (status='running' AND lease_token IS NOT NULL AND leased_at IS NOT NULL)
    OR status<>'running'
  )
);
CREATE INDEX pv_literature_work_item_status_idx
  ON pv_source.literature_work_item(cohort_id,status,work_kind,literature_work_item_id);

CREATE TABLE pv_source.literature_work_attempt (
  literature_work_attempt_id BIGSERIAL PRIMARY KEY,
  literature_work_item_id    BIGINT NOT NULL
    REFERENCES pv_source.literature_work_item(literature_work_item_id),
  lease_token                UUID NOT NULL,
  attempt_number             INTEGER NOT NULL CHECK (attempt_number > 0),
  status                     TEXT NOT NULL CHECK (status IN ('running','completed','failed','interrupted')),
  started_at                 TIMESTAMPTZ NOT NULL,
  completed_at               TIMESTAMPTZ,
  acquisition_run_ids        UUID[] NOT NULL DEFAULT '{}',
  stdout_tail                TEXT,
  stderr_tail                TEXT,
  error_summary              TEXT,
  UNIQUE (literature_work_item_id,attempt_number),
  UNIQUE (lease_token)
);

COMMIT;
