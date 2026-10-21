-- Deterministic verification projections for LLM-first trial semantics.

BEGIN;

ALTER TABLE pv_core.target
  ADD COLUMN target_kind TEXT NOT NULL DEFAULT 'protein' CHECK (
    target_kind IN (
      'protein', 'protein_family', 'protein_complex', 'nucleic_acid',
      'pathogen_target', 'other'
    )
  );
ALTER TABLE pv_core.target
  ALTER COLUMN approved_symbol DROP NOT NULL;

ALTER TABLE pv_core.trial_asset_link
  DROP CONSTRAINT trial_asset_link_link_role_check;
ALTER TABLE pv_core.trial_asset_link
  ADD CONSTRAINT trial_asset_link_link_role_check CHECK (
    link_role IN (
      'registered_intervention', 'title_mention', 'background_therapy',
      'component', 'historical_exposure', 'active_comparator',
      'inactive_comparator', 'inferred_exposure'
    )
  );
ALTER TABLE pv_core.trial_asset_link
  ADD COLUMN llm_decision_id BIGINT
    REFERENCES pv_evidence.llm_decision(llm_decision_id);
CREATE UNIQUE INDEX pv_trial_asset_link_nullsafe_unique_idx
  ON pv_core.trial_asset_link (
    nct_id, asset_entity_id, COALESCE(intervention_mention_id, 0),
    link_role, source_record_version_id
  );

CREATE UNIQUE INDEX pv_entity_alias_release_unique_idx
  ON pv_core.entity_alias (
    entity_id, entity_type, alias_text, alias_kind, source_release_id,
    COALESCE(source_record_version_id, 0)
  );

ALTER TABLE pv_evidence.asset_target_assertion
  ADD COLUMN source_native_id TEXT,
  ADD COLUMN support_locator JSONB NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN relationship_origin TEXT NOT NULL DEFAULT 'source_asserted' CHECK (
    relationship_origin IN (
      'structured_database', 'regulatory_text', 'publication_text',
      'source_asserted', 'manual_source_verified'
    )
  );

CREATE TABLE pv_core.mechanism (
  entity_id            UUID PRIMARY KEY REFERENCES pv_core.entity(entity_id),
  mechanism_kind       TEXT NOT NULL CHECK (
    mechanism_kind IN (
      'biological_process', 'pathway', 'chemical_action',
      'physiological_action', 'immune_process', 'unknown'
    )
  ),
  vocabulary_namespace TEXT,
  vocabulary_identifier TEXT,
  created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (vocabulary_namespace, vocabulary_identifier)
);

CREATE TABLE pv_evidence.llm_proposal_verification (
  llm_proposal_verification_id BIGSERIAL PRIMARY KEY,
  llm_decision_id              BIGINT NOT NULL
    REFERENCES pv_evidence.llm_decision(llm_decision_id) ON DELETE CASCADE,
  proposal_kind                TEXT NOT NULL CHECK (
    proposal_kind IN (
      'asset', 'indication', 'pharmacology', 'trial_relationship'
    )
  ),
  proposal_path                TEXT NOT NULL,
  verification_status          TEXT NOT NULL CHECK (
    verification_status IN (
      'verified', 'partially_verified', 'unsupported', 'conflicting',
      'ambiguous', 'unresolved', 'not_applicable'
    )
  ),
  verified_entity_id           UUID REFERENCES pv_core.entity(entity_id),
  verification_source_record_version_id BIGINT
    REFERENCES pv_source.source_record_version(source_record_version_id),
  verifier                     TEXT NOT NULL,
  verifier_version             TEXT NOT NULL,
  detail                       JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at                   TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (btrim(proposal_path) <> ''),
  CHECK (btrim(verifier) <> ''),
  CHECK (btrim(verifier_version) <> ''),
  UNIQUE (llm_decision_id, proposal_kind, proposal_path, verifier, verifier_version)
);
CREATE INDEX pv_llm_proposal_verification_status_idx
  ON pv_evidence.llm_proposal_verification
    (proposal_kind, verification_status);

COMMIT;
