-- Store exact-source, LLM-structured qualifiers on verified ChEMBL
-- asset-to-target assertions without manufacturing narrower target entities.

BEGIN;

CREATE TABLE pv_evidence.asset_target_context_assertion (
  asset_target_context_assertion_id BIGSERIAL PRIMARY KEY,
  asset_target_assertion_id BIGINT NOT NULL
    REFERENCES pv_evidence.asset_target_assertion(asset_target_assertion_id),
  context_type TEXT NOT NULL CHECK (
    context_type IN (
      'subfamily', 'binding_site', 'domain', 'subunit', 'isoform',
      'mutation_state', 'other'
    )
  ),
  context_name TEXT NOT NULL,
  context_normalized TEXT NOT NULL,
  source_record_version_id BIGINT NOT NULL
    REFERENCES pv_source.source_record_version(source_record_version_id),
  source_path TEXT NOT NULL,
  support_quote TEXT NOT NULL,
  llm_decision_id BIGINT NOT NULL
    REFERENCES pv_evidence.llm_decision(llm_decision_id),
  verification_status TEXT NOT NULL CHECK (
    verification_status IN ('exact_source_span', 'rejected')
  ),
  search_eligible BOOLEAN NOT NULL DEFAULT false,
  verifier TEXT NOT NULL,
  verifier_version TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (
    asset_target_assertion_id, context_type, context_normalized,
    source_record_version_id, source_path, support_quote, llm_decision_id
  )
);

CREATE INDEX pv_asset_target_context_lookup_idx
  ON pv_evidence.asset_target_context_assertion
    (asset_target_assertion_id, context_type, search_eligible);

COMMIT;
