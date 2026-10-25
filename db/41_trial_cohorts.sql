-- Immutable cohort definitions and auditable membership decisions.

BEGIN;

CREATE TABLE pv_core.trial_cohort (
  cohort_id          TEXT PRIMARY KEY,
  definition         JSONB NOT NULL,
  definition_sha256  CHAR(64) NOT NULL CHECK (definition_sha256 ~ '^[0-9a-f]{64}$'),
  source_retrieval_query_id BIGINT REFERENCES pv_source.retrieval_query(retrieval_query_id),
  created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (btrim(cohort_id) <> ''),
  CHECK (jsonb_typeof(definition) = 'object'),
  UNIQUE (definition_sha256)
);

CREATE TABLE pv_core.trial_cohort_member (
  cohort_id          TEXT NOT NULL REFERENCES pv_core.trial_cohort(cohort_id),
  nct_id             TEXT NOT NULL REFERENCES pv_core.trial(nct_id),
  candidate_ordinal  INTEGER NOT NULL CHECK (candidate_ordinal >= 0),
  membership_status  TEXT NOT NULL CHECK (
    membership_status IN ('included','excluded','review')
  ),
  reason_code        TEXT NOT NULL,
  decision_method    TEXT NOT NULL,
  support            JSONB NOT NULL DEFAULT '{}'::jsonb,
  decided_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (btrim(reason_code) <> ''),
  CHECK (btrim(decision_method) <> ''),
  CHECK (jsonb_typeof(support) = 'object'),
  PRIMARY KEY (cohort_id,nct_id),
  UNIQUE (cohort_id,candidate_ordinal)
);

CREATE INDEX pv_trial_cohort_member_status_idx
  ON pv_core.trial_cohort_member(cohort_id,membership_status,candidate_ordinal);

COMMIT;
