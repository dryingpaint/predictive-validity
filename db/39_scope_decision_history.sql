-- Preserve scope decisions across policy versions and source-driven changes.

BEGIN;

ALTER TABLE pv_core.asset_development_scope
  DROP CONSTRAINT asset_development_scope_pkey;
ALTER TABLE pv_core.asset_development_scope
  ADD PRIMARY KEY (asset_entity_id,policy_version);

ALTER TABLE pv_core.trial_development_scope
  DROP CONSTRAINT trial_development_scope_pkey;
ALTER TABLE pv_core.trial_development_scope
  ADD PRIMARY KEY (nct_id,policy_version);

CREATE TABLE pv_core.asset_development_scope_history (
  scope_decision_id BIGSERIAL PRIMARY KEY,
  asset_entity_id   UUID NOT NULL REFERENCES pv_core.asset(entity_id),
  policy_version    TEXT NOT NULL
    REFERENCES pv_core.development_scope_policy(policy_version),
  decision_sha256   CHAR(64) NOT NULL,
  scope_status      TEXT NOT NULL CHECK (
    scope_status IN ('included','excluded','unresolved')
  ),
  scope_category    TEXT NOT NULL,
  reason_code       TEXT NOT NULL,
  classification_method TEXT NOT NULL,
  decision_basis    JSONB NOT NULL,
  classified_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (decision_sha256 ~ '^[0-9a-f]{64}$'),
  UNIQUE (asset_entity_id,policy_version,decision_sha256)
);

CREATE TABLE pv_core.trial_development_scope_history (
  scope_decision_id BIGSERIAL PRIMARY KEY,
  nct_id            TEXT NOT NULL REFERENCES pv_core.trial(nct_id),
  policy_version    TEXT NOT NULL
    REFERENCES pv_core.development_scope_policy(policy_version),
  decision_sha256   CHAR(64) NOT NULL,
  scope_status      TEXT NOT NULL CHECK (
    scope_status IN ('included','separate','excluded','not_applicable','unresolved')
  ),
  scope_category    TEXT NOT NULL,
  reason_code       TEXT NOT NULL,
  classification_method TEXT NOT NULL,
  llm_decision_id   BIGINT REFERENCES pv_evidence.llm_decision(llm_decision_id),
  decision_basis    JSONB NOT NULL,
  classified_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (decision_sha256 ~ '^[0-9a-f]{64}$'),
  UNIQUE (nct_id,policy_version,decision_sha256)
);

COMMIT;
