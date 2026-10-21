-- Versioned development-scope policy and materialized scope decisions.
--
-- Raw trial, asset, and source records are never removed by this policy.  The
-- decisions below only gate target/phenotype and asset/preclinical expansion.

BEGIN;

CREATE TABLE pv_core.development_scope_policy (
  policy_version TEXT PRIMARY KEY,
  definition     JSONB NOT NULL,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (btrim(policy_version) <> ''),
  CHECK (jsonb_typeof(definition) = 'object')
);

INSERT INTO pv_core.development_scope_policy (policy_version,definition)
VALUES (
  'human_therapeutics_v1',
  jsonb_build_object(
    'raw_ingestion', 'retain_all_selected_trials_and_source_records',
    'main_track', 'therapeutics acting on human targets or verified human biological mechanisms',
    'excluded', jsonb_build_array(
      'antibiotics',
      'therapeutic-primary bacterial targets',
      'therapeutic-primary viral targets',
      'therapeutic-primary fungal targets',
      'therapeutic-primary parasitic targets'
    ),
    'separate_track', 'vaccines',
    'non_molecular', 'retained without molecular literature expansion',
    'unknown', 'no literature expansion until resolved'
  )
);

CREATE TABLE pv_core.asset_development_scope (
  asset_entity_id   UUID PRIMARY KEY REFERENCES pv_core.asset(entity_id),
  policy_version    TEXT NOT NULL
    REFERENCES pv_core.development_scope_policy(policy_version),
  scope_status      TEXT NOT NULL CHECK (
    scope_status IN ('included','excluded','unresolved')
  ),
  scope_category    TEXT NOT NULL CHECK (
    scope_category IN (
      'human_therapeutic','antibiotic','non_human_target',
      'mixed_human_non_human_target','unknown_target_domain'
    )
  ),
  reason_code       TEXT NOT NULL,
  classification_method TEXT NOT NULL,
  decision_basis    JSONB NOT NULL DEFAULT '{}'::jsonb,
  classified_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (btrim(reason_code) <> ''),
  CHECK (btrim(classification_method) <> ''),
  CHECK (jsonb_typeof(decision_basis) = 'object'),
  CHECK (
    (scope_status = 'included' AND scope_category = 'human_therapeutic')
    OR (scope_status = 'excluded' AND scope_category IN (
      'antibiotic','non_human_target','mixed_human_non_human_target'
    ))
    OR (scope_status = 'unresolved' AND scope_category = 'unknown_target_domain')
  )
);

CREATE TABLE pv_core.trial_development_scope (
  nct_id            TEXT PRIMARY KEY REFERENCES pv_core.trial(nct_id),
  policy_version    TEXT NOT NULL
    REFERENCES pv_core.development_scope_policy(policy_version),
  scope_status      TEXT NOT NULL CHECK (
    scope_status IN ('included','separate','excluded','not_applicable','unresolved')
  ),
  scope_category    TEXT NOT NULL CHECK (
    scope_category IN (
      'human_therapeutic','vaccine','non_human_target',
      'non_molecular_intervention','unknown_target_domain'
    )
  ),
  reason_code       TEXT NOT NULL,
  classification_method TEXT NOT NULL,
  llm_decision_id   BIGINT REFERENCES pv_evidence.llm_decision(llm_decision_id),
  decision_basis    JSONB NOT NULL DEFAULT '{}'::jsonb,
  classified_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (btrim(reason_code) <> ''),
  CHECK (btrim(classification_method) <> ''),
  CHECK (jsonb_typeof(decision_basis) = 'object'),
  CHECK (
    (scope_status = 'included' AND scope_category = 'human_therapeutic')
    OR (scope_status = 'separate' AND scope_category = 'vaccine')
    OR (scope_status = 'excluded' AND scope_category = 'non_human_target')
    OR (scope_status = 'not_applicable' AND scope_category = 'non_molecular_intervention')
    OR (scope_status = 'unresolved' AND scope_category = 'unknown_target_domain')
  )
);

CREATE INDEX pv_trial_development_scope_status_idx
  ON pv_core.trial_development_scope(policy_version,scope_status,scope_category);
CREATE INDEX pv_asset_development_scope_status_idx
  ON pv_core.asset_development_scope(policy_version,scope_status,scope_category);

CREATE VIEW pv_core.v_asset_indication_literature_scope AS
SELECT DISTINCT
  tal.nct_id,
  tal.asset_entity_id,
  til.phenotype_entity_id,
  til.indication_role,
  tds.policy_version
FROM pv_core.trial_asset_link tal
JOIN pv_core.trial_development_scope tds
  ON tds.nct_id=tal.nct_id AND tds.scope_status='included'
JOIN pv_core.asset_development_scope ads
  ON ads.asset_entity_id=tal.asset_entity_id
 AND ads.policy_version=tds.policy_version
 AND ads.scope_status='included'
JOIN pv_core.trial_indication_link til ON til.nct_id=tal.nct_id
WHERE tal.resolution_status='resolved'
  AND til.indication_role IN ('treatment','prevention','diagnosis');

CREATE VIEW pv_core.v_target_phenotype_literature_scope AS
SELECT DISTINCT
  scoped.nct_id,
  scoped.asset_entity_id,
  ata.target_entity_id,
  scoped.phenotype_entity_id,
  scoped.indication_role,
  scoped.policy_version
FROM pv_core.v_asset_indication_literature_scope scoped
JOIN pv_evidence.asset_target_assertion ata
  ON ata.asset_entity_id=scoped.asset_entity_id
JOIN pv_core.target target ON target.entity_id=ata.target_entity_id
WHERE ata.role='therapeutic_primary'
  AND target.taxon_id=9606;

COMMIT;
