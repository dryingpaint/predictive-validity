-- Preserve ChEMBL group/complex membership without naming the whole target
-- after the first component gene.

BEGIN;

CREATE TABLE pv_core.target_component (
  group_target_entity_id      UUID NOT NULL REFERENCES pv_core.target(entity_id),
  component_key              TEXT NOT NULL,
  component_target_entity_id UUID REFERENCES pv_core.target(entity_id),
  gene_symbol_literal        TEXT,
  uniprot_accession_literal  TEXT,
  component_name_literal     TEXT,
  relationship_literal       TEXT,
  source_record_version_id   BIGINT NOT NULL
    REFERENCES pv_source.source_record_version(source_record_version_id),
  created_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (group_target_entity_id,component_key,source_record_version_id)
);
CREATE INDEX pv_target_component_resolved_idx
  ON pv_core.target_component(component_target_entity_id,group_target_entity_id);

COMMIT;
