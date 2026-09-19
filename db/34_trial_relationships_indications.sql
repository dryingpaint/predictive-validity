-- Versioned, source-backed links between trials and between trials and
-- normalized indications. LLM proposals remain in the decision ledger until a
-- verifier creates one of these promoted links.

BEGIN;

CREATE TABLE pv_core.trial_relationship (
  trial_relationship_id BIGSERIAL PRIMARY KEY,
  subject_nct_id        TEXT NOT NULL REFERENCES pv_core.trial(nct_id),
  object_namespace     TEXT NOT NULL,
  object_identifier    TEXT NOT NULL,
  object_display_name  TEXT,
  object_nct_id        TEXT CHECK (
    object_nct_id IS NULL OR object_nct_id ~ '^NCT[0-9]{8}$'
  ),
  relationship_type    TEXT NOT NULL CHECK (
    relationship_type IN (
      'reuses_data_from', 'retrospective_reanalysis_of', 'substudy_of',
      'extension_of', 'follow_up_of', 'protocol_successor_of', 'other'
    )
  ),
  created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (btrim(object_namespace) <> ''),
  CHECK (btrim(object_identifier) <> ''),
  CHECK (object_nct_id IS NULL OR object_nct_id <> subject_nct_id),
  UNIQUE (
    subject_nct_id, object_namespace, object_identifier, relationship_type
  )
);
CREATE INDEX pv_trial_relationship_object_idx
  ON pv_core.trial_relationship
    (object_namespace, object_identifier, relationship_type);
CREATE INDEX pv_trial_relationship_nct_idx
  ON pv_core.trial_relationship (object_nct_id)
  WHERE object_nct_id IS NOT NULL;

CREATE TABLE pv_evidence.trial_relationship_evidence (
  trial_relationship_id     BIGINT NOT NULL
    REFERENCES pv_core.trial_relationship(trial_relationship_id) ON DELETE CASCADE,
  source_record_version_id  BIGINT NOT NULL
    REFERENCES pv_source.source_record_version(source_record_version_id),
  source_path               TEXT NOT NULL,
  support_quote             TEXT NOT NULL,
  derivation_method         TEXT NOT NULL CHECK (
    derivation_method IN (
      'source_explicit', 'deterministic_mapping',
      'llm_proposed_source_verified', 'manual_source_verified'
    )
  ),
  llm_decision_id           BIGINT
    REFERENCES pv_evidence.llm_decision(llm_decision_id),
  detail                    JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at                TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (btrim(source_path) <> ''),
  CHECK (btrim(support_quote) <> ''),
  PRIMARY KEY (
    trial_relationship_id, source_record_version_id, source_path
  )
);
CREATE INDEX pv_trial_relationship_evidence_source_idx
  ON pv_evidence.trial_relationship_evidence (source_record_version_id);

CREATE TABLE pv_core.trial_indication_link (
  trial_indication_link_id  BIGSERIAL PRIMARY KEY,
  nct_id                    TEXT NOT NULL REFERENCES pv_core.trial(nct_id),
  phenotype_entity_id       UUID NOT NULL
    REFERENCES pv_core.phenotype(entity_id),
  condition_mention_id      BIGINT
    REFERENCES pv_core.condition_mention(condition_mention_id),
  indication_role           TEXT NOT NULL CHECK (
    indication_role IN (
      'treatment', 'prevention', 'diagnosis', 'supportive_care',
      'background_condition', 'population_characteristic',
      'healthy_volunteer'
    )
  ),
  source_record_version_id  BIGINT NOT NULL
    REFERENCES pv_source.source_record_version(source_record_version_id),
  resolution_method         TEXT NOT NULL,
  llm_decision_id           BIGINT
    REFERENCES pv_evidence.llm_decision(llm_decision_id),
  created_at                TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (btrim(resolution_method) <> ''),
  UNIQUE (
    nct_id, phenotype_entity_id, indication_role, source_record_version_id
  )
);
CREATE INDEX pv_trial_indication_phenotype_idx
  ON pv_core.trial_indication_link (phenotype_entity_id, indication_role);
CREATE INDEX pv_trial_indication_source_idx
  ON pv_core.trial_indication_link (source_record_version_id);

CREATE TABLE pv_evidence.trial_indication_evidence (
  trial_indication_link_id BIGINT NOT NULL
    REFERENCES pv_core.trial_indication_link(trial_indication_link_id)
    ON DELETE CASCADE,
  source_path              TEXT NOT NULL,
  support_quote            TEXT NOT NULL,
  evidence_role            TEXT NOT NULL CHECK (
    evidence_role IN (
      'literal_condition', 'title_or_summary', 'design_context',
      'eligibility_context', 'ontology_mapping'
    )
  ),
  detail                   JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (btrim(source_path) <> ''),
  CHECK (btrim(support_quote) <> ''),
  PRIMARY KEY (trial_indication_link_id, source_path)
);

COMMIT;
